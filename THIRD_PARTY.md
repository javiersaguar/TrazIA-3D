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
| openapi-typescript 7.13.0 | MIT | Tipos del cliente desde el esquema OpenAPI |

No se añade ninguna dependencia AGPL. El contenedor Redis utilizará una versión 7.2 BSD;
no se incluye ni se modifica su código en este repositorio.


## Herramientas e imágenes

| Componente | Licencia | Uso |
| --- | --- | --- |
| uv 0.11.30 | MIT o Apache-2.0 | Instalación reproducible con uv.lock |
| Python 3.12 | PSF-2.0 | Runtime de API |
| Node.js 22 | MIT (con avisos de sus componentes) | Runtime web |
| PostgreSQL 16 | PostgreSQL License | Base de datos del perfil escala |
| Redis 7.2 | BSD-3-Clause | Servidor de cola (rama 7.2, no Redis posterior) |
| Ollama 0.40.11 | MIT | Servicio local; sin pesos incluidos |
| PyYAML 6.0.3 | MIT | Herramienta temporal de validación YAML; no dependencia de runtime |

Licencia de [Redis 7.2](https://raw.githubusercontent.com/redis/redis/7.2/COPYING).
Las imágenes upstream conservan los avisos de sus componentes de sistema.
