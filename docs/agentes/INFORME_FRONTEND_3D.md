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

Siguiente sección. Geometría procedural separada de PreparedProduct/IFC, con etiqueta visible.

## 2.3–2.6

Pendientes. Antes de editar families/ o ifc.py se requiere la confirmación de Javier indicada
en el encargo. No se han modificado esos archivos ni datos de data/private/.
