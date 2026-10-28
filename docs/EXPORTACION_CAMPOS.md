# Tabla de campos con evidencia

Exportación de solo lectura para revisión de ingeniería (ROADMAP C.6). Funciona con CPU,
sin red ni modelo de IA; no requiere el frontend.

```powershell
uv run trazia fields examples/vessel_rev_a.json -o generated/revision_a.csv
uv run trazia fields examples/vessel_rev_a.json -o generated/revision_a.xlsx
```

Cada fila corresponde a una ruta estable del contrato. Incluye valor/unidad, estado y confianza,
identificador/nombre/SHA del documento, página o hoja/celda, localizador, bbox, texto/unidad
original si existen, canal/estrategia/modelo/prompt, respaldo, intervalo y alternativas con sus
propias evidencias. La huella de revisión y el indicador DRAFT/APPROVED se repiten en las filas.
Los datos ausentes quedan vacíos, no se rellenan con supuestos. `dataset=synthetic` sigue visible.

La tabla conserva una aprobación válida, pero nunca aprueba ni modifica la revisión.
Un objeto con aprobación obsoleta se rechaza. Las huellas de documentos se copian del contrato:
esta exportación no vuelve a verificar los originales ni acredita autenticidad de la fuente.
Las correcciones hechas en Excel no se importan automáticamente ni cambian el JSON de origen.

El CSV usa UTF-8 con BOM y separador coma. Excel puede abrirlo con **Datos → Desde texto/CSV**.
Las cadenas que empiezan por un signo de fórmula se prefijan con apóstrofo; los números siguen
siendo numéricos. En XLSX las cadenas se guardan como texto literal. La hoja Campos tiene filtros
y cabeceras fijas. Bbox y alternativas se guardan como JSON dentro de una celda.
Excel no admite textos de más de 32767 caracteres ni algunos controles XML: se devuelve error
sin escribir una tabla truncada. CSV conserva esos textos largos.
