# Preguntas difíciles del jurado

ROADMAP 4.7 (J.5). Una respuesta de unos 20 segundos para cada pregunta, con la cifra que la
sostiene y su fuente. Fecha: 18/11/2026.

Todas las cifras son de **datos sintéticos** y se dicen como tales. Del 25/11 en adelante se
sustituyen por las medidas con el dataset del reto, sin mezclarlas con las sintéticas. Si una
cifra del evento no está medida, se dice que no lo está: nunca se estima en voz alta.

Responde quien lleva el área, según el reparto propuesto en el
[ROADMAP 5.5](ROADMAP.md#55-reparto-de-roles-propuesta--confirmar-en-la-reunión-0):

- **Lectura:** Javier.
- **3D e IFC:** Miguel.
- **Web:** Iria.
- **Evaluación y negocio:** Alejandro.

## Lectura y fiabilidad

**¿Y si la IA se inventa una cota?** *(Lectura)*
Ningún valor entra sin una cita: página y región del plano de donde sale. Si no se puede citar, el
campo queda vacío o en abstención y va a revisión. En los estudios sintéticos, las estrategias
elegibles tienen 0 % de valores sin respaldo y el 100 % citados.
Matiz que hay que decir si insisten: ese 0 % significa que el número está en la región citada, no
que sea el campo correcto. Leer un dato real en el campo equivocado no lo detecta esa métrica.
Fuente: [ESTUDIO.md](ESTUDIO.md), estudio 7, y [DEMO.md](DEMO.md).

**¿Qué pasa con planos escaneados o de mala calidad?** *(Lectura)*
Empeora, y lo medimos por separado. La estrategia D puntúa 0,951 en vectorial, 0,648 en escaneado
limpio y 0,478 en escaneado pobre. Por eso la cola de revisión empieza por lo más dudoso y no damos
nunca una media que mezcle tipos de plano.
Fuente: ESTUDIO.md, estudio 7.

**¿Por qué no usar solo un modelo de visión?** *(Lectura)*
Lo probamos. Con Qwen3-VL local como lector, A baja de 0,543 a 0,445, mete un 7,3 % de valores
que no se pueden anclar y tarda 130 veces más (172 s por revisión), en un subconjunto declarado de
seis equipos. Probamos también seis modelos externos, solo con sintéticos: ninguno superó a A sin
visión, y los mejores alucinaron entre el 8,6 % y el 11,4 %. La visión entra como un canal más
dentro de D, no como lector único.
Fuente: ESTUDIO.md y [INFORME_LECTURA.md](agentes/INFORME_LECTURA.md).

**¿Por qué D y no otra?** *(Lectura)*
Porque es la que mejor puntúa con la rúbrica del reto: 0,708, IC 95 % [0,676; 0,740], frente a
0,609 de reglas con OCR. Quitarle la geometría le resta 0,066 de forma significativa. Si lo
preguntan con detalle: en vectorial las reglas solas son muy buenas, pero el selector por tipo de
documento perdió en el conjunto reservado, así que mantenemos D para todo.
Fuente: ESTUDIO.md, estudio 7.

**¿Qué significa la confianza?** *(Lectura)*
Está calibrada. En el conjunto reservado, el error de calibración (ECE) de D es 0,027 y el intervalo
del 90 % acierta el 91,4 % de las veces. Esa garantía vale si los planos se parecen a los de
calibración; con un proveedor de planos nuevo es una comprobación, no una garantía.
No decir «± 3 mm»: no lo hemos medido.
Fuente: ESTUDIO.md, estudio 7, y DEMO.md.

**¿Un detector entrenado con planos sintéticos sirve con planos reales?** *(Lectura)*
Todavía no lo sabemos, y lo decimos. Con sintéticos, el detector propio acierta campos que otros
canales no aciertan, pero su efecto en la puntuación no se distingue de cero. Como lector único,
además, no es elegible: un 3,7 % de valores sin respaldo. Medirlo con planos reales es trabajo del evento.
Fuente: ESTUDIO.md, estudios 6 y 7.

**¿Las correcciones humanas mejoran la lectura?** *(Lectura)*
El circuito existe: una corrección aprobada se registra y recalibra. Pero en la prueba sintética el
ajuste de prioridades empeoró y lo rechazamos. Sin una muestra de correcciones reales no podemos
afirmar que mejore.
Fuente: [ROADMAP](ROADMAP.md), tarea 3.8.

## Modelo 3D e IFC

**¿Lo que veis es el IFC o un dibujo?** *(3D e IFC)*
Es el IFC. El visor lee la geometría del archivo y no dibuja una versión aparte. Incluso en
Modelo › Diseños, al cambiar una medida se reescribe el IFC4 en el navegador y el visor lo vuelve a leer.
Fuente: [AGENTS.md](../AGENTS.md) y [EDICION_ASISTIDA.md](EDICION_ASISTIDA.md), sección 10.

**¿Se integra con SP3D, Tekla o el visor que ya usamos?** *(3D e IFC)*
Exportamos IFC4, IFC4X3 e IFC2X3 con GUID estables y los cambios como incidencias BCF 2.1. Un IFC4
de ejemplo pasó el validador de esquema y reglas sin incidencias y se abrió en Bonsai, en nuestro
visor web y en BIMvision. No lo hemos probado dentro de SP3D ni de Tekla.
Fuente: [ifc-checks/01nov](ifc-checks/01nov/README.md).

**¿Por qué paramétrico y no reconstrucción libre?** *(3D e IFC)*
Es el compromiso que plantea el propio enunciado. Un modelo paramétrico por familia es robusto, se
compara entre revisiones y conserva la identidad de cada pieza. Si la N3 sube, sigue siendo la
misma N3, no una baja y un alta. La reconstrucción libre cubre más formas, pero no da esa trazabilidad.

**¿Qué pasa si alguien cambia un dato después de aprobar?** *(3D e IFC)*
La aprobación está ligada a la huella de los datos. Si cambia un valor, la aprobación desaparece
y el modelo vuelve a DRAFT. Se puede enseñar en vivo.
Fuente: DEMO.md.

## Escala, coste e impacto

**¿Escala a 400 o 500 equipos?** *(Evaluación y negocio)*
La arquitectura sí: cola, varios workers y caché por huella. Con un lote sintético de 336
revisiones, cuatro workers en CPU fueron 1,47 veces más rápidos que uno. Salieron 251 IFC DRAFT
y 85 errores. Lo de 400 equipos es una extrapolación, no una medida, y 251 DRAFT miden cobertura,
no fidelidad.
Fuente: ROADMAP, tareas 3.7 y H.7, y el pitch.

**¿Cuánto cuesta por equipo?** *(Evaluación y negocio)*
En el estudio, todo corre en local: 0 € de servicios externos y unos 2,5 s por revisión con D en
CPU. No incluye el tiempo de la persona que revisa ni el hardware.
Fuente: ESTUDIO.md, estudio 7.

**¿Cuánto tiempo ahorra?** *(Evaluación y negocio)*
Lo que podemos decir es el punto de partida del enunciado: entre 1.800 y 10.000 horas de
transcripción por proyecto. El ahorro solo lo damos si hemos cronometrado una sesión de revisión
real. Sin eso, la calculadora de Impacto es un escenario y se presenta así.
Fuente: enunciado GA2MODEL, pág. 5, y ROADMAP E.5.

**¿Qué medís contra nuestros IFC?** *(Evaluación y negocio)*
Superficie contra superficie frente al IFC de referencia, por equipo, con un mapa de calor de
dónde nos separamos. La convención de orientación se fija con los demás equipos, no con el propio
equipo medido.
Fuente: [GUION_DEMO.md](GUION_DEMO.md) y `databricks/03_evaluar_contra_tr.py`.

## Datos y confidencialidad

**¿Habéis mandado nuestros planos a una IA externa?** *(Lectura)*
No. Los datos del reto se quedan en la plataforma del evento. Nuestros notebooks solo sacan
agregados. Cualquier proveedor externo se ha usado únicamente con sintéticos y queda registrado.
Además, un guardián en cada commit impide subir documentos, salidas o claves al repositorio.
Fuente: [FLUJO_IA.md](FLUJO_IA.md) y [AUTOMATIZACION.md](AUTOMATIZACION.md).

**¿Qué parte existía antes del evento?** *(Javier)*
Está declarado en [PREVIOUS_WORK.md](../PREVIOUS_WORK.md) y marcado con el tag
`pre-hackathon-baseline` al empezar. Todo lo posterior se registra por commit.

## Visión

**¿Qué haríais con tres meses más?** *(Evaluación y negocio)*
Medir y ajustar con planos reales e históricos de Técnicas Reunidas, ampliar las familias y conectar
la salida con su entorno común de datos. En ese orden: primero medir, después ampliar.

## Preguntas al mentor (no al jurado)

Unidades, origen, Norte y azimut. También tolerancias geométricas, criterio de boquillas, familias
prioritarias, documentos de referencia y permisos de tratamiento y exportación.
