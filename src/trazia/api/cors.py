"""Orígenes explícitos de la web, configurables sin abrir CORS a cualquier sitio."""

import os
from urllib.parse import urlsplit


def origins() -> list[str]:
    raw = os.getenv("TRAZIA_CORS_ORIGINS", "").strip()
    if not raw:
        return [
            f"http://{host}:{port}"
            for host in ("localhost", "127.0.0.1")
            for port in (3000, 3100, 3200, 3300, 3310, 3311)
        ]
    result = []
    for value in raw.split(","):
        if not value.strip():
            continue
        try:
            url = urlsplit(value.strip())
            port = url.port
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or url.path not in {"", "/"}
                or url.query
                or url.fragment
            ):
                raise ValueError()
        except ValueError as failure:
            raise ValueError(
                "TRAZIA_CORS_ORIGINS requiere orígenes HTTP(S) sin rutas ni credenciales"
            ) from failure
        host = f"[{url.hostname}]" if ":" in url.hostname else url.hostname
        suffix = (
            f":{port}"
            if port is not None and port != {"http": 80, "https": 443}[url.scheme]
            else ""
        )
        result.append(f"{url.scheme}://{host}{suffix}")
    if not result:
        raise ValueError("TRAZIA_CORS_ORIGINS no contiene ningún origen válido")
    return list(dict.fromkeys(result))
