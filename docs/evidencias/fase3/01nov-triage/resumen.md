# Reproducción de los 85 errores · 01/11

Datos exclusivamente sintéticos; D en CPU, sin proveedores ni red. No se modifica el extractor,
la reconciliación, los validadores ni el contrato. La GT solo se lee después de cada predicción.

- Casos: 85/85 del inventario previo; 34 S-dev, 19 S-reservado y 32 S-mecánico.
- Resultado: **0 recuperados, 85 errores** (63 campos ausentes y 22 geometrías incoherentes).
- Tiempo acumulado de las 85 invocaciones: **290.244 s**.
  Incluye importación inicial del OCR en el primer caso; no mide upload, Redis ni escalado.
- Parámetros: calibración v6 `5496cf49cbe426d15ad807a662ce0aa26cb3454540b2b4b047ce3c8d3f0d66ec`.
- Documentos: `da9ea85b70734d8ccdb0d63aef882b1d488667f08e52495a5a9b6c28a951e170`, iguales al lote completo de 336 revisiones del 01/11.
- Fuente Python montada en solo lectura: `72d924b7f6924999609bfc05a1e2ee59240d96ae0b5bc899a39f61104d6db105`.
  La imagen aporta dependencias; su código queda reemplazado por el montaje indicado.
- Llamadas externas: 0; GPU oculta, ONNX en CPU.

[Datos completos y metadatos](triage-v6.json), [parámetros](calibracion-v6.json).

## Diagnóstico para Lectura

En S-dev, tres ejemplos reproducidos antes del lote muestran asociación ambigua de cotas:

| Equipo/rev | Campo elegido | Predicción mm | GT sintética mm |
| --- | --- | --- | --- |
| C-202/2 · escaneado limpio | head_depth | 6750,05 | 525,4625 |
| C-203/1 · limpio | skirt_height | 246,062 | 1449,3875 |
| V-210/1 · escaneado pobre | skirt_height | 11 | 1950 |

Los dos primeros conservan diámetro correcto; el segundo conserva altura y profundidad correctas.
El pipeline rechaza los tres por la posición del fondo inferior. No es un problema de Redis ni
una razón para relajar las restricciones físicas. El inventario conserva candidatos, alternativas,
canal, estado, fuente y avisos para revisar geometría/OCR y fusión en las carpetas de Lectura.
No se ha ajustado el sistema con S-reservado ni se ha usado la GT como entrada.

## Reproducción

Con las dependencias CPU/OCR/geometría del proyecto, desde la raíz:

```powershell
$env:CUDA_VISIBLE_DEVICES='-1'
$env:TRAZIA_VISION_OFFLINE='1'
$env:TRAZIA_CALIBRATION='docs/evidencias/fase3/01nov-triage/calibracion-v6.json'
uv run python scripts/triage_scale.py --report docs/evidencias/fase3/01nov/d-workers-4.json --data ../TrazIA-3D/generated/synthetic_v2 --output generated/triage-repeticion --sets s-dev s-reservado s-mecanico s-adversarial
```

La ejecución archivada utilizó la imagen del registro anterior con el código actual montado,
`--network none`, `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1` y caché local compartida
con la reproducción inicial de tres casos S-dev; no se presenta como tiempo en frío. El SHA de código y
script identifica la ejecución; el comando de arriba no garantiza esos mismos tiempos en Windows.
El programa verifica el SHA del corpus completo y rechaza carpetas privadas o lotes incompletos.

## Límite del resultado

Solo se repiten los fallos: no se ha vuelto a medir el rendimiento ni las 251 exportaciones
previas con v6. No permite afirmar que el total actual sea 251/336 ni validar su precisión.
El presupuesto de 1.600 IFC correctos sigue desconocido. Se conserva como extrapolación de
terminaciones el escenario anterior de 72,96 min y 0,4864 EUR de cómputo bajo su tarifa hipotética;
no incluye corregir estas 85 incidencias, revisión humana ni coste de ingeniería.
