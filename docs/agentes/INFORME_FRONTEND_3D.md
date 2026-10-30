# Agente 2 · 3D · plan frontend

Worktree `TrazIA-3D-web-3d`, rama `feat/web-3d`, base compartida `976d8dd`.
Se comprobó AGENTS.md, web/AGENTS.md, plan, contratos, necesidades y guías locales de Next 16.
Referencias visuales 05 y 06 inspeccionadas. Skills usadas: frontend-design, ui-ux-pro-max,
react-best-practices, emil-design-eng y animate. Sin push ni PR.

## 2.1 · Kit de realismo

Material físico de acero (metalness 0,85; roughness 0,34; clearcoat 0,2), pintura, caras mecanizadas
y pernos. Texturas procedurales de normales/rugosidad, deterministas, cacheadas y liberadas al
salir la última instancia, compatibles con Strict Mode. Spring conserva la opacidad y el color.
Los pigmentos 3D usan exclusivamente BRAND; no se modifica brand.ts ni archivos del Agente 1.
Se añaden UV de superficie al IFC sin cambiar posiciones, normales o índices.

Estudio con RoomEnvironment capturado por el PMREM de Environment, anillo y tres rectángulos
Lightformer, AgX, sombras de contacto, SSAO, SMAA, Bloom selectivo y viñeta. Render a demanda,
DPR adaptativo y pausa al salir de pantalla/ocultar la pestaña. La selección resalta el contorno
sin convertir el acero entero en una superficie celeste emisiva.

Comprobado: typecheck, lint (solo aviso previo TanStack), 18 pruebas unitarias y build.
Chrome/WebGL: laboratorio con los tres canvas y sin errores; captura oscura
`docs/capturas/agente2-21-laboratorio.png`. Medición de giro de 5 s: 240 fps, p95 4,3 ms,
1.201 frames, 73 draw calls, 11.786 triángulos, DPR 0,65, ANGLE/D3D11 sobre RTX 5070 Laptop.
Son cifras de este navegador y la calidad adaptativa indicada; se repetirá con las nuevas escenas.

Pendiente externo: la API 8010 rechaza CORS desde 3300. Registrado en NECESIDADES.md y consultado
a Javier; la API existente se mantiene en ejecución. No se presenta la captura con error CORS
como verificación de Revisión conectada.

## 2.2 · Modelos ilustrativos

Cinco generadores: vertical con fondos 2:1, soldaduras, cuatro conexiones, boca de hombre ciega
con pescante, orejetas taladradas por CSG, faldón hueco con cuatro aberturas CSG, anillo y anclajes;
horizontal con silletas; columna con platos, plataformas y escalera; intercambiador abierto con
haz de tubos y canal; tanque de techo cónico. Cuatro lotes de superficie por modelo y pernos en
InstancedMesh. Esta geometría no se introduce en el visor de IFC.

ShowcaseVessel implementa selección de familias y controles de cámara; modo particles con 18.000
puntos muestreados sobre la superficie, nube inicial y morph interrumpible mediante uniforms/refs.
Respeta movimiento reducido y pausa fuera de pantalla; no usa setState por frame. La familia se
controla externamente con kind/onKindChange o internamente. HUD con orientación real de cámara.
Etiqueta persistente «Ilustrativo · no procede del IFC». El modo hologram usa alambre por ahora;
el shader completo corresponde a 2.3.

EquipmentThumb renderiza una imagen 3D estática por familia, solo cuando entra en pantalla;
serializa el trabajo y libera su contexto WebGL. Cinco miniaturas no mantienen cinco canvas activos.
Recursos compartidos con referencia y limpieza. No se necesitan providers de la app.

Comprobado: typecheck, lint, 25 unitarias y build; seis pruebas de geometría finita/bounds y un
muestreo reproducible. Laboratorio independiente /lab/showcase: sin errores de navegador, cinco
miniaturas reales, selección de intercambiador y transición de partículas. Capturas oscuras
agente2-22-vertical/intercambiador/particulas.png. Giro: 239 fps, p95 4,3 ms, 1.196 frames,
32 draw calls, 64.324 triángulos y DPR 1, RTX 5070 Laptop/ANGLE/D3D11. Pendiente repetir el
presupuesto en la página final con holograma y callouts.

Aviso de dependencia: three-bvh-csg 0.0.18 usa maxLeafSize, deprecado por three-mesh-bvh 0.9;
no falla la geometría y no se modifica la dependencia del Agente 1. @types/three omite el método
setRandomGenerator que sí tiene MeshSurfaceSampler 0.186; la anotación local cubre esa API real.

## 2.3 · Holograma → acero

Shader fresnel celeste con rejilla y scanlines, flujo de partículas y barrido de material físico
con borde emisivo. Disposiciones side/inplace, progress externo o autoplay con scrub. Los
recortes circulares usan RenderTexture con otra cámara y las mismas mallas, sin sustituciones.
Modo hologram de ShowcaseVessel actualizado al shader. Página /modelo con IFC B y selector
separado de las cinco familias ilustrativas. Los controles esperan a que la fuente esté lista.

source=ifc conserva la geometría y el posicionamiento de PreparedProduct. El IFC actual carece
de orejetas/bridas detalladas: se muestran conexión y faldón existentes, sin inventar el tercer
recorte. El modelo ilustrativo sí tiene los tres detalles, marcados como tales.

Comprobado: typecheck, lint, 25 unitarias y build. Chrome sin errores de página en las dos
fuentes, scrub al 50 % y movimiento reducido al 100 % con controles desactivados. Capturas
agente2-23-procedural/ifc/barrido.png. Integración con portada pendiente del Agente 1;
ambos componentes funcionan en laboratorios independientes sin providers propios de la app.

## 2.4–2.6

Pendientes. Antes de editar families/ o ifc.py se requiere la confirmación de Javier indicada
en el encargo. No se han modificado esos archivos ni datos de data/private/.
