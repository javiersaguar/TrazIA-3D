# Correcciones aprobadas en extracción · 01/11

La API ya transporta feedback al proceso de extracción mediante un contexto aislado por trabajo. El perfil solo usa revisiones con huella de aprobación vigente, originales verificables, **sesión humana finalizada** y acciones de campo vinculadas a esa sesión. Se excluyen el equipo consultado y los documentos compartidos. Pruebas automáticas, sesiones abiertas, revocadas o sin vínculo quedan fuera. Los trabajos pueden desactivarlo con `use_learning: false`.

Se incorporan hasta tres ejemplos few-shot al prompt real del proveedor, como JSON de datos citado y con instrucción de no copiar cifras al equipo actual. Cambia la huella del prompt y de su caché. La evidencia actual sigue teniendo que proceder del documento consultado. No se ha llamado a ningún proveedor para comprobarlo: las pruebas de contrato usan un proveedor inyectado.

Antes de fusionar D, la prioridad aprendida de un canal puede modificar su confianza por un factor entre 0,85 y 1,15, conservando confianza bruta y explicación. Se compara la primera predicción con la decisión final; se exige un mínimo de 30 campos y seis grupos independientes. Revisiones del mismo equipo o equipos con originales compartidos no cuentan como grupos independientes. La frecuencia suavizada es una heurística limitada, **no una validación causal ni una nueva calibración certificada**.

La huella del estado aprobado y de sus sesiones entra en la clave de caché de trabajo (versión 4). Revocar, finalizar o cambiar una revisión invalida la selección de ejemplos/prioridades. En offline se verifican los originales de los ejemplos antes de reutilizar. La recalibración CPU existente continúa produciendo propuestas con sus condiciones de activación; esta sesión no entrena ni activa un modelo con datos inventados.

Pruebas: `test_plataforma_extraction_feedback.py`, caché/offline, proveedores y fusión. La autorización positiva se construye solo en una base temporal de prueba; **no es una sesión realizada por una persona ni una medición E.5**.

## Pendiente

E.5 queda pospuesta por indicación de Javier (01/11). No hay muestra nueva de correcciones humanas ni evaluación separada que demuestre mejora de precisión. Por eso 3.8/E.6 conservan su parte de validación pendiente. Un experimento de eficacia deberá separar equipos/documentos, comparar extracción con/sin perfil y verificar riesgo-cobertura; no se atribuye al feedback el cambio de resultados del lote de escala sin una ablación.


## Evaluación pendiente · 01/11

Muestra humana aportada para esta sesión: **n=0** (confirmado por Javier). No hay una mejora de
extracción/prioridad medida con correcciones humanas representativas; E.6 y 3.8 siguen parciales.
E.5 está pospuesta y no se realiza una sesión manual ni se presentan pruebas sintéticas como uso real.

Cuando haya evidencia autorizada, congelar documentos, modelos y correcciones aprobadas, separar
por equipo/documentos el conjunto de ejemplos del de evaluación y comparar `use_learning=false`
con `true` sobre las mismas entradas. Mantener proveedores/semilla/parámetros y contabilizar fuentes,
abstenciones, aciertos/errores por campo, calibración, latencia y coste. Verificar exclusión de
equipo/documento y retirada al revocar; no incorporar al contexto respuestas del equipo evaluado.
Informar tamaño de muestra, diferencias pareadas e incertidumbre antes de atribuir mejora causal.
No se publican originales reales ni correcciones sin autorización.

## Evaluación sintética adicional · 02/11

[Ablación reproducible](evidencias/fase3/02nov-aprendizaje/README.md): ajuste en 24 equipos de
S-dev y prueba en 16 equipos disjuntos de S-reservado (96 revisiones), sin documentos compartidos.
Las prioridades reducen el recall medio por equipo en 3,72 puntos, IC95 [−6,08; −1,65]; el perfil
queda rechazado. Los ejemplos cambian el prompt, con resultado CPU idéntico al no utilizar
proveedores; su eficacia visual sigue sin medir. La recalibración sintética de B+OCR reduce ECE
externa 0,1454 → 0,0753, aún sobre el objetivo 0,05, y no se activa. La ruta actual de D no propone
curva sin las filas de fusión con máscaras: [entrega a Lectura](agentes/ENTREGA_LECTURA_02NOV.md).

Se ha reforzado el consumidor para ignorar feedback no verificado, distinguirlo en la huella y
acotar los factores a [0,85; 1,15]. La simulación usa un contexto experimental aislado: cero
sesiones humanas, cero aprobaciones fabricadas y ningún cambio en el almacén de producción.
3.8/E.6 conservan su validación humana pendiente; E.5 permanece pospuesta.
