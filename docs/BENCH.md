# GA2MODEL Bench y generador sintético

Tareas 1.4 y 1.5 del [roadmap](ROADMAP.md) (sección G). Miden el pipeline real del núcleo con la
estructura de la rúbrica del jurado: 35 % geometría, 25 % atributos, 20 % cambios y 10 % escalado.

> Todo lo de esta página es **sintético**. Sirve para medir y comparar extractores con verdad
> conocida; no es precisión sobre planos de Técnicas Reunidas.

## Uso

```bash
uv run python -m synthetic --casos 20 --semilla 2026          # → generated/synthetic/
uv run python -m bench                                        # → generated/bench/report.md y .json
uv run python -m bench --detalle                              # añade cases.json con el detalle por caso
```

`generated/` no se versiona: el conjunto se regenera igual con la misma semilla.

## Qué genera `synthetic`

Recipientes verticales aleatorios: diámetro, virola, fondos 2:1, faldón, de 3 a 7 boquillas y datos de
diseño. Todos son válidos para las reglas de `trazia.model`. Cada equipo tiene:

- **rev1** y **rev2**: la rev2 aplica de 1 a 4 cambios del tipo que muestra el reto (pág. 11). Por
  ejemplo, mover o girar una boquilla, alargar la virola o el faldón, cambiar el peso o la presión, o
  añadir o quitar una boquilla.
- Archivos con la **convención de nombres del dataset**: `GAD_<TAG>_rev1.pdf`, `HDM_<TAG>_rev1.xlsx`…
- `truth/<TAG>.json`: valores verdaderos de las dos revisiones y la lista de cambios esperados, con la
  misma forma que `trazia diff`.

Hay tres estilos de GA:

| Estilo | Qué es | Para qué sirve |
| --- | --- | --- |
| `rotulado` | Parámetros escritos como `ETIQUETA = valor unidad` | Comprueba la cadena completa con el extractor actual |
| `plano` | GA dibujado: alzado con cotas, planta con orientaciones, tabla de boquillas, datos de diseño, cajetín y triángulos Δ en la rev2 | Es el objetivo de los extractores de tablas y de visión |
| `escaneado` | El plano rasterizado con ruido y una leve rotación, sin capa de texto | Es el objetivo del OCR |

## Qué mide `bench`

| Rúbrica | Métricas |
| --- | --- |
| Geometría 35 % | Cobertura y acierto de campos geométricos; error medio en dimensiones (mm); recall y precisión de boquillas; error de posición 3D de la cara de cada boquilla (mm); error de orientación (°); acierto de DN. **IFC frente a IFC de referencia**: elementos presentes, IoU de cajas y error de centro (mm) |
| Atributos 25 % | Cobertura; acierto de valor + unidad; **ECE** y Brier de la confianza; puntos del diagrama de fiabilidad (en `report.json`) |
| Cambios 20 % | Precisión, recall y F1 por campo y operación; error en la magnitud del cambio |
| Escalado 10 % | Segundos por revisión con modelo (ingesta → IFC), revisiones por hora, llamadas a modelos de IA |

El IFC de referencia del conjunto sintético se construye con los valores verdaderos.
`bench/ifc_geometry.py` compara elemento a elemento cualquier par de IFC. Con el dataset del reto se
usará igual contra los 4 IFC de Técnicas Reunidas: solo habrá que añadir la correspondencia de nombres
de sus elementos.

El extractor es un parámetro (`--extractor`). Para medir uno nuevo, se implementa
`trazia.extraction.Extractor` y se registra en `EXTRACTORS` de `bench/runner.py`.

## Extractores medidos

| Nombre (`--extractor`) | Qué es |
| --- | --- |
| `etiquetas` | `LabelExtractor` del núcleo: líneas `ETIQUETA = valor unidad` |
| `tablas` | `trazia.extractors.DrawingExtractor`: tabla de boquillas por cabecera, datos de diseño, diámetro, faldón, tag del cajetín y cotas verticales comprobadas con la cadena faldón + virola + fondo = total |
| `combinado` | Los dos anteriores; los conflictos los bloquea el ensamblado |

## Resultado actual (20 equipos, semilla 2026)

| | rotulado | plano | escaneado |
| --- | --- | --- | --- |
| **etiquetas** · revisiones con modelo IFC | 40 / 40 | 0 / 40 | 0 / 40 |
| **etiquetas** · campos geométricos correctos | 100 % | 0 % | 0 % |
| **combinado** · revisiones con modelo IFC | 40 / 40 | 40 / 40 | 0 / 40 |
| **combinado** · campos geométricos correctos | 100 % | 100 % | 0 % |
| **combinado** · F1 de cambios | 100 % | 100 % | — |
| **combinado** · atributos correctos (valor + unidad) | 100 % | 100 % | 100 % |
| **combinado** · ECE de la confianza | 0,25 | 0,12 | 0,25 |

Con otra semilla (99, 40 equipos, solo «plano») el combinado da 80 de 80 modelos, 100 % de geometría y
F1 de cambios del 100 %.

Cómo leerlo:

- La cadena funciona de punta a punta: con el dato bien leído, el error es 0 mm, el IoU de IFC es 1 y
  el F1 de cambios es 100 %.
- `DrawingExtractor` lee los GA dibujados **de este generador**. Está pensado para su maqueta, así que
  el 100 % mide robustez dentro de ese formato (cotas giradas con dígitos invertidos, rótulos
  solapados, triángulos Δ), **no** frente a planos reales. Con el dataset del reto habrá que ajustar
  nombres de columnas, posición del cajetín y convenciones de cotas, y medir de nuevo.
- Los planos escaneados siguen a 0 %: falta OCR.
- La confianza no está calibrada: las cifras fijas (0,75 a 0,95) aciertan casi siempre. El ECE es la
  cifra que la calibración (B.6) tiene que bajar por debajo de 0,05.

Durante el desarrollo, el bench encontró dos fallos de lectura del plano:

- La cabecera de la tabla compartía altura con la cota de diámetro.
- El número del triángulo Δ se tomaba por una cota.

Los dos están corregidos y cubiertos por pruebas.

## Generador v2: ocho proveedores y cuatro conjuntos (DEC-21)

```bash
uv run python -m synthetic --conjunto todos          # generated/synthetic_v2/<conjunto>/
uv run python -m bench --entrada generated/synthetic_v2/s-dev --extractor combinado
```

Todo es sintético y lo dice en cada hoja («SYNTHETIC TEST DOCUMENT»). Los proveedores son
ficticios.

| Proveedor | Reservado | Idioma | Unidades | Lo que cambia |
| --- | --- | --- | --- | --- |
| atlas | no | en | mm | El estilo del generador v1 |
| iberica | no | es | mm | Coma decimal, punto de miles, tabla a la izquierda, Ø con línea de cota, «L.T.» |
| gulf | no | en | pulgadas | Fracciones de 1/16", NPS, psig, °F, lb; orden de columnas distinto |
| prairie | no | en | pies-pulgadas | Columna de rating, servicio delante, tabla abajo |
| nordic | no | en | mm | Texto de cotas horizontal, tabla abajo |
| levante | no | es | mm | Dos hojas (tabla en la 2), cotas de boquilla desde la tangente inferior |
| meridian | **sí** | en | mm | Rumbo horario desde el norte, cotas desde la tangente inferior, «I.D.» |
| cantabrico | **sí** | es | mm + NPS | Tamaños en pulgadas, cotas horizontales, cabeceras propias |

| Conjunto | Semilla | Casos | Proveedores | Notas |
| --- | --- | --- | --- | --- |
| `s-dev` | 2026 | 24 | los 6 públicos | Único conjunto para desarrollar y entrenar |
| `s-reservado` | 7919 | 16 | los 2 reservados | Solo mide generalización: no se mira caso a caso |
| `s-mecanico` | 4242 | 12 | atlas, iberica, gulf | Bomba con bancada; verdad de envolvente y bridas |
| `s-adversarial` | 6666 | 12 | atlas, iberica | Tres trampas por caso (DEC-32), sin hoja de datos |

- Cada caso lo dibuja un proveedor, por turno según su índice, y se entrega en tres degradaciones:
  `vectorial`, `escaneado_limpio` (200 ppp) y `escaneado_pobre` (120 ppp, JPEG, giro de hasta 1,5°).
- Uno de cada cuatro casos llega dentro de un paquete de proveedor (portada, índice, GA y placa con
  valores distractores). Uno de cada tres llega sin hoja de datos.
- Con proveedores en pulgadas, la verdad (en mm) cae en la rejilla de 1/16": el valor del plano es
  exacto y el error de conversión no se confunde con un error de lectura.
- Trampas: instrucción visible en inglés, instrucción en español, fila en blanco sobre blanco, texto
  de 2 pt, boquilla fantasma y metadatos del PDF. La verdad nunca cambia; el valor falso queda en
  `truth/<TAG>.json` para medir la tasa de envenenamiento.
- Las semillas se fijaron antes de medir nada y no se cambian por resultado.

### B frente al generador v2 (primera medición, sin tocar el extractor)

`combinado` (etiquetas + `DrawingExtractor`), degradación `vectorial`. Porcentaje de campos
correctos; «modelos» = revisiones que llegan a IFC.

| Conjunto | Proveedor | Geometría | Atributos | Modelos |
| --- | --- | --- | --- | --- |
| s-dev | atlas | 100 % | 100 % | 8/8 |
| s-dev | iberica | 14 % | 100 % | 0/8 |
| s-dev | gulf | 0 % | 25 % | 0/8 |
| s-dev | prairie | 0 % | 100 % | 0/8 |
| s-dev | nordic | 8 % | 100 % | 0/8 |
| s-dev | levante | 15 % | 25 % | 0/8 |
| s-reservado | meridian | 0 % | 72 % | 0/16 |
| s-reservado | cantabrico | 4 % | 81 % | 0/16 |

En los escaneados, la geometría es 0 % en todos los proveedores: no hay capa de texto.

**Lectura honesta.** `DrawingExtractor` se escribió mirando el generador v1, que es el estilo
`atlas`; por eso acierta todo ahí y casi nada en el resto. Los atributos se salvan cuando hay hoja
de datos. Este es el punto de partida del estudio: cualquier mejora de B sobre `s-dev` se medirá
después en `s-reservado`, que B no ha visto.

## Calibración, intervalos conformes y abstención (tarea 3.3, 30/10/2026)

```bash
uv run python -m bench.calibrar --datos generated/synthetic_v2   # → generated/calibration/
uv run python -m bench.calibrar --reusar                         # reajusta sin volver a leer
```

- **Qué hace.** Pasa B, C y D por `trazia.pipeline.process` sin calibrar sobre S-dev y
  S-reservado. Después ajusta en S-dev y mide en S-reservado, que tiene dos proveedores que S-dev no
  tiene.
  - Ajuste en dos mitades de S-dev, partidas por equipo: la primera para las curvas isotónicas
    por (estrategia, canal, vectorial o escaneado); la segunda para los cuantiles conformes y el
    umbral de abstención.
  - En S-dev, C usa la biblioteca sin el proveedor del caso, para no aprender la ventaja de tener
    una plantilla propia.
- **En el producto.** La etapa `calibrate` lee `generated/calibration/calibracion.json`. Si no
  existe, la etapa se omite y la confianza sale sin calibrar.
  - Rellena `confidence` (calibrada), `confidence_raw`, `interval` (conforme al 90 %) y el estado
    `abstained`. Un campo en abstención conserva su valor, pero hay que confirmarlo antes de aprobar.

Resultado en **S-reservado** (sintético, no visto en el ajuste):

| Estrategia | Campos | Acierto | ECE bruta | ECE calibrada | Cobertura del intervalo al 90 % | Abstención: se quedan · riesgo |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| B | 456 | 91,7 % | 0,191 | **0,035** | **100 %** | 85,5 % · 0,0 % |
| C | 954 | 77,8 % | 0,023 | 0,210 | 77,0 % | 24,3 % · 0,0 % |
| D | 1.963 | 76,7 % | 0,127 | 0,270 | **94,0 %** | 59,9 % · 10,9 % |

- **Objetivo del ROADMAP (ECE < 0,05 y cobertura ≥ 90 %):** B lo cumple. D cumple la cobertura,
  pero no la ECE. C no cumple ninguno de los dos.
- **En S-dev** el ajuste sí cumple: la ECE de D baja de 0,048 a 0,006 y la cobertura es del 97,6 %.
  El fallo en S-reservado es un cambio de reparto que S-dev no puede enseñar:
  - En S-dev, B lee las tablas de los seis proveedores. La geometría solo rellena 37 campos
    vectoriales sueltos y casi todos son errores (boquillas trampa). La curva aprende que
    «geometría sola» acierta el 8 %.
  - En S-reservado, B no entiende las tablas de los dos proveedores nuevos. La geometría rellena 593
    campos vectoriales y acierta el 95 %, pero la curva los deja en 0,37.
  - Lo mismo pasa con C: sin plantilla del mismo proveedor acierta menos, y de forma distinta.
- **Curva riesgo-cobertura de D en S-reservado:**

  | Umbral | Se quedan | Riesgo |
  | --- | --- | --- |
  | 0 | 100 % | 23,3 % |
  | 0,4 | 51 % | 5,9 % |
  | 0,8 | 38 % | 2,3 % |

  La ordenación sirve aunque los valores absolutos no estén bien calibrados.
- **Intervalos.** En las franjas de confianza baja el cuantil es enorme, del orden de ±70 veces el
  valor. Eso equivale a decir que el valor puede ser cualquiera, y el campo queda en abstención.
- **Límite de este método.** S-reservado se miró dos veces. Tras la primera se añadió el tipo de
  documento a la curva y la biblioteca sin el proveedor. No se ha ajustado nada más contra él. La
  próxima mejora necesita datos de otro reparto: el dataset real (R-ref), las correcciones humanas
  (3.8) o la fusión aprendida con señales de acuerdo entre canales (3.4).

## Hallazgos para el núcleo

1. **Un texto fuera de la página tumbaba la ingesta del PDF.** `ingest_bytes` limitaba la caja a
   [0, 1] coordenada a coordenada; un texto por completo fuera del borde dejaba `y0` y `y1`
   invertidos y `Source` rechazaba la línea, con lo que fallaba el documento entero. **Corregido:**
   ahora la caja se recorta al borde si el texto se sale en parte, y se descarta si queda fuera del
   todo. En los dos casos queda un aviso por página. Un PDF corrupto da `ValueError` en vez de una
   excepción de pdfminer. Prueba: `tests/test_lectura_ingest.py`.

## Siguiente paso

1. **OCR** para el estilo `escaneado`: convertir la imagen en líneas con caja, para que
   `DrawingExtractor` funcione igual.
2. **Calibración** (B.6): usar los pares (confianza, acierto) de `report.json` para ajustar las
   confianzas y bajar el ECE.
3. Con el dataset del reto: ejecutar `bench` contra los 4 IFC de referencia y ajustar
   `DrawingExtractor` a sus planos. Medir siempre separando lo sintético de lo real.
