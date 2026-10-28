# TrazIA / 3D

**Del plano al modelo, con cada cambio trazado.**

Base funcional para [GA2MODEL, reto de Técnicas Reunidas y Multiplica](https://indesiahack.org/tecnicas-reunidas-2026)
en IndesIAhack 2026. Convierte parámetros documentados en un recipiente 3D IFC y permite
revisar de dónde salió cada valor y qué cambió entre versiones.

## Probar en local

Requisitos: Python 3.11–3.13, Git y [uv](https://docs.astral.sh/uv/).

```powershell
git clone https://github.com/javiersaguar/TrazIA-3D.git
cd TrazIA-3D
uv sync --frozen --extra dev
uv run trazia serve
```

Abrir **http://127.0.0.1:8501**. La app arranca con la revisión A de un caso sintético.

1. Orbitar el IFC e inspeccionar virola, fondos, faldón y tres boquillas.
2. Seleccionar un campo para ver su región en el PDF o su fila de Excel.
3. Corregir datos y comprobar las validaciones.
4. Revisar valores y evidencias, indicar revisor y aprobar esa versión.
5. Descargar JSON e IFC; las versiones sin aprobación se marcan DRAFT.
6. Abrir Cambios A → B para comparar ambos modelos y descargar el delta.

Alternativa sin uv: crear un entorno virtual e instalar `python -m pip install -e ".[dev]"`.
Después usar `python -m trazia` en lugar de `uv run trazia`.

## Qué hay construido

| Parte | Estado |
| --- | --- |
| Ingesta PDF | Texto por región, página, SHA-256 y visualización de evidencia |
| Ingesta Excel | Filas/celdas y unidades; detecta fórmulas sin evaluarlas |
| Imágenes y páginas sin texto | Se catalogan y señalan como pendientes de OCR/visión |
| Extracción de referencia | Reglas para etiquetas explícitas; candidatos, conflictos y normalización |
| Contrato JSON | Valor, unidad, fuente, score y estado de revisión por campo |
| IFC4 | Virola, dos fondos semielipsoidales, faldón anular y ≥3 boquillas radiales |
| Visor | Tesela el IFC generado con IfcOpenShell y lo muestra con Plotly |
| Revisión humana | Verifica originales y liga la aprobación a una huella de los datos |
| Revisiones | Diferencias de valores/unidades, evidencias y documentos; GUID estables |
| Calidad | Pruebas del recorrido, reglas EXPRESS IFC y CI para Windows/Linux |

**Evaluado con sintéticos, todavía no con el dataset oficial.** B lee etiquetas, tablas y cotas;
RapidOCR aporta texto en escaneados. A reconstruye desde vistas, C adapta plantillas y D combina
canales. Hay adaptadores de visión locales y externos con caché. La precisión depende del tipo
de plano y de la variante; implementación no equivale a validación sobre planos arbitrarios.
El estado medido y lo pendiente figuran en [ROADMAP](docs/ROADMAP.md) y [ESTUDIO](docs/ESTUDIO.md).

## Demo reproducible

Los archivos de `examples/documents/` son **PDF y Excel sintéticos que sí existen**.
Los JSON de ejemplo se han extraído de esos archivos con el mismo pipeline de la aplicación;
incluyen hashes y localizadores reales y comienzan sin aprobación.

```powershell
uv run trazia validate examples/vessel_rev_a.json
uv run trazia export examples/vessel_rev_a.json --draft -o generated/rev_a.ifc
uv run trazia export examples/vessel_rev_b.json --draft -o generated/rev_b.ifc
uv run trazia diff examples/vessel_rev_a.json examples/vessel_rev_b.json -o generated/changes.json
uv run trazia diff examples/vessel_rev_a.json examples/vessel_rev_b.json -o generated/changes.md
uv run trazia schema -o generated/revision.schema.json
```

En B la virola pasa de 6.000 a 6.500 mm; el faldón de 1.200 a 1.350 mm; N3 sube 200 mm;
el peso de operación aumenta 800 kg; se añade N4. Resultado: **8 cambios de campos,
7 geométricos y 1 de atributo**. La boquilla nueva aporta cuatro campos.

Para regenerar los documentos y sus JSON: `uv run python scripts/make_demo.py`.
No usar esta demo para afirmar precisión sobre documentación de ingeniería real.

## Campos para revisión en Excel o CSV

```powershell
uv run trazia fields examples/vessel_rev_a.json -o generated/campos.xlsx
uv run trazia fields examples/vessel_rev_a.json -o generated/campos.csv
```

Conserva valor, unidad, estado y evidencia por campo; no modifica ni aprueba el JSON.
[Formatos y columnas](docs/EXPORTACION_CAMPOS.md).

## Ingesta y aprobación por CLI

```powershell
uv run trazia ingest examples/documents/GAD_V-101_revA.pdf --id GA-V101 --revision A -o generated/ga.json
uv run trazia ingest examples/documents/HDM_V-101_revA.xlsx --id HDM-V101 --revision A -o generated/hdm.json
uv run trazia extract generated/ga.json generated/hdm.json --project DEMO-PLANT --equipment vessel-001 --revision A --synthetic -o generated/draft.json
```

Tras revisar los originales y todos los campos:

```powershell
uv run trazia approve generated/draft.json --reviewer "Nombre del revisor" --original GA-V101=examples/documents/GAD_V-101_revA.pdf --original HDM-V101=examples/documents/HDM_V-101_revA.xlsx -o generated/approved.json
uv run trazia export generated/approved.json -o generated/approved.ifc
```

La aprobación guarda revisor, fecha con zona horaria y huella de datos/evidencias/documentos.
No es una firma digital ni autenticación de identidad. Un JSON modificado con la aprobación
anterior es rechazado. `validate` valida el contrato; no concede aprobación.

## Arquitectura

```text
PDF / XLSX / imagen
  → ingest.py       Catálogo, hashes, texto y localizadores
  → extraction.py   Candidatos por etiquetas + interfaz para futuros extractores IA
  → model.py        JSON normalizado y validación geométrica
  → review.py       Originales verificados + revisión humana
  → ifc.py          IFC4 con identidad y trazabilidad
  → viewer.py       Mallas leídas del IFC
  → revisions.py    Valores, unidades, fuentes e impacto por reglas
  → app.py / cli.py Espacio de revisión y comandos
```

## Convenciones y límites

- Una familia inicial: recipiente vertical con fondos iguales y boquillas laterales radiales.
- Longitudes canónicas en mm y ángulos en grados, explícitos por campo. IFC y visor en metros.
- Z vertical; azimut antihorario de +X a +Y. Elevaciones medidas desde el suelo.
- `height`: longitud de virola entre tangentes. `skirt_height`: suelo a tangente inferior.
- Altura total = `skirt_height + height + head_depth`; fondo inferior dentro del faldón.
- Envolvente de virola y boquillas maciza; fondos semielipsoidales teselados; faldón anular.
  Sin diseño de espesores del recipiente, bridas, taladros ni cálculo mecánico.
- El delta compara valores/unidades exactos; no hace equivalencias de atributos ni tolerancias.
- Se regenera cada IFC conservando GUID; no parchea IFC externos ni detecta cambios de identidad.
- Impactos por reglas, pendientes de revisión de ingeniería. Scores heurísticos sin calibrar.
- Sesiones locales en memoria; descargar los resultados para conservarlos. Sin base de datos,
  autenticación, colaboración multiusuario ni despliegue de producción.
- Máximo 25 MB por documento y 100 páginas por PDF; imágenes sin OCR no producen parámetros.
- Todo se procesa localmente; no hay llamadas a un proveedor IA ni claves necesarias.

Los originales privados deben ir en `data/private/`, excluido de Git. El PDF del enunciado y
el dataset del organizador no se incluyen en el repositorio.

## Verificación y siguiente hito

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

Ver [alcance y prioridades](docs/BASE_DEL_RETO.md), [contrato y extracción](docs/DATA_CONTRACT.md)
y [guion de demo](docs/DEMO.md). El siguiente hito es conectar OCR/visión con un GA y su HDM
del dataset oficial y medir errores frente a su IFC de referencia.
