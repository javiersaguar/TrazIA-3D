# Pulido del frontend · 08/11/2026

Base: 4929cef. Pruebas locales con datos sintéticos, API aislada 8059 y web de producción
3356. Chrome con SwiftShader CPU: no se ha medido el FPS nativo de la RTX ni el tiempo humano.

## Copiloto

El panel ocupa una columna propia en escritorio. El contenido reduce su ancho; no se coloca
por encima. En pantallas menores se apila antes del contenido. La prueba contrasta las cajas
de ambos elementos y comprueba ausencia de desbordamiento a 800 px. Se conserva la pregunta
escrita al navegar, cerrar/reabrir el panel o recargar, durante la sesión del navegador.

## Proponer cambios

Selector de proyecto, equipo, revisión y pieza sobre el visor. Modelo a todo el ancho, seguido
del formulario en columnas según el espacio disponible, también al abrir el Copiloto.

- Valores iniciales del catálogo real y restablecimiento por campo. Solo se envían cambios;
  cambiar de unidad conserva la magnitud. Normalización y validación siguen en la API.
- Recorrido entre boquillas, virola, fondos, faldón, silletas, techo, tramos y accesorios, según
  la familia. Las dimensiones compartidas del modelo siguen siendo comunes; no se inventan
  parámetros independientes para una pieza que no los tiene.
- Chat, reglas y altas/bajas en secciones desplegables para evitar una columna interminable.
- Borradores separados por API/proyecto/equipo/revisión, incluso el alta que aún no se ha
  incluido en el lote. Se conservan actor, motivo, cambios de todas las piezas y propuesta.
- Al volver, la propuesta se consulta de nuevo al servidor; no se confía en un estado de
  confirmación almacenado. Si había un trabajo en curso, se recupera su seguimiento.

El almacenamiento es `sessionStorage`, no persistencia en servidor ni una aprobación. Dura
la sesión de esa pestaña; si el navegador lo bloquea, se conserva en memoria mientras la app
permanece abierta. Ningún borrador se aplica automáticamente.

## Landing

Mismos textos, secciones, geometría, materiales y recorrido visual:

- Límite de 650.000 píxeles por escena de portada, frente a 1.000.000; resolución adaptativa.
  **35 % menos de techo de píxeles**, no una mejora de FPS medida. Los visores del producto
  conservan su presupuesto anterior. Una escena pequeña puede estar por debajo de ambos límites.
- Caché de referencias de materiales en la animación plano→IFC. No se recorren las dos
  jerarquías de mallas ni se reescriben opacidades cuando el avance no cambia.
- El titular deja de rotar fuera de pantalla, con la pestaña oculta o con movimiento reducido.
- El foco del cursor agrupa las coordenadas por fotograma y evita actualizar React en cada
  evento de puntero. Conserva el mismo gradiente y movimiento.
- La precarga de PDF/IFC empieza más cerca de la sección para no competir tan pronto con el
  hero. Se conserva y verifica la pausa de escenas fuera de pantalla.

`render.json` registra la prueba CPU. No acredita LCP, INP ni fluidez en todos los equipos.

## Validación

- Typecheck, lint, build y **58 pruebas unitarias** correctos. Permanece el aviso anterior de
  React Compiler/TanStack Table en la tabla de Proyecto.
- **11 recorridos Playwright** correctos: seis de layout/persistencia/K8, cuatro de regresión
  3D y uno de recuperación de previsualización después de navegar.
- Capturas inspeccionadas: `edicion-claro.png`, `edicion-oscuro.png`, `copiloto-oscuro.png` y
  `landing-holograma.png`. Las pruebas K8 actualizan también sus capturas de la interfaz.
- Sin dependencias nuevas, cambios de API, originales privados ni ejecución de modelos.
