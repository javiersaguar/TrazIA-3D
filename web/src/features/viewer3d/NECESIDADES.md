# Integración del 3D · estado 30/10/2026

- Paso 0 incorporado desde main (`976d8dd`). Contratos y dependencias disponibles; Vitest y
  test:unit ya están instalados. No se modifica el manifiesto ni el lockfile.
- ShowcaseVessel, EquipmentThumb y HologramToReal funcionan sin providers de la app. El
  consumidor los carga con next/dynamic({ssr:false}); las firmas se conservan y las ampliaciones
  son opcionales. La portada definitiva y su presupuesto de carga quedan para la integración con A.
- Cambios ya no tiene temporizador de pantalla: el reloj único vive en useFrame/refs del visor.
  onPlayingChange/onStep sincronizan la narración y la lista sin React por frame. Scrub pausa ambos.
- El WASM 0.0.78 se sirve localmente en /wasm/. La geometría del visor procede siempre del IFC.
- drei conserva tipos transitivos de three-mesh-bvh 0.8; el árbol y raycast usan el 0.9 directo.
  three-bvh-csg 0.0.18 emite un aviso maxLeafSize deprecado. Funciona, sin parchear dependencias.
- Como el plano es un alzado ortográfico canónico. La alineación automática de un plano arbitrario
  necesita su calibración, que no se inventa en el frontend.

## API y aprobación

La API 8010 rechaza CORS desde localhost:3300/3311. No se ha editado api/app.py ni reiniciado 8010.
Para las pruebas se usa una instancia aislada en 8011, con CORSMiddleware añadido solo al arrancar,
exposición de ETag y datos sintéticos en generated/e2e-3d-8011. PW_EXTERNAL_API=1 evita que Playwright
levante otra API. La aprobación usa If-Match/Idempotency-Key; un 412 exige recargar y revisar.
Si se quiere conectar la web de 3300 directamente a 8010, Plataforma deberá ampliar sus orígenes.

## 2.6 pendiente de autorización

No se modifican src/trazia/families/, src/trazia/ifc.py ni public/demo/ifc/ sin la confirmación
expresa de Javier indicada en el encargo. El IFC actual no tiene bridas, orejetas ni manway de
detalle: el holograma IFC solo amplía detalles existentes. Los tres recortes completos aparecen
solo en los modelos procedurales, etiquetados como ilustrativos.

Al enriquecer el IFC habrá que actualizar también la expectativa de siete productos de
web/tests/e2e/humo.spec.ts (fuera del reparto del Agente 2), conservando las pruebas de identidad
GUID y la lectura real del IFC. Los componentes nuevos requieren GUID y procedencia de norma.
