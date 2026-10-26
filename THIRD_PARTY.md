# Dependencias de Plataforma

Dependencias sin modificar; las licencias y avisos se conservan en las distribuciones instaladas.
Esta relación complementa las dependencias existentes del proyecto.
Licencias comprobadas en los metadatos de PyPI el 26/10/2026.

| Dependencia | Licencia | Uso |
| --- | --- | --- |
| FastAPI | MIT | API HTTP y esquema OpenAPI |
| SQLModel | MIT | Modelos persistentes |
| SQLAlchemy (transitiva de SQLModel) | MIT | Transacciones SQLite/Postgres |
| Alembic | MIT | Migraciones |
| Uvicorn | BSD-3-Clause | Servidor ASGI |
| python-multipart | Apache-2.0 | Subida multipart |
| HTTPX | BSD-3-Clause | Cliente local y pruebas HTTP |
| arq | MIT | Cola Redis y workers |
| redis-py (transitiva de arq) | MIT | Cliente Redis |
| psycopg / psycopg-binary | LGPL-3.0-only | Adaptador Postgres sin modificar |

No se añade ninguna dependencia AGPL. El contenedor Redis utilizará una versión 7.2 BSD;
no se incluye ni se modifica su código en este repositorio.
