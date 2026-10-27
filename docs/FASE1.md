# Fase 1 · Cimientos: evidencias de cierre

Revisión del 27/10/2026 en feat/plataforma. El trabajo ya implementado en main se ha verificado;
las casillas se actualizan con evidencia, no solo por la existencia de archivos.
La comprobación real del segundo proveedor de visión sigue pendiente de credenciales.
No se ha llamado a servicios externos ni se ha enviado ningún documento de TR.

## Contrato, motor y API (1.1, 1.2 y 1.8)

Contrato 0.3, migrador 0.2→0.3, ejemplos raíz validados, estados/alternativas/intervalos y LOD.
Esquema regenerado con `uv run trazia schema -o generated/revision.schema.json` y tipos web
regenerados con `corepack pnpm gen:types` y `corepack pnpm gen:api`, sin diferencias pendientes.
Las pruebas cubren migración, invalidación de aprobación, fuentes y familias.

`trazia.pipeline.process(..., strategy="b_reglas")` es el motor compartido, con interfaz
Strategy, candidatos y StageEvent. API/cola usan ese motor, sin un pipeline duplicado.
La demo persiste en SQLite y la web conectada consume REST/SSE, idempotencia y ETag.
POST /estudio sigue devolviendo 503: el arnés se lanza por CLI. Lanzarlo como trabajo desde
la web es una integración posterior, fuera del criterio de API base de Fase 1.

## Docker real (1.6)

Docker está disponible dentro de Ubuntu/WSL: Engine 29.6.2, Compose 5.3.1, runtime NVIDIA.
Se construyen las imágenes Linux de API y web, y se comprueban los perfiles en proyectos
aleatorios aislados, con puertos del host desactivados. El script verifica API 0.3, trabajo B,
SSE, IFC DRAFT, idempotencia y persistencia tras reiniciar la API, más HTTP 200 de Next.js.
El perfil escala usa Redis + arq + Postgres; el perfil GPU comprueba la GPU dentro de Ollama.
Resultados en [compose-results.json](evidencias/fase1/compose-results.json).

La primera prueba detectó una dependencia de ejecución que el entorno dev ocultaba:
IfcOpenShell importa `_pytest.assertion` al validar EXPRESS. Se incorpora pytest al extra API;
no se desactiva la validación para hacer pasar la prueba. La imagen mantiene el código de
solo lectura para su usuario sin privilegios y almacena caché/registro de visión bajo /data.
Los contextos siguen acotados por Dockerfile.api.dockerignore y Dockerfile.web.dockerignore.

```bash
docker compose --profile local build
uv run python scripts/check_compose.py --profiles local escala gpu
# En PowerShell si Docker está en Ubuntu/WSL:
uv run python scripts/check_compose.py --wsl Ubuntu --profiles local escala gpu
```

El script elimina exclusivamente los contenedores/volúmenes sintéticos de su proyecto
aleatorio. No administra otros proyectos Docker. La prueba del perfil GPU no descarga pesos
ni mide inferencia dentro del contenedor; la inferencia visual real se mide en el Ollama del host.

## Visión, caché y offline (1.9: parcial)

Adaptadores Ollama, Gemini y Mistral con el mismo esquema de líneas/cajas. Plataforma IndesIA
responde explícitamente que falta conocer su servicio; el requisito dice «cuando se sepa».
Se corrige Mistral para consumir los bloques oficiales con content y coordenadas top_left /
bottom_right, sin inventar cajas si faltan dimensiones. Se comprueban ambos adaptadores
externos con transportes simulados; eso es prueba de integración de contrato, no una medición real.

Ollama respeta TRAZIA_OLLAMA_URL/MODEL del Compose y verifica pesos visuales locales antes de
enviar la imagen. Un Ollama remoto se clasifica como externo y pasa por la política/registro.
No se siguen redirecciones ni proxies de entorno. La caché incluye versión de prompt, esquema,
modelo y, para Ollama, servidor. Gemini/Mistral permiten leer cachés offline sin una clave.

Lectura real del mismo GA sintético de la demo, página 1, 100 dpi: 27 fragmentos, 2059/1263 tokens,
34,266 s reportados por Ollama y 38,767 s de pared, con repetición offline idéntica.
Imagen y respuesta real versionadas en tests/fixtures/vision_cache; la prueba que antes se
omitía ahora se ejecuta sin red ni modelo. No es una medición de exactitud en el dataset real.

[Informe de proveedores](evidencias/fase1/vision-comparison.json): Ollama pasa; Gemini y Mistral
no se han llamado porque no hay credenciales. **1.9 no se marca terminada:** exige la misma
página leída por dos proveedores reales. Dos modelos de Ollama o respuestas simuladas no
sustituyen esa comprobación. Para cerrarla hace falta configurar una de las claves y ejecutar:

```bash
uv run --env-file .env python -m trazia.vision.comparar examples/documents/GAD_V-101_revA.pdf --dataset synthetic --proveedores ollama:qwen3-vl:4b-instruct gemini
# O sustituir gemini por mistral.
```

El comando devuelve código 2 si no hay dos familias de proveedor válidas. Deja el error y
el resultado parcial en JSON; no convierte una ausencia en éxito. Las claves nunca van a Git.
La configuración de modelos/precios de servicios externos puede necesitar revisión antes de
la medición real. Fuentes: [Ollama](https://docs.ollama.com/api/chat),
[Mistral OCR y bloques](https://docs.mistral.ai/studio/document-processing/basic_ocr) y
[esquema de su API](https://docs.mistral.ai/openapi.yaml).

## Generador v2 (1.10)

Generados con sus semillas originales, sin escoger casos por resultado:

| Conjunto | Semilla | Equipos | Degradaciones | PDF rev1/rev2 | Excel |
| --- | --- | --- | --- | --- | --- |
| S-dev | 2026 | 24 | 3 | 144 | 96 |
| S-reservado | 7919 | 16 | 3 | 96 | 66 |
| S-mecánico | 4242 | 12 | 3 | 72 | 0 |
| S-adversarial | 6666 | 12 | 1 | 24 | 0 |

Ocho estilos, dos reservados separados, idiomas/unidades, varias páginas, paquetes vendor,
bombas con bancada y trampas adversariales. El mecánico de esta versión es una bomba según
DEC-21; no se declara una familia sintética de compresor. Se han verificado manifiestos y
existencia de ambos GA por condición; no se ha usado S-reservado para ajustar el extractor.
[Manifiestos resumidos y huellas de verdad](evidencias/fase1/conjuntos.json).

```bash
uv run python -m synthetic --conjunto todos
```

## Estudio con B (1.11)

24 equipos de S-dev × tres degradaciones × dos revisiones. Se miden B y su ablación sin HDM;
1000 remuestreos con semilla 2026, McNemar por campo y Pareto. El bootstrap agrupa todas las
degradaciones de cada equipo y las mantiene juntas, también en la diferencia pareada de
ablaciones. Se corrige la unidad de remuestreo, que antes contaba condiciones como equipos.
El título del informe enumera solo los conjuntos efectivamente medidos.

B obtiene puntuación 0,389, IC 95 % [0,327; 0,449], geometría 5,6 %, atributos 69,4 % y F1 de
cambios 13,2 %. Es un baseline de Fase 1: los escaneos y estilos distintos exponen limitaciones
reales que quedan para OCR y las estrategias de Fase 2. No se dice que el estudio A/B/C/D
esté completo ni que esto mida generalización en S-reservado o datos de TR.

[Informe](evidencias/fase1/estudio.md) y [JSON con métricas/estadística](evidencias/fase1/estudio.json).
La prueba del endpoint vacío usa ahora una carpeta aislada: producir un estudio local ya no
hace fallar ese caso. También comprueba que GET /estudio sirve un archivo medido si existe.

```bash
uv run python -m bench.estudio --conjuntos s-dev --variantes b_reglas b_reglas-hdm
```

## Comprobaciones

Typecheck, lint, 13 pruebas unitarias y build web pasan con API y offline. Playwright pasa
12 pruebas conectadas (una exclusiva offline omitida) y ocho offline (cinco exclusivas API
omitidas), incluido el laboratorio IFC. Avisos previos de TanStack/Three/React Flow no son
pruebas fallidas. Se han regenerado esquema y tipos sin cambios manuales.

Ruff check y format globales pasan (92 archivos); 177 pruebas Python pasan, sin omisiones.
Se conserva el aviso previo de deprecación de TestClient/HTTPX. No se hace push ni PR.
