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

## Resultado actual (20 equipos, semilla 2026, extractor de etiquetas)

| | rotulado | plano | escaneado |
| --- | --- | --- | --- |
| Revisiones con modelo IFC | 40 / 40 | 0 / 40 | 0 / 40 |
| Campos geométricos correctos | 100 % | 0 % | 0 % |
| Atributos correctos (valor + unidad) | 100 % | 100 % | 100 % |
| F1 de cambios | 100 % | — | — |
| ECE de la confianza | 0,25 | 0,25 | 0,25 |

Cómo leerlo:

- La cadena funciona de punta a punta cuando el dato está rotulado: el error es 0 mm, el IoU de IFC es
  1 y el F1 de cambios es 100 %.
- El extractor actual **no lee planos dibujados ni escaneados**. Los atributos salen bien en todos los
  estilos porque vienen del Excel.
- La confianza fija de 0,75 está **mal calibrada** (acierta el 100 %). El ECE de 0,25 es la cifra que
  la calibración (B.6) tiene que bajar por debajo de 0,05.

## Hallazgos para el núcleo

1. **Un texto fuera de la página tumba la ingesta del PDF.** `ingest_bytes` limita la caja a [0, 1]
   coordenada a coordenada. Si un texto queda por completo encima del borde, `y0` y `y1` acaban
   invertidos y `Source` lanza un error de validación. Esto hace fallar el documento entero. En planos
   reales con anotaciones en el margen puede pasar. Propuesta: descartar o recortar esa línea y dejar
   un aviso, en vez de abortar. El bench registra ahora estos casos como ingesta fallida en lugar de
   detenerse.

## Siguiente paso

El hueco más grande con más peso es la geometría del estilo `plano` (35 %). Primero conviene un
extractor de **tablas vectoriales** (tabla de boquillas y datos de diseño) y de **cotas** en PDF
vectorial (ROADMAP B.1). Después, OCR para `escaneado`. Cada mejora se medirá aquí con las mismas
cifras.
