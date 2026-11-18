# Trabajo previo al evento · BORRADOR

Equipo: Javier Saguar Antona, Iria Lozano Carrasco, Miguel Vera del Castillo y Alejandro Cuevas Cid.

Este borrador describe la base existente al 18/11/2026: 227 commits en `main` desde el 26/10/2026.
Debe revisarse y cerrarse al inicio del evento con el commit exacto y el tag
`pre-hackathon-baseline`, con `uv run python scripts/arranque_evento.py --aplicar`.
El tag todavía no se crea.

Todo lo que se enseña de esta base es sintético. Ningún documento, plano, modelo o salida de
Técnicas Reunidas forma parte de ella.

## Base preparada

### Lectura de documentos y modelo

- Núcleo Python y contrato 0.3: valor, unidad, fuente, confianza, estado y aprobación por campo.
- Ingesta de PDF vectorial y escaneado, XLSX e imágenes, con huella SHA-256 de cada original.
- Cuatro estrategias de lectura (A geometría, B reglas con OCR, C recuperación y D híbrida),
  con calibración, intervalos y abstención.
- Familias paramétricas y exportación IFC4, IFC4X3 e IFC2X3 con trazabilidad y GUID estables.
- Comparación de revisiones, BCF 2.1 y auditoría automática de geometría, unidades y propiedades IFC.
- Edición asistida (K.0–K.8): propuestas de cambio con vista previa del IFC, revisión derivada,
  deshacer, plano derivado en PDF, piezas reversibles y planos GA desde IFC.

### Plataforma

- API FastAPI con eventos SSE, cola Redis y workers, Postgres o SQLite, cachés y modo offline.
- Lote por carpeta y cuatro notebooks de Databricks preparados para la plataforma del evento:
  comprobación del entorno, proceso del lote, perfil del dataset y evaluación contra los IFC de
  referencia. Solo trabajan con agregados; ningún dato del reto sale de la plataforma.

### Web

- Next.js con portada, documentos por familias y proyectos, pipeline por estrategia, revisión,
  cambios entre revisiones, modelo 3D que lee el IFC, estudio, lote, impacto y copiloto.
- Catálogo sintético de 18 familias con 72 diseños: 56 con plano GA e IFC paramétrico y 16 bocetos.
  Desde Modelo › Diseños se ven en 3D y se editan en directo; el IFC se regenera en el navegador.

### Estudio y evidencias

- Banco sintético y estudio A/B/C/D con intervalos del 95 %, en `docs/ESTUDIO.md`.
- Mediciones y sus límites en `docs/evidencias/`. Proceden de sintéticos y no acreditan fidelidad
  en los planos que se entreguen en el evento.

### Presentación y preparación del evento

- Pitch web de seis minutos (`pitch/web`), exportable a `pitch/TrazIA-3D.pptx` y PDF.
- Guion de la demo con voz, pantallas, tomas y clips (`docs/GUION_DEMO.md`), vídeo de producto
  de 45 s (`promo/trazia-hackathon`) y grabación automática del vídeo de respaldo.
- Automatización del evento (`docs/AUTOMATIZACION.md`): guardián de datos en el pre-commit,
  cifras del lote al pitch, triaje de fallos, arranque y reinicio de la demo y comprobación de entrega.

### Calidad

- Pruebas de Python (538 al 18/11), pruebas unitarias de la web y del pitch y recorridos e2e con
  Playwright. CI en GitHub con Ubuntu y Windows.

## Pendiente de realizar con el equipo y los datos del evento

Recepción e inventario del dataset, permisos de procesamiento, referencia espacial y contraste
con los IFC de TR. Adaptación y evaluación real de los lectores, correcciones humanas, estudio
y demostración sobre los datos recibidos. Presentación, grabaciones y montaje finales.

## Registro que se cerrará al empezar

- Fecha/hora de corte: pendiente.
- Commit exacto de la base: pendiente.
- Tag publicado: pendiente.
- Declaración entregada a la organización: pendiente.
- Trabajo nuevo durante el evento: registrar por commit y evidencia, separado de esta base.

No se incluyen documentos confidenciales ni claves en esta declaración o en el repositorio.
