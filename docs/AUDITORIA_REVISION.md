# Auditoría de revisión y aprendizaje · 31/10

Base revisada: `main` en `8713f7a`; trabajo aislado en `feat/cierre-plataforma-visor`.
El contrato de datos 0.3 se conserva. No se cambian lectores, OCR, proveedores, entrenamientos
ni el visor 3D.

| Punto | Existía | Cierre o límite de esta sesión |
| --- | --- | --- |
| E.1 Validación | Geometría del contrato, unidades canónicas, fuentes y páginas | Errores 422 con campo, mensaje y acción; diagnóstico de alternativas equivalentes/discrepantes y posible solape radial. El solape es un cribado advertido, no una comprobación normativa. Avisos accesibles desde la revisión. |
| E.2 Prioridad | Impacto × (1 − confianza), abstenciones primero | Se incorporan conflictos y todos los campos trazados de la revisión, incluidos coordenadas y envolventes; supuestos/rechazos siguen pendientes para aprobar. Impactos declarados por regla; el genérico usa 0,8. |
| E.3 Acciones | Aceptar, corregir, supuesto, PATCH con ETag y auditoría | Rechazar sin cambiar el enum 0.3; evidencia y nota opcionales; deshacer completo mediante auditoría inversa e idempotencia; protección frente a un campo que cambió después. El historial local añade solo escrituras confirmadas. |
| E.5 Tiempo | `seconds` en PATCH y suma en auditoría, sin conexión en la web | Sesiones manuales por revisión, reloj activo del cliente, agrupación por equipo/proyecto/dataset y separación de pruebas. Registro preparado; muestra humana e impacto del pitch todavía sin medir. |
| E.6 / 3.8 | JSONL, exportación de correcciones aprobadas y propuesta de recalibración CPU | Selección de pares few-shot por campo/estrategia, recortes PDF, huellas e invalidación; excluye el equipo y documentos consultados. Los consume el contexto del Copiloto. La extracción y prioridad de fuentes requieren integración/evaluación de Lectura; muestra humana pendiente. |
| C.4 Referencia | Geometría Z vertical y azimut matemático en el generador | Convenio interno documentado y comprobado, incluido intercambio IFC/Three.js. Norte de planta y contraste con IFC de TR siguen pendientes. |
| 3.7 / H.7 | Dos lotes CPU, cola horizontal y diagrama en FASE3 | Inventario de los 163 fallos, filtro por tag para reproducir, control de cobertura y material de pitch con presupuesto paramétrico. No se da por resuelta la lectura de escaneados ni se presupuestan 1.600 IFC correctos. |

## Garantías del recorrido

Cada escritura usa ETag/If-Match e Idempotency-Key. La web envía además la instantánea del
campo que mostró: actualizar el ETag desde otra pantalla no permite aceptar un valor no visto.
Deshacer restaura valor, unidad, estado, fuente, alternativas, intervalo y explicación, conserva
la auditoría anterior, registra `undo_of` e invalida cualquier aprobación.

Rechazar equivale a `state="abstained", action="reject"`, con explicación de rechazo. No se
inventan un valor ni un estado fuera del contrato. Un rechazo y un supuesto impiden aprobar.
Las coordenadas pueden ser negativas; los límites físicos de cada parámetro los valida la API.

Si la escritura SQL termina y falla solo la exportación JSONL, la respuesta 503 identifica que
el cambio está persistido y devuelve revisión, ETag e ID de auditoría. La web conserva la acción,
permite deshacer y ofrece reintentar **solo la exportación**, sin repetir la corrección.

Los tiempos antiguos sin reloj no se convierten en cero segundos medidos. Las sesiones humanas
son declaradas, no autenticadas. Se informa de pendientes y aprobación para distinguir tiempo
parcial de una revisión terminada. [Protocolo del piloto](MUESTRA_REVISION_MANUAL.md).

## Límite de aprendizaje

Los ejemplos de la API proceden exclusivamente de revisiones sintéticas aprobadas. No se
entrena un modelo al consultarlos, no se despliegan curvas ni se cambian las prioridades de
fuentes automáticamente. El contenido de un ejemplo no prueba valores del equipo actual.
La caché de respuestas del Copiloto incorpora su manifiesto; la de trabajos incorpora también
los hashes de calibración y fusión, y evita guardar si cambian durante la ejecución.

La muestra manual comienza vacía. Las simulaciones y pruebas no se presentan como correcciones
de uso humano ni como validación sobre planos reales.
