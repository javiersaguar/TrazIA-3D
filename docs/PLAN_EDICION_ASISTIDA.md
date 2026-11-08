# Edición asistida del modelo · plan de desarrollo

Fecha: 08/11/2026. Estado: **planificado; funcionalidad nueva sin implementar**.
Workstream K del [ROADMAP](ROADMAP.md#k-edición-asistida-del-modelo-planificada).

## Resultado de producto

Desde Modelo, una persona selecciona un equipo o boquilla y pide un cambio por formulario
o chat. El sistema prepara una propuesta, comprueba su coherencia y muestra el antes/después
con geometría IFC. Solo al confirmar se crea una revisión DRAFT nueva, con autor, motivo,
procedencia y comparación. El plano original se conserva; las anotaciones se exportan como
documento derivado. La aprobación técnica sigue siendo una acción humana posterior.

Ejemplo sintético: cambiar la longitud entre tangentes y la elevación de N3 en una operación.
Si se pide «aumentar la altura» sin distinguir altura total y longitud de virola, se solicita
esa aclaración. Si cambiar la dimensión deja una boquilla fuera del recipiente, se informa
del conflicto y no se desplaza la boquilla silenciosamente.

## Base existente y trabajo nuevo

| Base comprobada en el repositorio | Lo que hay que añadir |
| --- | --- |
| Campos con unidades, estado y fuente; validadores por familia | Operaciones de diseño permitidas y su procedencia diferenciada |
| PATCH de campo, ETag, idempotencia, auditoría y deshacer | Propuesta de varios cambios, validación conjunta y confirmación atómica |
| Generación/validación IFC, geometría por GUID y comparación | IFC temporal de propuesta y publicación de una revisión nueva |
| Copiloto con herramientas de lectura y citas | Intérprete de intención que entrega propuestas estructuradas |
| Selección 3D, revisión PDF y marcas vinculadas a evidencias | Formulario contextual e informe PDF derivado de cambios de diseño |
| Exportación de correcciones y aprendizaje aprobado | Excluir decisiones de diseño del aprendizaje de extracción |

No se considera que un PATCH existente resuelva por sí solo este flujo: editar campos uno
a uno puede dejar estados intermedios inválidos y no equivale a confirmar un lote completo.

## Alcance y prioridades

**P0 · MVP de formulario:** K.0–K.4 y sus pruebas. Un equipo por propuesta; editar parámetros
existentes soportados por su familia, atributos admitidos y posición/elevación/azimut de una
boquilla existente. Entrada en unidades explícitas y normalización con la capa existente.
Primera demostración sobre un recipiente vertical sintético; la UI solo ofrece operaciones
con cobertura verificada para la familia elegida.

**P1 · Asistente y plano derivado:** K.5–K.7. El chat usa las mismas operaciones que el
formulario. Las anotaciones del PDF se limitan a elementos con localización comprobable.

**P2 · Ampliación posterior:** K.8. Altas/bajas de boquillas, otras operaciones estructurales,
varios equipos y planos nuevos generados desde el modelo. Cada ampliación necesita validación
propia; no entra automáticamente en el MVP.

Quedan fuera del MVP la edición libre de mallas, generar piezas arbitrarias mediante texto,
sobrescribir el PDF original y emitir un plano de fabricación certificado. La coherencia de
parámetros/IFC no acredita cálculo resistente, proceso ni cumplimiento normativo completo.

## Reglas que debe conservar la implementación

1. Formulario y chat producen el mismo contrato de propuesta. Solo funciones deterministas
   admitidas modifican los parámetros; el modelo de lenguaje no ejecuta código ni escribe IFC.
2. Generar una propuesta no confirma cambios. La confirmación humana se hace sobre la lista
   exacta y la previsualización vigentes, vinculadas a la huella de la revisión base.
3. La revisión anterior y sus originales se conservan. La revisión derivada nace DRAFT y no
   hereda aprobación. Se mantiene la identidad estable de los elementos que siguen existiendo.
4. La previsualización usa el IFC generado con esos parámetros. No se dibuja una aproximación
   procedural que luego difiera del archivo publicado.
5. Una orden de diseño es distinta de corregir una lectura. Nunca se atribuye al plano original
   una dimensión pedida por chat ni se reutiliza su confianza/intervalo para el nuevo valor.
6. Las órdenes de diseño quedan excluidas de recalibración, few-shot de extracción y prioridad
   de fuentes. Solo correcciones verificadas contra originales pueden seguir ese circuito.
7. Los fallos de validación o geometría no publican revisiones parciales. Reintentar una misma
   confirmación no crea revisiones duplicadas. Una base modificada exige volver a previsualizar.
8. Datos sintéticos etiquetados. Procesamiento local por defecto; no hacen falta datos de TR
   ni sesiones humanas inventadas para implementar y probar este flujo.

## Secuencia de trabajo y criterios de cierre

### K.0 · Operaciones y procedencia — Plataforma, con revisión de Lectura

- [ ] Definir matriz familia × operación × restricciones, empezando por el recipiente vertical.
  Distinguir altura total/entre tangentes, elevación respecto al datum y azimut respecto al Norte.
- [ ] Definir `correccion_extraccion` frente a `cambio_diseno` y cómo se conservan solicitud,
  actor, motivo, fuente anterior y nueva procedencia. No asumir que una orden tiene bbox en GA.
- [ ] Resolver la compatibilidad de procedencia antes de implementar: `Source` 0.3 exige documento
  y página o celda, y una confianza numérica. Especificar los cambios aditivos/versionados que
  necesite una orden de diseño, su documento propio y los consumidores afectados; nunca crear
  una página ficticia ni inventar confianza IA para hacer pasar el validador.
- [ ] Planificar el filtro explícito de diseño en correcciones, ejemplos y recalibración, además
  de su visualización en auditoría y exportaciones. Documentar la ampliación de DEC-26/27.

**Hecho cuando:** matriz y contrato de procedencia definidos en documentación técnica, con
ejemplos de corrección y diseño claramente diferenciados y migración compatible definida.
Este punto bloquea aplicar cambios; las maquetas pueden avanzar con fixtures.

### K.1 · Propuestas y validación conjunta — Plataforma

- [ ] Definir `ChangeProposal`: ID, proyecto/equipo, revisión base, ETag/fingerprint, operaciones
  tipadas, unidades originales/normalizadas, valores antes/después, motivo, actor y origen.
- [ ] Añadir estados: borrador, requiere aclaración, inválida, lista para previsualizar,
  previsualizada, aplicada, descartada y obsoleta; separar errores de avisos.
- [ ] Implementar lista cerrada de operaciones, rutas y tipos. Validar pertenencia al equipo,
  unidades, rangos y relaciones entre parámetros sobre el lote completo.
- [ ] Identificar cambios dependientes y piezas derivadas que deban regenerarse. Mostrar
  cualquier ajuste adicional; no corregir silenciosamente otros campos.

**Hecho cuando:** un lote coherente pasa aunque un cambio aislado produzca un estado intermedio
inválido; un lote incoherente se rechaza con motivo y campo, sin alterar la revisión persistida.

### K.2 · Previsualización IFC y delta — Plataforma + 3D

- [ ] Construir el candidato y su IFC en almacenamiento temporal aislado, con caducidad y limpieza.
- [ ] Ejecutar validadores de datos, familia e IFC; registrar boquillas sin colocar y conflictos.
  Bloquear confirmar si se introducen problemas o quedan problemas sin resolución explícita.
- [ ] Comparar base/candidato con la capa existente: valores, unidades, geometría y GUID.
- [ ] Mostrar antes/después en el visor, resaltar elementos afectados y asociar cada cambio
  a su fila. Relacionar artefacto, propuesta, huella de parámetros y versión del generador.
- [ ] Usar trabajos/SSE para operaciones costosas y cancelación, sin publicar el resultado temporal
  como revisión. Informar progreso solo cuando exista un denominador real.

**Hecho cuando:** cancelar no cambia el proyecto; la geometría vista corresponde al IFC temporal
validado y cada cambio visible se puede relacionar con una operación de la propuesta.

### K.3 · Confirmación, revisión nueva y deshacer — Plataforma

- [ ] Confirmar con ID/hash de propuesta, base vigente, `If-Match` e `Idempotency-Key`.
  Rechazar propuestas caducadas, alteradas, no previsualizadas o basadas en datos obsoletos.
- [ ] Publicar una revisión nueva DRAFT, los artefactos exactos validados, procedencia y auditoría
  como una unidad coherente. Preparar blobs por hash antes de la transacción SQL y limpiar huérfanos;
  no suponer una transacción única entre sistema de archivos y base de datos.
- [ ] Registrar identidad del revisor y confirmación del lote; ninguna salida del LLM puede
  sustituirla ni aprobar automáticamente la revisión.
- [ ] Deshacer el lote mediante una revisión compensatoria trazable. No borrar historia ni
  restaurar una aprobación antigua como si siguiera vigente.

**Hecho cuando:** doble clic/reintento produce una sola revisión; una edición concurrente devuelve
conflicto recuperable; un fallo entre escritura de artefactos y commit no deja una revisión rota.

### K.4 · Formulario contextual en Modelo — Frontend + 3D

- [ ] Abrir «Proponer cambios» desde el equipo o boquilla seleccionados; mostrar dimensiones,
  unidades, datum y valores actuales. Ocultar operaciones no soportadas para esa familia.
- [ ] Permitir varios cambios, validación por campo y resumen antes/después con efecto sobre
  otras piezas. Mantener separado «Corregir lectura» de «Cambiar diseño».
- [ ] Conectar crear → validar → previsualizar → confirmar, indicando revisión base, estado DRAFT
  y artefactos resultantes. Cambiar una entrada invalida la previsualización anterior.
- [ ] Ofrecer descartar, recuperar errores y deshacer. Conservar selección/cámara cuando el
  elemento siga existiendo. El formulario funciona sin un modelo de lenguaje disponible.

**Hecho cuando:** una persona realiza un cambio sintético completo desde la UI y ve la revisión
nueva persistir al recargar, su delta correcto y el regreso mediante deshacer. Aquí cierra el MVP.

### K.5 · Chat que prepara cambios — Copiloto + Frontend

- [ ] Añadir un modo explícito «Proponer cambios» manteniendo las preguntas actuales de lectura.
  Documentar la evolución de DEC-26; el servicio actual no recibe permisos de escritura.
- [ ] Resolver el objeto por selección/ID estable. Convertir texto en operaciones de K.1,
  usando el contexto permitido y validación de esquema. Rechazar rutas/acciones ajenas al catálogo.
- [ ] Pedir aclaración ante objeto, unidad, magnitud o referencia ambiguos. Distinguir petición
  del usuario, texto de documentos e instrucciones internas; no ejecutar instrucciones del PDF.
- [ ] Mostrar una tarjeta editable de propuesta. Reutilizar formulario, previsualización y botón
  de confirmación; la respuesta «hecho» del chatbot no aplica nada por sí misma.
- [ ] Probar con proveedor inyectado y medir después el modelo local disponible: acciones
  correctas, aclaraciones, rechazos, latencia y coste. Modelo ausente/fallo → formulario accesible.

**Hecho cuando:** una petición precisa produce el mismo lote que el formulario; una ambigua no
modifica nada; un intento de ejecutar acciones no permitidas falla. No hay escrituras desde el LLM.

### K.6 · Plano derivado de revisión — Plataforma + Frontend

- [ ] Generar un PDF anotado separado, vinculado a revisión base/destino y a la propuesta aplicada.
  Etiquetarlo como propuesta o revisión de diseño derivada, con autor, fecha y tabla de cambios.
- [ ] Dibujar Δ, llamadas y valores nuevos solo donde exista una región del plano verificable.
  Si falta localización, incluirlo en la tabla como pendiente de delineación, sin inventar bbox.
- [ ] Marcar cotas/posiciones afectadas y advertir cuándo el dibujo original ya no representa
  a escala la geometría nueva. Una anotación no equivale a redibujar el recipiente.
- [ ] Conservar PDF original y SHA intactos. Vincular IFC, informe y PDF derivados por revisión;
  impedir que se usen como referencia de extracción original sin una política explícita.

**Hecho cuando:** se exporta un PDF legible con cambios trazables al modelo y sin alterar el
original; los cambios sin ubicación quedan declarados, no simulados visualmente.

### K.7 · Cierre y evidencia — Todo el equipo

- [ ] Ejecutar el recorrido completo con sintéticos: cambio válido, varias operaciones relacionadas,
  unidades equivalentes, boquilla fuera de límites, referencia ambigua, base obsoleta, reintento,
  caída de generación, cancelación, descarte y deshacer.
- [ ] Verificar GUID de elementos persistentes, geometría IFC reabierta, artefactos por hash,
  invalidación de aprobación y exclusión de órdenes de diseño del aprendizaje.
- [ ] Comprobar que documento adversarial no dispara acciones y que el proveedor no puede
  confirmar/publicar sin la operación explícita de la persona.
- [ ] Registrar tiempos medidos de propuesta, previsualización y confirmación; tamaño de casos,
  equipo/entorno y límites. No presentar la reducción de tiempo humano sin sesión real; E.5 sigue pospuesta.
- [ ] Documentar API y uso, guardar capturas claro/oscuro y añadir el nuevo trabajo a la declaración
  previa al evento. Pasar comprobaciones del código afectado antes de publicar cada subtarea.

**Hecho cuando:** hay demo reproducible de formulario y chat con recuperación de errores y
evidencias, y el roadmap separa lo implementado de lo validado con datos/personas reales.

### K.8 · Ampliación opcional — después del MVP

- [ ] Añadir/eliminar boquillas con identidad estable, reglas de colocación y delta correcto.
- [ ] Extender la matriz a cada familia soportada, con fixtures de sus parámetros específicos.
- [ ] Evaluar generar vistas 2D desde la geometría IFC y acotarlas para producir un GA nuevo.
  Validar proyección, cotas, escalas, cajetín y legibilidad antes de llamarlo plano técnico.
- [ ] Evaluar operaciones en varios equipos, permisos por rol y aprobación según disciplina.

## Interfaces propuestas, no existentes

Los nombres se concretan en K.1; esta tabla no describe endpoints ya disponibles.

| Operación | Propuesta de interfaz | Garantía |
| --- | --- | --- |
| Preparar lote desde formulario | `POST /revisions/{id}/change-proposals` | No modifica la revisión base |
| Consultar propuesta | `GET /change-proposals/{id}` | Estados, operaciones, incidencias y huellas |
| Generar previsualización | `POST /change-proposals/{id}/preview` | IFC/delta temporales ligados a la propuesta |
| Confirmar | `POST /change-proposals/{id}/apply` | Revisión nueva; concurrencia e idempotencia |
| Deshacer aplicación | `POST /change-proposals/{id}/revert` | Revisión compensatoria; historial conservado |
| Interpretar intención | `POST /copiloto/design-proposals` | Solo prepara una propuesta, nunca la confirma |
| Obtener plano derivado | `GET /revisions/{id}/design-report.pdf` | Documento identificado como derivado |

## Dependencias y reparto de ejecución

Orden: **K.0 → K.1 → K.2 → K.3 → K.4 (MVP) → K.5/K.6 → K.7**. K.8 es opcional.
Las pruebas de cada sección forman parte de su cierre; K.7 añade la validación del recorrido completo.
Tras congelar K.1, se pueden repartir motor/API y UI sin editar los mismos archivos.

| Responsable | Zona propuesta | Coordinación necesaria |
| --- | --- | --- |
| Plataforma | Módulo nuevo de propuestas, API, persistencia, IFC y documentos derivados | Dueño del contrato, transacciones y publicación |
| Frontend/3D | Función nueva de edición asistida e integración en Modelo/Copiloto | Consume contrato; el visor sigue leyendo IFC |
| Lectura | Filtros de aprendizaje y revisión de procedencia | No modifica el motor de cambios ni el visor |

Esto es un reparto para una futura ejecución, no el lanzamiento de agentes. Asignar archivos concretos
antes de sesiones paralelas; usar worktrees, commits por subtarea y publicación según AGENTS.md.

Se puede avanzar con sintéticos antes de recibir el dataset de TR. No se propone una fecha cerrada
sin ejecutar el primer recorrido de previsualización y medir su complejidad. Prioridad previa al
evento: cerrar K.0–K.4; ampliar a chat y PDF si el MVP está estable. El redibujado completo de planos
no debe bloquear la entrega principal de extracción, revisión e IFC.
