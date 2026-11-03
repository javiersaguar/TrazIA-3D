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


## 03/11 · traza, ritmo e inspector

- Paso normal: 1.050 ms frente a 2.600 ms; velocidades 0,5/1/2/3×. Traza activa
  de 4,5 px, halo de conexión, flechas y tres partículas cada 0,78 s. Caja activa con
  fondo azul y halo pulsante. Pausa y movimiento reducido detienen la animación.
- Pulsar una caja abre un inspector sobre el grafo, con descripción, identificación de
  estrategia/trabajo, eventos reales OK/error/omitido, archivos y mensajes del servidor.
  Escape o cerrar devuelve foco a la caja. La selección no inventa flujo real en un trabajo
  finalizado ni transforma eventos de demo en ejecución API.
- El almacén conserva estado del trabajo, estrategia y nombres de entradas. Las respuestas
  de un trabajo anterior no sobreescriben el nuevo. Sin cambios de contrato del backend.
- Porcentaje de ingesta: documentos con respuesta / entradas conocidas, deduplicando por
  nombre y evitando nombres ambiguos. Se etiqueta cobertura, incluidos errores/duplicados,
  no éxito ni tiempo restante. Prueba de 50 % parcial y 100 % con error conservado.
- Otras fases: porcentaje pendiente sin informar mientras la API no publica un denominador;
  100 % solo en tramos con resultados OK, sin errores, al terminar el trabajo correctamente.
  Fases sin eventos, omitidas, canceladas o fallidas no se rellenan con porcentajes ficticios.
- Verificación: 46 unitarias, tipos, lint y build; cuatro pruebas de navegador sin API y una
  con API aislada/SSE real. Se verifica inspector con IFC finalizado, 100 % y mensajes reales.
  Captura adicional: docs/capturas/pipeline-inspector-real.png. Sin GPU ni datos privados.
