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


## Geometría (extra geo)

| Dependencia | Licencia | Uso |
| --- | --- | --- |
| trimesh 4.12.2 | MIT | Muestreo de superficies y distancias a triángulos |
| scipy 1.18.1 | BSD-3-Clause (más avisos de bibliotecas incluidas en su distribución) | Índices y cálculos geométricos |
| Rtree 1.4.1 | MIT | Índice espacial para proximidad |
| libspatialindex incluida por Rtree (versión >=1.8) | MIT | Motor nativo de índice espacial, sin modificar |

Metadatos de las distribuciones instaladas comprobados el 26/10/2026. Se conservan sus avisos.
[Licencia de libspatialindex](https://raw.githubusercontent.com/libspatialindex/libspatialindex/master/COPYING).


## Cambios visuales y unidades

| Dependencia | Licencia | Uso |
| --- | --- | --- |
| Pint 0.26.2 | BSD-3-Clause | Equivalencias de unidades y temperaturas con offset |
| flexcache 0.3 / flexparser 0.4 | BSD-3-Clause | Dependencias de Pint |
| platformdirs 4.13.5 | MIT | Rutas de caché de Pint |
| opencv-python-headless 4.14.0.94 | Apache-2.0 (OpenCV), MIT (empaquetado) | ECC y contornos sin GUI |
| FFmpeg incluido en la rueda OpenCV | LGPL-2.1 | Binario sin modificar; se conservan sus avisos |
| lxml (herramienta temporal de validación XML) | BSD-3-Clause, más avisos de libxml2/libxslt incluidos | Verificar BCF frente a XSD oficiales; no se añade al runtime |

Metadatos instalados comprobados el 26/10/2026.
[Licencias OpenCV y ruedas](https://github.com/opencv/opencv-python#licensing).
Los XSD oficiales de BCF 2.1 se descargan solo a generated/ para comprobación local; no se redistribuyen.


## Núcleo y lectura (Lectura)

Prohibido todo lo AGPL: Ultralytics/YOLO y PyMuPDF no se usan (DEC-30).

| Dependencia | Licencia | Uso |
| --- | --- | --- |
| pydantic | MIT | Contrato de datos |
| ifcopenshell | LGPL-3.0 | Escritura y validación IFC |
| pdfplumber | MIT | Texto, trazos y tablas de PDF vectorial |
| openpyxl | MIT | Hojas de datos mecánicos |
| pillow | MIT-CMU (HPND) | Imágenes de página |
| streamlit | Apache-2.0 | Demo de escritorio |
| plotly | MIT | Gráficos de la demo |
| pint | BSD-3-Clause | Unidades del estudio (pulgadas, ft-in, psig, °F) |
| scipy | BSD-3-Clause | McNemar exacto y estadística del estudio |
| scikit-learn | BSD-3-Clause | Calibración isotónica y fusión aprendida (próximas fases) |

## Modelos (Lectura)

| Modelo | Licencia | Uso |
| --- | --- | --- |
| Qwen3-VL 4B Instruct (vía Ollama, Q4_K_M) | Apache-2.0 | Lectura visual local por mosaicos (tarea «lineas»); los pesos no se incluyen |


## Modelo del Copiloto (Plataforma)

Qwen3-VL-4B-Instruct, Apache-2.0, ejecutado con Ollama mediante la etiqueta
`qwen3-vl:4b-instruct` (GGUF Q4_K_M). Se reutiliza el modelo local instalado; los pesos
no se incluyen ni se redistribuyen en este repositorio. Sirve para planificar lecturas y
responder con citas, sin capacidad de escritura. Comprobado el 27/10/2026 con Ollama 0.40.11,
modelo instalado `84f7ed8042fa`. No se añaden dependencias Python/JavaScript para esta fase.

[Modelo y licencia oficial](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct),
[distribución Ollama](https://ollama.com/library/qwen3-vl:4b-instruct).


Pytest (MIT) también es dependencia de ejecución del extra API: IfcOpenShell 0.8.x usa
`_pytest.assertion` para ejecutar las reglas EXPRESS. Se conserva la validación en producción.
