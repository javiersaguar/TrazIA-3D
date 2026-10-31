# Unidades y referencia · C.1, C.2 y C.4 (01/11)

`trazia.units.normalize` usa Pint, sin tablas de factores duplicadas en los lectores. Se conecta a la extracción por etiquetas, al lector de dibujo y al PATCH de revisión. La interfaz antigua que solo devuelve número/unidad rechaza una presión absoluta o una interpretación que no puede explicar.

| Magnitud | Entradas admitidas | Unidad de salida |
| --- | --- | --- |
| Longitud | mm, cm, m, in, fracciones y ft-in | mm |
| Presión | bar(g), barg, bar(a), bara, kPa, MPa, psi/psig/psia, kgf/cm² | bar o bara según base |
| Temperatura | °C, °F | °C |
| Masa | kg, t, lb | kg |

`text_original` y `unit_original` permanecen en Source. Una corrección humana cambia el canal a humano y conserva en auditoría el valor/unidad anterior. No se interpreta bara como barg: no se suma ni resta una atmósfera sin contexto. La forma kg/cm² se interpreta como kgf/cm² con aviso de supuesto; no desaparece la ambigüedad física del original.

`2.000` y `2,000` requieren contexto de separador. En PATCH puede enviarse `decimal_separator: "."` o `","`. Se rechazan valores incompatibles/ambiguos con 422 antes de cambiar el ETag, escribir correcciones o mutar la revisión. Cambiar solo una unidad exige aportar también el valor. El normalizador no recupera una cifra ausente ni certifica que haya sido leída correctamente.

## Referencia

Se mantiene el contrato 0.3: longitudes mm; IFC metros; +Z vertical; azimut interno 0° = +X, 90° = +Y, antihorario visto desde +Z. La web transforma `(x,y,z) IFC → (x,z,-y)` y el BCF aplica la inversa. `trazia.reference` centraliza conversiones y posiciones de boquillas. Si se declara Norte de planta, convierte un rumbo horario desde ese Norte al azimut interno.

`build_ifc(..., plant_north_deg=...)` acepta Norte explícito y lo escribe en `TrueNorth`. El Pset `TrazIA_ReferenceFrame` declara ejes/unidades/convenio y que el convenio de TR no está verificado. Sin Norte declarado no se inventa TrueNorth. No se ha cambiado el esquema de model.py.

El PDF del reto menciona coordenadas globales/posición relativa en PLOT PLAN (p. 8); no proporciona en su texto el convenio de azimut/Norte del IFC de referencia. **C.4 sigue parcial** hasta contrastarlo con esa referencia. Estas utilidades no demuestran esa compatibilidad externa.

## Pruebas

`tests/test_plataforma_units.py`, `test_api_units.py` y `test_plataforma_reference.py` comprueban conversiones, separadores, evidencia original, rechazo atómico y coordenadas/TrueNorth reales en IFC. El conjunto Python completo pasó con 346 pruebas y una omitida; la evidencia de unidades nueva se elimina únicamente de una copia al contrastar la huella histórica de referencia.
