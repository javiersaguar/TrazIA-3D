# Producto y preparación previa · 02/11/2026

Base: main 01b2699. Trabajo aislado en feat/web-producto, worktree TrazIA-3D-producto.
Sin cambios en extracción/OCR, modelos de datos, API, dependencias ni datos privados.

## Navegación y organización

- Ajustes en la rueda del pie de la barra lateral. El cambio de tema está dentro de Ajustes.
- Equipo muestra los nombres; no muestra el reparto de responsabilidades.
- Auditoría sale del producto visible. Su registro de servidor se conserva.
- Desaparecen las letras/números de acceso rápido de los enlaces laterales. Los atajos
  siguen operativos, incluidos los enlaces previos.
- Documentos agrupa familias, proyectos y diseños. Se pueden crear familias/proyectos,
  añadir documentos, reasignar un diseño, filtrar por familia/proyecto, buscar y descargar.
  Metadatos en localStorage y archivos en IndexedDB; persisten al recargar. Límite 50 MB por
  archivo y errores recuperables. No es un catálogo compartido ni lanza extracción automática.
  Crear una clasificación no inventa un generador geométrico.
- Modelo agrupa Revisión, Cambios y Modelo 3D mediante URL `vista`. Solo se monta el espacio
  activo. La geometría del visor viene del IFC, con selección compartida y revisiones A/B.
- Lotes e informes comparte ruta. Ambas secciones conservan su aviso de demostración.
- Estudio se integra en Bench como «Comparar estrategias». No tiene enlace de menú propio.
- Las rutas antiguas redirigen a sus vistas agrupadas, incluidos comandos y accesos directos.

## Portada y 3D

- Sin botón 360° en el plano ilustrativo de portada. Los controles del visor de ingeniería
  y del laboratorio permanecen disponibles.
- Holograma → modelo: cámara fija, sin giro automático ni arrastre. La transformación por
  scroll y la inspección visual de detalles permanecen.
- Holograma claro usa BRAND.skyDeep y mezcla normal para conservar la rejilla azul sobre
  superficies claras; el tema oscuro mantiene la mezcla aditiva.
- Cómo funciona: cuatro dibujos SVG rehechos, cota y evidencia legibles, contornos cerrados,
  línea continua entre números y aparición progresiva al deslizar. En ancho reducido se apilan
  y la línea pasa a vertical. Con movimiento reducido se muestra el estado estático final.
- Halo del puntero fijo al viewport, azul más oscuro en claro; sigue disponible después de
  la cabecera y respeta movimiento reducido y dispositivos sin puntero preciso.

## Datos del estudio

Informe completo sintético de 13 variantes, generado 01/11/2026 01:02:20 UTC, copiado sin
modificar a `web/public/demo/json/estudio.json`. SHA-256:
`794ee71813523101c96f72a24a99dd025d29f7126c407c1dbae2ee64c51fd872`.
Resumen de portada con la misma procedencia en `web/src/lib/data/study-summary.json`:

| Enfoque | Variante representada | Puntuación |
| --- | --- | ---: |
| A | a_geometria, sin modelo multimodal | 0,5784 |
| B | b_reglas+ocr, CPU | 0,6089 |
| C | c_rag, recuperación ligera | 0,5995 |
| D | d_hibrido, fusión/calibración v6 | 0,7077 |

Cada fila muestra las métricas al apuntar, enfocar o pulsar: atributos, geometría,
alucinación, citas, F1 de cambios, cobertura de intervalos, coste, ECE y tiempo, con IC95
para la puntuación y el alcance de la variante. El A con Qwen se midió en otro subconjunto:
no se mezcla con A geométrico. Ninguna puntuación se presenta como validación TR ni como
porcentaje de IFC aprobados. No se ha repetido un estudio GPU para esta actualización.

## Verificación

- Typecheck y build de producción correctos; lint sin errores. Se conserva el aviso previo
  de React Compiler/TanStack Table en Resumen.
- 42 pruebas unitarias correctas (15 archivos).
- Suite humo sin API: 30 correctas y 9 omisiones de casos conectados, en 2,6 min.
- Suite humo con API aislada: 38 correctas y una omisión del caso exclusivo sin API, en 3,3 min.
  Incluye persistencia de revisión, deshacer, IFC real del servidor, BCF, marcas, SSE y el Copiloto con respuestas de interfaz inyectadas.
- Seis pruebas de producto adicionales sobre producción (20,1 s): catálogo persistente con descarga,
  navegación/Ajustes, métricas/halo, espacio agrupado y cámara del holograma inmóvil durante
  la transición y al arrastrar, más trazos fuera de pantalla con movimiento reducido. Ejecución CPU con Chrome/SwiftShader, sin medir rendimiento GPU.
- Capturas en `docs/capturas/producto/`: 11 imágenes, claro/oscuro de Documentos, Modelo, Cómo funciona,
  Holograma y estrategias, más la vista móvil de Cómo funciona. Se mantienen las capturas históricas sin sobrescribirlas.
- API efímera de pruebas en 8044 retirada; no se detienen los servicios del usuario.

## Preparación y pendientes

[PREPARACION_25NOV](../PREPARACION_25NOV.md) incorpora las confirmaciones del equipo y enlaza
los borradores de storyboard/pitch, preguntas, trabajo previo, instalación y licencias.
El roadmap marca subtareas concretas hechas, sin cerrar ensayos, material físico, presentación,
vídeo, tag ni recepción del dataset que deben confirmarse allí.

3.7 conserva los 85 errores de extracción; no se promete un presupuesto para 1.600 IFC correctos.
El diagnóstico CPU y la medición ya existen; corregir OCR/extracción requiere coordinar la
propiedad de Lectura antes de editarla. No se ha cambiado su código en esta sesión.
3.8 necesita correcciones humanas representativas y demostrar mejora independiente; la regresión
de prioridades y la propuesta D siguen pendientes. E.5 continúa pospuesta.

## Comandos

Desde `web/`: `corepack pnpm@10.18.0 typecheck`, `lint`, `test:unit` y `build`.
Para humo sin API, en PowerShell: `$env:PW_CPU_ONLY='1'; $env:PW_PORT='3342'` y
`corepack pnpm@10.18.0 test:e2e`. Para producto contra el build:
`$env:PW_USE_BUILD='1'` y `corepack pnpm@10.18.0 exec playwright test tests/e2e/producto.spec.ts --project=humo`.
Para conectado, levantar previamente una API aislada con datos sintéticos, definir
`NEXT_PUBLIC_API_URL`, `PW_EXTERNAL_API=1` y otro `PW_PORT`, y repetir humo. La ejecución
registrada utilizó la imagen local CPU `trazia-plataforma:20261102-cpu-v1` en 8044 con
almacén tmpfs, CORS para 3341, CUDA_VISIBLE_DEVICES=-1 y TRAZIA_VISION_OFFLINE=1.
No usar los almacenes o servicios activos del equipo para la prueba que modifica revisiones.
