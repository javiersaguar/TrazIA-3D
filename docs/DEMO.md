# Guion de prueba y presentación

Ejecutar `uv run trazia serve` y abrir http://127.0.0.1:8501.
Todos los datos mostrados son sintéticos; decirlo al iniciar.

1. **Problema, 0:00–0:45.** Los datos de un GA y su HDM deben alimentar un modelo
   trazable y conservarse entre revisiones.
2. **Documento, 0:45–1:30.** En Modelo y revisión, seleccionar altura o presión para
   mostrar PDF/celda de origen. En Documentos están hashes y revisiones independientes.
3. **Extracción, 1:30–2:30.** Cargar los PDF/Excel A de `examples/documents/`, asignar
   IDs estables `GA-V101` y `HDM-V101`, elegir `synthetic`, ingerir y construir DRAFT.
   Explicar que este baseline usa etiquetas y el adaptador IA está pendiente.
4. **Modelo, 2:30–3:45.** Orbitar IFC, aislar N3, ver fondos y faldón. Descargar JSON
   e IFC DRAFT. Revisar y registrar el checkpoint humano para exportar aprobado.
5. **Cambio, 3:45–5:00.** Comparar A/B. N3 sube 200 mm; faldón +150 mm; virola +500 mm;
   peso +800 kg y boquilla N4 nueva. Mostrar valores, unidades, evidencia e impacto.
6. **Límites, 5:00–6:00.** Familia vertical simplificada, sin OCR/visión general ni métricas
   oficiales. Siguiente experimento: un par GA/HDM del organizador con IFC de referencia.

Para comprobar el bloqueo, modificar un valor después de aprobar: desaparece la aprobación
y vuelve DRAFT. El JSON previo descargado conserva la versión anterior.
