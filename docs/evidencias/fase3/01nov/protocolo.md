# Protocolo · CPU / 01 de noviembre

Código de medición y backend: commit `63e6c213182b18c0237ec2b9f75d536ddc8356d0`. Imagen y huellas completas en [procedencia.json](procedencia.json). El primer intento se detuvo por un error de serialización NumPy; no forma parte de las cifras finales. Se conserva como diagnóstico local. La imagen nueva se construyó después de corregirlo y su page_cache.py se contrastó byte a byte con el árbol de trabajo.

## Condiciones

- Sintéticos v2: las mismas 336 revisiones del registro del 31/10. S-dev: 24 casos × 3 estilos × 2 revisiones = 144 (semilla 2026); S-reservado: 16 × 3 × 2 = 96 (7919); S-mecánico: 12 × 3 × 2 = 72 (4242); S-adversarial: 12 × 1 × 2 = 24 (6666). Total: 168 condiciones documentales y dos revisiones por condición. La proyección a cuatro revisiones es una extrapolación, no otro lote medido. La comparación exige coincidencia de claves y de input_sha256; no se toca data/private/.
- D híbrido sin proveedores de visión. CPU: CUDA_VISIBLE_DEVICES=-1, OMP_NUM_THREADS=1 y OPENBLAS_NUM_THREADS=1; sin credenciales externas en contenedores. Se verifica calibración y fusión en API y en cada worker antes de enviar trabajos.
- Redis/arq y Postgres, concurrencia uno por worker; despliegues independientes con volúmenes nuevos, primero uno y después cuatro workers. Puerto 8034. El script solo elimina sus proyectos de Compose al terminar.
- Host Windows/WSL compartido. Las pruebas web y Python terminaron antes del lote final; durante el lote solo se consultó progreso y editaron documentos. Observación agregada del host en host.jsonl (carga observada del proceso de WSL y suma de los 15 procesos superiores, no CPU total exacta). Los registros crudos de procesos se conservan solo localmente.
- Calibración v5 S-dev: [parámetros exactos](calibracion-v5.json), huella de modelo dd2f98c238da35d7d648b36b99317e2a991d7041d51ab03ea171428952c10636. Fusión empaquetada: a7d09074255ee78af4af3dd1cb7dd8f592e795c5000ebad560cc2a0415486d55. No se entrenó otro modelo para este lote.

## Reproducción

En Windows con Docker disponible en WSL Ubuntu, desde el checkout del commit anterior (ajustar la ruta del conjunto):

```powershell
uv sync --frozen --extra dev --extra api --extra geo
wsl -d Ubuntu --exec docker build -f Dockerfile.api -t trazia-plataforma:20261101-pagecache-v2 .
uv run python scripts/run_scale.py --wsl Ubuntu --workers 1 4 --estrategia d_hibrido --image trazia-plataforma:20261101-pagecache-v2 --data ../TrazIA-3D/generated/synthetic_v2 --output generated/escala-reproduccion --api-port 8034 --calibration docs/evidencias/fase3/01nov/calibracion-v5.json --expected-calibration dd2f98c238da35d7d648b36b99317e2a991d7041d51ab03ea171428952c10636 --expected-fusion a7d09074255ee78af4af3dd1cb7dd8f592e795c5000ebad560cc2a0415486d55 --eur-worker-hora 0.10
```

El commit fija código; los documentos y calibración de esta carpeta pertenecen al commit posterior de evidencias. Se pueden copiar sobre el checkout fijado sin modificar código. No se compara una regeneración del corpus como si fuese idéntica sin contrastar su huella.

## Qué mide

Terminaciones, DRAFT exportables, errores, LOD, boquillas sin ubicar, latencia/tiempo por equipo y consumo registrado de proveedores. El factor de escala compara el tiempo total del mismo lote. No prueba precisión de ingeniería ni coste de entregar 1.600 IFC correctos.

0,10 €/worker-h es una **hipótesis**, no una tarifa contratada ni un gasto medido. El cálculo 400×4 extrapola terminaciones, también las fallidas. Coste humano, infraestructura fija, tiempo/coste de IFC correctos permanecen null. E.5 está pospuesta por Javier; no se realiza ni simula una sesión humana para rellenarlos.

La prueba incremental es otra secuencia real, sin red, RapidOCR y etapas por página: [resultado](incremental-etapas.json). Usa la imagen previa solo como dependencias/pesos y monta el código de c066864 en lectura. El patrón 2/1/0/2 confirma reutilización por página; no implica edición incremental del IFC ni un porcentaje de ahorro generalizable.
