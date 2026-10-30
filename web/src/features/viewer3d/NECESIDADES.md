# Integración del 3D · cierre 30/10/2026

- Contratos implementados e integrados con feat/web-marca. ShowcaseVessel, EquipmentThumb y
  HologramToReal se cargan con next/dynamic ssr:false, funcionan sin providers de la app y
  conservan sus firmas. progressValue y controls son ampliaciones opcionales para la portada.
- El reloj de Cambios vive en useFrame/refs; onStep/onPlayingChange sincronizan la pantalla.
- El worker lee el IFC y sus Psets. Los detalles conservan identidad propia y ParentComponentId
  los vincula con el elemento que posee evidencia. Ninguna vista IFC añade piezas procedurales.
- IFC públicos regenerados: A 73 productos y B 83. details=True habilita el detalle de demostración;
  la API lo solicita para sintéticos. El núcleo conserva por defecto su LOD y no inventa campos.
- El Pset distingue patrones de tabla, clase supuesta y proporciones ilustrativas. La lectura de
  originales, el cálculo mecánico y la certificación normativa no se sustituyen por esta demo.
- CORS actualizado para 3300/3310/3311. La API 8010 existente no se detiene. Pruebas con API
  aislada 8011 y PW_EXTERNAL_API=1; no se necesita el anterior middleware añadido en memoria.
- Dependencias suficientes, sin cambios de manifiesto. three-bvh-csg 0.0.18 emite un aviso de
  maxLeafSize deprecado; funciona con el BVH fijado. No quedan dependencias pendientes de A.
- Como el plano es un alzado ortográfico canónico. Alinear un plano arbitrario requiere su
  calibración real, que no se deduce de estos ejemplos sintéticos.

Validación y limitaciones de medida: docs/agentes/INFORME_FRONTEND_3D.md.
