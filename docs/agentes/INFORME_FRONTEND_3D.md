# Informe frontend 3D · 30/10/2026

Implementadas las secciones 2.1–2.6 en el worktree TrazIA-3D-web-3d, rama feat/web-3d.
Integrada feat/web-marca (06a3628) mediante merge local 8796616. No se modifica el checkout del
Agente 1, no se cambia main, no hay push ni PR. Autor de los commits: Javier Saguar.

## Entrega por sección

- **2.1:** acero físico con cepillado cacheado, pintura, caras mecanizadas y pernos. Estudio con
  PMREM/RoomEnvironment, Lightformers, AgX, contacto, SSAO, SMAA, Bloom selectivo y viñeta.
  Render a demanda, DPR adaptativo y pausa fuera de pantalla. Colores exclusivamente desde BRAND.
- **2.2:** cinco familias paramétricas ilustrativas, taladros/aberturas CSG, pernos instanciados,
  nube de 18.000 partículas, morph interrumpible, HUD y miniaturas estáticas con contexto liberado.
  Etiqueta persistente «Ilustrativo · no procede del IFC». Los ejemplos no sustituyen mallas IFC.
- **2.3:** shader fresnel/rejilla/scanlines, barrido físico, flujo de partículas y tres recortes
  circulares de la misma geometría. Disposiciones side/inplace, autoplay, scrub, progress numérico
  y progressValue opcional para scroll sin React por frame. /modelo muestra rev B y la galería.
- **2.4:** cambios segmentados por elemento, cámara, pulso/outline, fantasma A, cota interpolada,
  barrido/partículas, velocidades, scrub con marcas, hover y selección sincronizados, filtro de
  modificados, A | B con cámaras vinculadas y presentación con Fullscreen API/Escape.
- **2.5:** paneles redimensionables con persistencia y foco; PDF multipágina y miniaturas;
  inspector de Psets/GUID/fuente/confianza/procedencia; conexión campo → plano → elemento.
  Aprobación API con If-Match, clave idempotente, progreso y recuperación de conflictos 412.
- **2.6:** IFC con bridas realmente taladradas, pernos, boca de hombre con tapa/pescante, orejetas
  perforadas, faldón con aberturas booleanas, anillo base y anclajes. Los productos originales
  conservan su GUID; cada pieza nueva tiene GUID estable y Pset_TrazIA.Origen=derivado_de_norma.
  El worker reconoce detalles y sus padres; seleccionar una brida lleva al campo de su boquilla.

## Alcance del detalle y de la tabla

El generador lo habilita con build_ifc(..., details=True). La API lo solicita para sus datos
sintéticos y los IFC públicos se regeneran con esa opción: rev A tiene 73 productos; rev B, 83.
El comportamiento habitual del núcleo, el bench y Streamlit conserva su LOD. Los documentos reales
no reciben implícitamente piezas supuestas. No se añade ningún campo extraído ni confianza falsa.

Los patrones publicados cubren DN 50/80/100/150/200/500 y clases 150/300. Se usa coincidencia
exacta; no se extrapolan tamaños ni clases. Si existe una brida trazada, se conservan su diámetro,
espesor y GUID y se deriva el taladrado cuando cabe. Sin rating, la clase 150 es un supuesto visual
expreso en el Pset. Cabezas de pernos, boca, pescante, orejetas y soporte usan proporciones de
ilustración; no constituyen cálculo mecánico ni de izado/cimentación. Origen, alcance, valores de
tabla, referencia y necesidad de verificación viajan en los Psets y aparecen en el inspector.

Fuentes primarias: alcance de [ASME B16.5](https://www.asme.org/codes-standards/find-codes-standards/b16-5-pipe-flanges-flanged-fittings-nps-1-2-nps-24-metric-inch-standard/2017/pdf)
y tabla dimensional [HISAKA, ASME B16.5-1996](https://www.hisaka.co.jp/valve/english/techdoc-en/techdoc04-en/).
La edición de la tabla se registra; no se presenta como certificación de cumplimiento de 2025 ni
como selección de presión/temperatura/material. Datos dimensionales contrastados con la tabla de
[CRP](https://www.crp-us.com/products/flange-table-and-dimensions/).

## Integración de la portada

El hero ya permite cambiar de familia con clic; el alzado ilustrativo deja pasar gestos al visor.
El holograma inferior se carga al aproximarse a la sección y recibe MotionValue directo. React
solo cambia al cruzar una fase; shader, barras y porcentaje siguen refs/valores de movimiento.
El seguimiento conserva el foco durante cambios de tamaño del panel, orienta la cámara hacia
las boquillas y usa un único anillo de barrido por elemento. El estado reducido es estático y su preferencia se hidrata sin diferencias con el servidor.
La narración distingue el modelo paramétrico de la lectura real de evidencia.

## Verificación

- Python: ruff check y format --check pasan; pytest completo: **231 correctas, 1 omitida**,
  185,68 s. Siete pruebas nuevas de detalle cubren tres esquemas, mallas, agujeros, procedencia,
  GUID, clases desconocidas, datos reales y conservación de las dimensiones explícitas.
- IFC4/IFC4X3/IFC2X3: validación EXPRESS y lectura/tesselación correctas. Se conservan identidades
  entre revisiones, exportación básica y detallada. Las aberturas y taladros son geometría IFC.
- Frontend: typecheck, lint, **32 unitarias** y build pasan. Lint conserva un aviso previo de
  TanStack Table; las dependencias emiten avisos de BVH/Three sin fallos.
- E2E de humo: **22 correctas y 6 omitidas en offline**;
  **27 correctas y 1 omitida con API**. Incluyen el cambio de familia del hero,
  brida/GUID/evidencia, dos páginas PDF y aprobación real tras un conflicto 412.
- Rendimiento de la escena IFC enriquecida con tres recortes, en Chrome/RTX 5070 Laptop:
  **239,2 fps**, p95 **4,7 ms**, 1.197 frames, 944 draw calls, 296.162 triángulos,
  DPR adaptativo 0,592. Muestreo de giro de 5 s; describe esta máquina y esta resolución.
- Lighthouse y comprobación de scripts iniciales se guardan en generated/frontend/ y se resumen
  en verificacion_frontend.json. Three y web-ifc permanecen fuera de los scripts iniciales de /.
- **24 capturas** correctas (12 pantallas, claro y oscuro); revisión de las cuatro rutas
  principales a 390/1024/1600 px sin desbordamiento ni errores de página. En móvil el aviso de
  interpolación se ajusta para dejar libres los controles de cámara.
- Lighthouse escritorio: **100/100**, FCP 247 ms, LCP 778 ms, TBT 0 y CLS 0. Los 19 scripts
  iniciales suman 967.133 bytes sin comprimir; no contienen el renderer Three ni web-ifc.
  Se verifica también la existencia del chunk Three diferido como control positivo.

## Entorno y límites

La API original 8010 permanece en marcha. Se usa otra instancia en 8011 para pruebas y demo,
con datos sintéticos aislados; CORS permite los puertos 3300/3310/3311 del plan. No se ha leído
ni modificado data/private/. No se añaden dependencias de aplicación ni se modifican brand.ts,
package.json o el lockfile. Se mantienen las firmas públicas; solo se añaden props opcionales.

Skills aplicadas: frontend-design, ui-ux-pro-max, react-best-practices, emil-design-eng y animate;
guías de Next 16 consultadas en la versión instalada. Sin firmas de herramientas ni coautores.


## Sesión 31/10 · giro de cámara y presupuesto geométrico

### Hecho

- Giro automático de cámara alrededor del centro físico del modelo, sobre el eje
  vertical, a una vuelta por minuto. Se comparte en los visores que usan CameraRig:
  escaparate, holograma/Modelo, Revisión, Cambios y planta. Las miniaturas PNG siguen
  siendo imágenes. La figura y sus coordenadas IFC no se transforman para simular el giro.
- Botón 360° para pausar/reanudar. Arrastrar, enfocar o ampliar suspende temporalmente
  el giro; una vista fija elegida por la persona lo pausa. En A | B el estado se
  comparte y arrastrar cualquiera de las cámaras pausa ambas. Durante la coreografía
  de Cambios manda su cámara, y después vuelve la órbita.
- Con movimiento reducido no hay giro automático. Fuera de pantalla o con la pestaña
  oculta el Canvas sigue sin dibujar. useFrame/refs, sin estado React por fotograma.
- El espacio reservado a recortes/rótulos no desplaza el eje de órbita. Pausar no
  dispara el clic que cambia la familia del escaparate.
- Teselación circular del worker IFC de 48 a 24 segmentos y menor densidad en perfiles
  ilustrativos. Se mantienen geometría leída del IFC, huecos, GUID, Psets y selección.
  No cambian los archivos IFC públicos ni se añade una malla aproximada alternativa.
  La prueba de las cinco familias cuenta también los pernos instanciados.

### Verificación medida

Escena IFC sintética enriquecida con los tres recortes: **157.538 triángulos**,
**235.3 fps**, p95 **4.9 ms**, 944 draw calls, DPR **1**,
Chrome y RTX 5070 Laptop. Reduce el conteo anterior de 296.162 por debajo de 200.000.
No se interpreta como comparación controlada de FPS con la sesión anterior: cambian
DPR y carga compartida; Lectura ejecutaba estudios. No acredita un portátil sin GPU dedicada.

Órbita completa comprobada en navegador: **385.7° en 64.185 s**;
variación máxima del radio **7.1e-15** unidades de escena. El giro no altera
la geometría ni desplaza el modelo respecto a su propio eje.

Typecheck, lint (aviso previo de TanStack), 32 unitarias y builds offline/API correctos.
Humo final: 25 correctas + 6 omitidas offline; 30 correctas + 1 omitida con API real.
Incluye giro, pausa sin cambiar familia, movimiento reducido, pausa A | B sincronizada,
interacción/identidad IFC, aprobación ETag y límite de 200.000 triángulos.

Reproducción con la web ya levantada:

```powershell
node web/scripts/measure-viewer.mjs --orbita-completa
```

Se conserva la vista previa conectada en http://localhost:3120/modelo y API propia 8022.
No se para 8010/3100 ni el servicio de Lectura en 8020. Capturas oscuras en
`docs/capturas/31oct-{revision,cambios,modelo,holograma-ifc}.png`.
Medidas exactas en `docs/evidencias/frontend/31oct/`. El techo de triángulos está
comprobado en la escena de referencia; queda medir el objetivo en otro portátil normal.


## Sesión 01/11 · mejoras I.5

- Cámara con presets interrumpibles y retorno correcto tras recuperar una vista personal; hasta ocho vistas por URL de IFC, persistidas y validadas antes de aplicar. Se conservan órbita, enfoque y outline/hit slop existentes. El picking ignora los puntos recortados.
- Corte animado con refs/uniforms y estado final estático con movimiento reducido. La tapa se reconstruye al asentarse; triangulación distingue lazos separados y agujeros reales (prueba con dos sólidos). No se sustituye el IFC por geometría aproximada.
- Cotas enfocables con unidad, confianza, estado y fuente de la anotación o del Pset IFC. El inspector lee confidence dentro de source. Se mantiene la advertencia DN nominal. Material de supuesto según campo/componente: un supuesto de faldón no pinta toda la virola.
- PNG compuesto desde el canvas real y los rótulos visibles; procedencia, DRAFT, UTC y triángulos dentro del viewport. BCF conectado empaqueta esa imagen, cámara ortográfica convertida web→IFC y GUID. Errores recuperables; deshabilitado sin API.
- Typecheck, lint (aviso TanStack previo), 42 pruebas unitarias y build en verde. E2E final: API 33 pasadas/una omitida (2,8 min), sin API 26 pasadas/ocho omitidas por depender de API (2,3 min). El guardado espera a que el preset sea observable; movimiento reducido aplica cámara inmediatamente. Capturas sintéticas: [visor](../capturas/visor-mejoras-01nov.png) y [PNG exportado](../capturas/visor-exportado-01nov.png), ambas inspeccionadas visualmente.
- Navegador con SwiftShader en CPU: no es una nueva medición de FPS en la RTX. El presupuesto de 200.000 triángulos sigue comprobado por la prueba del holograma IFC. Falta otro portátil y calibrar cámara para superponer un GA arbitrario; las vistas personales no hacen esa calibración automáticamente.
