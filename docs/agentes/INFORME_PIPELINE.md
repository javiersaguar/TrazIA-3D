# Pipeline · 03/11/2026

Trabajo en `feat/pipeline-recorridos`, worktree propio desde main 55b1e02.

## Cambios

- Mapa lógico A/B/C/D: solo canales pertinentes, condiciones visibles y incorporación de
  canales realmente observados. Los extractores comparten columna; los colectores discurren
  entre columnas. Se elimina la conexión que saltaba calibración atravesando su tarjeta.
- Explicación independiente del procesamiento: reproducción, pausa, inicio, anterior/siguiente,
  deslizador, velocidades 0,5/1/2×, fases seleccionables, navegación por teclado y detalle.
- Vista general y seguimiento con encuadre de la etapa; desplazamiento manual interrumpe el
  seguimiento. Ampliación reversible con Escape. Partículas recorren las conexiones activas.
- Eventos reales conservan estado, omisiones, errores y mensaje del servidor. Sin API no se
  presentan los eventos simulados como reales. Las condiciones del mapa no acreditan ejecución.
- Respeta cambios de movimiento reducido; pausa cuando la tarjeta o pestaña están ocultas.
  No se ejecuta backend por reproducir la explicación. Sin dependencias nuevas ni cambios 3D.
- El guion offline deja de llamar «no implementadas» a etapas que sencillamente no simula.

## Verificación

- Typecheck, lint (aviso previo TanStack), 42 unitarias y build correctos.
- Tres pruebas de navegador: A/B/C/D sin aristas atravesando tarjetas ajenas, reproducción/
  pausa/seguimiento/deslizador/Escape/movimiento reducido, teclado/ausencia de API/móvil.
  La comprobación geométrica muestrea las rutas SVG reales contra los rectángulos de pantalla.
- Una cuarta prueba contra API aislada (8054), con build conectada (3351), procesa la demo,
  recibe SSE, comprueba la finalización e inspecciona IFC. Sin GPU ni servicios ajenos modificados.
- Capturas en docs/capturas/pipeline-d-{oscuro,claro}.png. Preview local: 3350 sin API, 3351 con API aislada.

## Alcance

El mapa explica dependencias lógicas; no promete paralelismo ni orden temporal de todos los
canales. En observación solo se muestran contadores recibidos. El transporte SSE no cambia.
Los proveedores, variantes y documentos determinan qué canales condicionales se ejecutan.
