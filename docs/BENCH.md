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
