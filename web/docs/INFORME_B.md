# Informe del 3D: visor IFC, planta, comparación de revisiones y «del plano al modelo»

Rama `feat/web-3d`, integrada en `main`. Estado a 26/10/2026.
Carpetas: `src/features/viewer3d/`, `plant/`, `delta3d/`, `src/workers/`, `src/app/lab/` y
`public/wasm/`. Capturas y mediciones en [`docs/capturas-3d/`](capturas-3d/).

## Qué está hecho

| Parte | Detalle |
| --- | --- |
| Carga IFC | `web-ifc` 0.0.78 en un Web Worker con el WASM servido desde `/wasm/`. Mallas, GlobalId, Name, tipo IFC y Psets, con transferencia sin copia. La UI no se bloquea |
| Identidad | Los ids semánticos (`shell`, `head-top`, `head-bottom`, `skirt`, `nozzle:N1`…) salen del `Name` del IFC (`semantic.ts`) |
| `IfcViewer` | Vistas iso, alzado, planta y «Como el plano» (ortográfica). Modos sólido, rayos X y explosionado. Corte con relleno rayado, cotas 3D con estética de plano, selección y hover con zona de clic ampliada, árbol de elementos, encuadre, captura PNG, pantalla completa y leyenda de estados |
| `PlantScene` | Planta isométrica con instancias del IFC por área, modos «Vista general» y «Seguir equipo», etiquetas por tag y aviso de distribución ilustrativa |
| `RevisionMorph` | Emparejamiento por GlobalId, fantasma azul de la rev A e interpolación por elemento. Al terminar, mallas exactas de la rev B. Marcadores Δ con la magnitud, altas y bajas, barra de avance propia y modo «Seguir el cambio» |
| Firma | `/lab/firma`: el plano se levanta y se convierte en el modelo leído del IFC. Se puede pausar o saltar, y respeta el movimiento reducido |
| Laboratorio | `/lab/3d`: los tres componentes aislados y el botón «Medir 5 s» |
| Pruebas | 9 pruebas unitarias del emparejamiento y la interpolación (`pnpm test:unit`) |
| Integración | Proyecto, Revisión y Cambios usan el 3D real. Seleccionar una evidencia del PDF resalta su elemento en el IFC |

La regla del proyecto se cumple: lo que se ve sale del IFC. Las cotas usan los valores del JSON,
ancladas a elementos del IFC.

## Rendimiento

En una AMD Radeon 610M integrada (Direct3D 11 vía ANGLE):

| Escenario | fps medios | p95 |
| --- | --- | --- |
| Visor en el laboratorio, ~630×680 px | 97,5 | 22,8 ms |
| Ventana completa **antes** del ajuste (SSAO a resolución completa) | 38,8 | 39,2 ms |
| Ventana completa 1920×1080 **después** del ajuste | 239,1 | 4,3 ms |

Ajuste aplicado (`stage.tsx`):

- Un presupuesto de ~1 MP para la resolución de render: el coste no crece al maximizar.
- El SSAO y el compositor a media resolución, con reescalado según profundidad.
- Render bajo demanda (`frameloop="demand"`).

La última medición se tomó maximizando el visor por CSS, porque el panel del navegador de la app no
concede pantalla completa real.

## Cambios al cerrar la integración

- `three-mesh-bvh` unificado en 0.9.16 con un override de pnpm (antes `drei` traía la 0.8.3).
- Etiquetas de la planta sobre la cabeza de cada recipiente, porque al pie se solapaban. El aviso
  «ilustrativo» queda en el tooltip y en el rótulo de la escena.
- Pantalla Cambios:
  - Una sola barra de avance: la del visor, que avisa con `onProgress` y pausa la reproducción de
    la pantalla.
  - La narración va bajo el lienzo, para no tapar la leyenda del visor.
- El botón flotante del Copiloto se oculta en Revisión y Cambios, porque tapaba los controles del
  visor.

## Límites conocidos

- «Como el plano» da un alzado ortográfico canónico. Para alinearlo con un plano concreto hace falta
  la transformación o calibración del plano, que tendrá que aportar el núcleo.
- El IFC del núcleo no marca supuestos ni conflictos. El visor admite un mapa opcional de estados
  por id semántico; sin él muestra el DRAFT leído del IFC.
- La planta repite el IFC de V-101 para enseñar escala: es ilustrativa y se rotula así.
- Las mediciones son de un único equipo (GPU integrada). Hay que repetirlas en el portátil de la
  demo antes del 27/11.
