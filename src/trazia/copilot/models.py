from typing import Literal

from pydantic import Field, model_validator

from trazia.model import Model, RunInfo


class Statement(Model):
    text: str = Field(min_length=1, max_length=3000)
    citations: list[str] = Field(min_length=1, max_length=6)


class ModelAnswer(Model):
    answer: str = Field(
        max_length=3000,
        description="Explicación con evidencia; vacía si no hay respaldo.",
    )
    citations: list[str] = Field(
        max_length=6,
        description="IDs exactos de las fuentes que respaldan la respuesta y comprobaciones.",
    )
    checks: list[str] = Field(
        max_length=4, description="Comprobaciones humanas propuestas, nunca acciones ejecutadas."
    )

    @property
    def abstained(self):
        return not self.answer.strip()

    @property
    def statements(self):
        return [] if self.abstained else [Statement(text=self.answer, citations=self.citations)]

    @property
    def proposals(self):
        return [Statement(text=text, citations=self.citations) for text in self.checks]

    @model_validator(mode="after")
    def check_answer(self):
        if self.abstained and (self.citations or self.checks):
            raise ValueError("La abstención debe estar vacía")
        if not self.abstained and not self.citations:
            raise ValueError("La respuesta requiere citas")
        if any(not text.strip() or len(text) > 1000 for text in self.checks):
            raise ValueError("Comprobación inválida")
        return self


class Citation(Model):
    id: str
    kind: Literal["field", "evidence", "change", "rule"]
    title: str
    excerpt: str
    path: str | None = None
    document_id: str | None = None
    filename: str | None = None
    sha256: str | None = None
    page: int | None = None
    bbox: list[float] | None = None
    sheet: str | None = None
    cell: str | None = None
    original_verified: bool = False


class CopilotAnswer(Model):
    cached: bool = False
    abstained: bool
    reason: str | None = None
    statements: list[Statement]
    proposals: list[Statement]
    citations: list[Citation]
    read_only: Literal[True] = True
    model: str
    revision_id: str
    revision_version: int
    input_sha256: str
    prompt_sha256: str
    tools_used: list[str]
    run: RunInfo
