# Fase 3 · Avance de Plataforma, 27/10/2026

Trabajo en feat/plataforma, separado del worktree feat/lectura donde se desarrolla Fase 2.
No se editan estrategias, proveedores, generador, calibración, geometría 2D ni bench Python.
No se integra el trabajo sin terminar del otro agente. El visor 3D permanece intacto.

## 3.1 · Cambios en tres capas, verificado

Implementación previa de Plataforma, contrastada de nuevo en la batería completa:
campos con unidades/tolerancias y emparejamiento de boquillas, páginas alineadas por ECC,
geometría por GUID, marcadores/nubes candidatos y BCF 2.1. GET /diff?layers=true,
/diff/visual y /diff/bcf. Pruebas en test_plataforma_changes y test_api_base.
Los marcadores son heurísticos, no detecciones certificadas. Las capas nuevas se consumen
por API/PNG/BCF; no se añade un control nuevo a los archivos del visor protegidos.
No se declara precisión sobre datos reales ni que el extractor B cumpla el F1 final del reto.

## 3.5 · Bench conectado al estudio

Bench consulta el mismo GET /estudio y la misma query que Estudio. La fuente predeterminada
es el estudio actual, con selección de variante, rúbrica, puntuación e IC, procedencia y
restricciones. El bench v1 se conserva en una pestaña separada: no se mezclan sus métricas.
El 10 % de innovación se identifica como convención fija, sin presentarlo como medición.
La elegibilidad por cita/alucinación no se confunde con buena fidelidad geométrica.

Estudio y Bench cuentan los estilos/degradaciones realmente presentes, sin afirmar ocho
proveedores o S-reservado si el informe solo contiene S-dev. Una caída de API muestra el
error y ofrece reintentar; un informe ausente presenta estado vacío. No hay fallback de
un error de API a cifras de la demo. El modo offline conserva el lector de informes publicados.

Pruebas de navegador: mismos valores al cambiar de variante, acceso al bench v1, navegación
a Estudio, alcance parcial, error y vacío. Se revisa visualmente en claro/oscuro sobre la
API local real; capturas bajo generated/qa/fase3-bench-*.png.

## 3.6 · Copiloto local, verificado

Ya implementado con Ollama, cuatro herramientas de solo lectura y citas. La batería vuelve
a comprobar ausencia de escrituras, originales por hash, referencias desconocidas, errores,
contabilidad y revisión cambiada. Sus límites semánticos y medidas reales constan en API.md
y en el informe de Plataforma. No se declara que una cita garantice toda conclusión del modelo.

## 3.7 · Medición real de la cola, parcial

Se añaden scripts/measure_scale.py y scripts/run_scale.py, sin nuevas dependencias.
El orquestador crea proyectos Docker aleatorios con Redis/arq/Postgres y uno o cuatro
workers, concurrencia uno por worker y BLAS/OMP limitados a un hilo. Usa el mismo corpus y
almacenes nuevos por despliegue. No modifica el stack de desarrollo de localhost:3000/8000.
Al terminar elimina exclusivamente sus contenedores y volúmenes sintéticos.

El cliente sube los originales por HTTP, encola revisiones y espera estados terminales.
Mide tiempo de pared, latencia por revisión, pares equipo/condición y contabilidad disponible.
Una respuesta de error cuenta como error, nunca como modelo completado. Los tiempos incluyen
subida, HTTP, cola e instrumentación del cliente. No incluyen construir/arrancar contenedores.

### Corpus y resultados

64 equipos únicos, 168 condiciones y 336 revisiones: todos los conjuntos de Fase 1, con
sus degradaciones y ambas revisiones. Se usa B del snapshot actual, no las estrategias
que el otro agente está desarrollando. No se ajusta el extractor con estilos reservados.

| Despliegue | Tiempo lote | Subida | Terminales/s | Latencia media | P95 | done / error |
| --- | --- | --- | --- | --- | --- | --- |
| 1 worker | 221,425 s | 6,043 s | 1,517 | 18,394 s | 23,772 s | 20 / 316 |
| 4 workers | 65,445 s | 6,877 s | 5,134 | 4,813 s | 8,348 s | 20 / 316 |

La duración observada se reduce 3,38 veces en este lote. Es una medición de infraestructura
con este baseline, sin intervalo estadístico ni garantía de extrapolación a otras estrategias.
Las diferencias de caché del SO/carga de la máquina no se controlan experimentalmente.

`done` significa que el trabajo produjo un IFC que pasó validación estructural/EXPRESS.
**No significa fidelidad correcta contra la verdad**, especialmente en el corpus adversarial.

| Conjunto | done | error |
| --- | --- | --- |
| S-dev | 8 | 136 |
| S-reservado | 0 | 96 |
| S-mecánico | 0 | 72 |
| S-adversarial | 12 | 12 |

Los recuentos coinciden en ambos despliegues. Predominan errores de campos explícitos ausentes,
coherentes con las limitaciones de B antes de OCR, mecánicos y las demás estrategias de Fase 2.
No se deduce de 20 trabajos terminados que 20 modelos sean técnicamente correctos.

La contabilidad devuelve cero llamadas externas y coste null en los 336 trabajos. Se conserva
null: no se inventan euros medidos ni consumo energético/GPU. La proyección a 400 equipos ×
4 revisiones se identifica como **extrapolación** y solo estima terminaciones incluyendo
fallos. No hay estimación defendible de 1600 IFC válidos ni coste monetario completo.
Por eso 3.7 sigue abierta hasta medir una estrategia que cubra el conjunto y su coste.

[Evidencia completa por despliegue y equipo/condición](evidencias/fase3/escala.json).
El SHA del corpus y el de la imagen Docker quedan registrados. Resultados individuales de
cada trabajo en generated/scale/workers-{1,4}.json, fuera de Git, reproducibles con:

```bash
# Construir API una vez desde esta revisión del repositorio.
docker compose --profile local build api
uv run python scripts/run_scale.py --wsl Ubuntu --workers 1 4
# Sin WSL: omitir --wsl Ubuntu, con Docker y Python en PATH.
```

### Necesidades de Lectura

Repetir el lote tras integrar Fase 2. Hace falta que RunInfo informe el coste de proveedor,
con cero explícito cuando proceda, y distinga consumo desconocido. Esta petición no se resuelve
editando su código en paralelo. La cobertura real de mecánicos/escaneos y los modelos A/C/D
siguen bajo responsabilidad de Lectura. El runner admite el corpus completo sin descartarlos.

## Verificación y publicación

180 pruebas Python y Ruff global pasan. Web: typecheck/lint/15 unitarias/build correctos.
Playwright: 15 pasan con API y una exclusiva offline omitida; 11 offline y cinco exclusivas
API omitidas. Se mantienen los avisos previos de TanStack y TestClient/HTTPX.
PW_USE_BUILD permite probar un build en puertos 3100/3200 con API aislada en 8100, sin parar
el servidor dev del usuario. CI añade un job web de instalación congelada, types, lint,
unitarias y build, conservando todos los pasos y la matriz Python Windows/Linux existentes.

3.2–3.4, 3.8 y 3.11 no se marcan como terminadas. Memoria, calibración, fusión y aprendizaje
activo necesitan el trabajo de Lectura. El pitch comparativo se completará con esos resultados.
Los commits y push se realizan por petición expresa del usuario en feat/plataforma.
