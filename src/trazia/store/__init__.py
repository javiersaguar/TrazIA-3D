"""Persistencia transaccional y archivos inmutables por SHA-256."""

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, create_engine


class DocumentRecord(SQLModel, table=True):
    __tablename__ = "documents"
    id: str = Field(primary_key=True)
    document_id: str
    filename: str
    revision: str
    sha256: str = Field(index=True)
    size: int


class RevisionRecord(SQLModel, table=True):
    __tablename__ = "revisions"
    id: str = Field(primary_key=True)
    project_id: str = Field(index=True)
    equipment_id: str
    tag: str = Field(index=True)
    revision: str
    version: int = 1
    payload: str


class JobRecord(SQLModel, table=True):
    __tablename__ = "jobs"
    id: str = Field(primary_key=True)
    tag: str
    status: str = Field(default="queued", index=True)
    request_json: str
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    attempts: int = 0
    cancel_requested: bool = False
    error: str | None = None
    run_json: str | None = None
    revision_id: str | None = None
    lease_until: float | None = None
    warnings_json: str = "[]"
    kind: str = "pipeline"
    result_sha256: str | None = None
    elapsed_seconds: float | None = None
    cache_hit: bool = False


class JobCacheRecord(SQLModel, table=True):
    __tablename__ = "job_cache"
    key: str = Field(primary_key=True)
    result_sha256: str
    created_at: float = Field(default_factory=time.time)


class EventRecord(SQLModel, table=True):
    __tablename__ = "events"
    id: int | None = Field(default=None, primary_key=True)
    job_id: str = Field(foreign_key="jobs.id", index=True)
    stage: str
    status: str
    file: str
    detail: str
    created_at: float = Field(default_factory=time.time)


class IdempotencyRecord(SQLModel, table=True):
    __tablename__ = "idempotency"
    id: str = Field(primary_key=True)
    request_sha256: str
    response_json: str
    expires_at: float


class AuditRecord(SQLModel, table=True):
    __tablename__ = "audit"
    id: int | None = Field(default=None, primary_key=True)
    revision_id: str = Field(foreign_key="revisions.id", index=True)
    path: str
    actor: str
    before_json: str
    after_json: str
    seconds: float | None = None
    created_at: float = Field(default_factory=time.time)


class IdempotencyConflict(ValueError):
    pass


class Store:
    def __init__(self, root: Path, database_url: str | None = None):
        self.root = root.resolve()
        self.blobs = self.root / "store"
        self.blobs.mkdir(parents=True, exist_ok=True)
        url = database_url or f"sqlite:///{(self.root / 'trazia.sqlite3').as_posix()}"
        options = {"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, connect_args=options, pool_pre_ping=True)
        if url.startswith("sqlite"):

            @event.listens_for(self.engine, "connect")
            def sqlite_settings(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA journal_mode=WAL")

        config = Config()
        config.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

    def put(self, content: bytes) -> str:
        digest = hashlib.sha256(content).hexdigest()
        folder = self.blobs / digest[:2]
        folder.mkdir(exist_ok=True)
        path = folder / digest
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("El archivo del almacén está dañado")
            return digest
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=folder, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
        return digest

    def read(self, digest: str) -> bytes:
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("SHA-256 inválido")
        content = (self.blobs / digest[:2] / digest).read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError("El SHA-256 del original no coincide")
        return content

    def perform(self, scope: str, key: str, body: dict, action):
        """Efecto y respuesta se confirman juntos; la clave caduca a las 24 horas."""
        identity = hashlib.sha256(f"{scope}:{key}".encode()).hexdigest()
        fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        with Session(self.engine) as session:
            record = session.get(IdempotencyRecord, identity)
            if record and record.expires_at <= time.time():
                session.delete(record)
                session.flush()
                record = None
            if record:
                if record.request_sha256 != fingerprint:
                    raise IdempotencyConflict("La clave ya se utilizó con otra petición")
                return json.loads(record.response_json)
            result = action(session)
            session.add(
                IdempotencyRecord(
                    id=identity,
                    request_sha256=fingerprint,
                    response_json=json.dumps(result),
                    expires_at=time.time() + 86400,
                )
            )
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                record = session.get(IdempotencyRecord, identity)
                if record is None or record.request_sha256 != fingerprint:
                    raise IdempotencyConflict("Escritura concurrente con otra petición") from None
                return json.loads(record.response_json)
            return result

    def close(self):
        self.engine.dispose()
