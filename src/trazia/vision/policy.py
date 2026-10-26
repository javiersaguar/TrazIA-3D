"""Confidencialidad (DEC-31): qué puede salir del equipo y registro de cada envío.

`TRAZIA_EXTERNAL_PROVIDERS`:
- `deny`: ningún proveedor externo.
- `synthetic_only` (por defecto): externos solo con documentos sintéticos.
- `allow`: externos también con documentos reales, y solo si `TRAZIA_EXTERNAL_AUTH` cita la
  autorización escrita (p. ej. «correo del mentor de TR, 25/11/2026»).

Cada llamada externa se anota en `generated/registro_envios.jsonl` (o `TRAZIA_REGISTRO_ENVIOS`):
hash del documento, proveedor, página, conjunto de datos, autorización y fecha. Se anota antes de
enviar: si el envío falla, el intento queda registrado igualmente.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .base import PolicyError

POLICIES = ("deny", "synthetic_only", "allow")


def current_policy() -> str:
    policy = os.environ.get("TRAZIA_EXTERNAL_PROVIDERS", "synthetic_only").strip().lower()
    if policy not in POLICIES:
        raise PolicyError(
            f"TRAZIA_EXTERNAL_PROVIDERS={policy!r} no es válido: usa {', '.join(POLICIES)}"
        )
    return policy


def registry_path() -> Path:
    return Path(os.environ.get("TRAZIA_REGISTRO_ENVIOS", "generated/registro_envios.jsonl"))


def check_external(provider: str, dataset: str) -> str | None:
    """Lanza PolicyError si el envío no está permitido. Devuelve la autorización aplicada."""
    policy = current_policy()
    if policy == "deny":
        raise PolicyError(f"{provider}: proveedores externos desactivados (deny).")
    if dataset != "synthetic":
        if policy != "allow":
            raise PolicyError(
                f"{provider}: los documentos reales no salen del equipo sin autorización "
                "(TRAZIA_EXTERNAL_PROVIDERS=allow y TRAZIA_EXTERNAL_AUTH)."
            )
        auth = os.environ.get("TRAZIA_EXTERNAL_AUTH", "").strip()
        if not auth:
            raise PolicyError(
                f"{provider}: 'allow' exige TRAZIA_EXTERNAL_AUTH con la autorización escrita."
            )
        return auth
    return None


def log_send(
    *,
    provider: str,
    document_sha256: str,
    page_ref: str,
    dataset: str,
    authorization: str | None,
) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provider": provider,
        "document_sha256": document_sha256,
        "page": page_ref,
        "dataset": dataset,
        "authorization": authorization,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def guard_and_log(
    provider: str, *, external: bool, dataset: str, document_sha256: str, page_ref: str
) -> None:
    """Punto único que llama cada proveedor antes de enviar una imagen."""
    if not external:
        return
    authorization = check_external(provider, dataset)
    log_send(
        provider=provider,
        document_sha256=document_sha256,
        page_ref=page_ref,
        dataset=dataset,
        authorization=authorization,
    )
