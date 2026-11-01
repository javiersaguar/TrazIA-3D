# D.4 · Interoperabilidad sintética · 01/11

**Apertura visual completada: tres de tres visores sobre el IFC4 sintético indicado.**
D.4 permanece parcial para el resto de la validación y la referencia externa.

Archivo compartido: [V-101 B DRAFT](V-101_B_DRAFT.ifc), IFC4, 238.848 bytes.
SHA-256: `9ca68e1230d7c4ca62668786ed95308d8c20c229151b2d2945930422c451472c`.
Generado desde `examples/vessel_rev_b.json` mediante `build_ifc(revision, draft=True)`;
no se usa referencia TR ni originales privados. Esta muestra no cubre todas las familias,
esquemas IFC o equipos de la entrega.

| Comprobación | Resultado y evidencia |
| --- | --- |
| IfcOpenShell, esquema + reglas EXPRESS | 0 incidencias; [manifiesto](ifc-manifest.json) |
| Bonsai Viewer, paquete portable 0.9.0post1 | Abierto; selección del IfcTank, GUID y Pset_TrazIA_Provenance visibles: [captura](bonsai-viewer.png) |
| Visor web propio con web-ifc | Mismos bytes servidos al lector IFC, 8 productos renderizables/3.696 triángulos; [captura](web-ifc.png) y [metadatos](web-ifc.json) |
| BIMvision 3.2.1 [31/12/2024] | Javier abrió manualmente el archivo; su captura muestra el recipiente, la ruta completa y las propiedades de IfcProject: [tercera captura](bimvision.png). |

El IFC contiene 15 IfcProduct, incluyendo contenedores/elementos sin representación: ese número
no equivale a los 8 productos que malla el visor web. Bonsai muestra el mismo recipiente y sus
boquillas; se inspeccionó IfcTank, GlobalId, EquipmentId, Dataset=synthetic, Draft=True y revisión B.
La captura de BIMvision fue aportada por Javier; muestra FileName=V-101_B_DRAFT.ifc,
IfcEntity=IfcProject y Name=DEMO-PLANT. No muestra las propiedades del recipiente ni cotas.
La huella del archivo de esa ruta se verificó de nuevo y coincide con el manifiesto; la imagen
por sí sola no acredita su SHA. Las capturas se conservan sin editar. No se ha enviado el modelo a un servicio externo ni se ha
registrado cuenta o correo.

## Referencia espacial y fidelidad

En esta muestra: longitud en METRE, origen (0,0,0), eje +Z vertical. `TrueNorth` no está declarado;
no se le atribuye un Norte de planta de TR. Es una comprobación interna del archivo, no una
comparación con el convenio de TR. C.4 y D.5 siguen pendientes porque no se ha aportado su IFC.
La apertura correcta y el validador de esquema no prueban fidelidad geométrica ni aprobación humana.

## Reproducir la captura web

Desde `web/`, con la API aislada del test y los puertos libres:

```powershell
$env:NEXT_PUBLIC_API_URL='http://127.0.0.1:8032'
$env:TRAZIA_CORS_ORIGINS='http://localhost:3132,http://127.0.0.1:3132'
$env:PW_PORT='3132'
$env:PW_CPU_ONLY='1'
$env:PW_USE_BUILD='1'
$env:PW_IFC_INTEROP=(Resolve-Path ../docs/ifc-checks/01nov/V-101_B_DRAFT.ifc).Path
corepack pnpm@10.18.0 exec playwright test --project=humo --grep '@interop'
```

Requiere build conectado a la misma API. El caso se registra solo con `PW_IFC_INTEROP`; verifica
la entrega de B, espera su carga y toma la captura real del navegador. Sirve exactamente los
bytes del archivo indicado por la ruta IFC de B; no sustituye geometría por primitivas. No mide
rendimiento: la captura archivada usa SwiftShader/CPU. El fixture permanece etiquetado sintético/DRAFT.

La apertura en tres visores y sus capturas quedan documentadas. En BIMvision falta contrastar
unidades, dimensiones y propiedades del recipiente; la captura aportada solo acredita apertura
y visualización con propiedades de proyecto visibles. No se declara equivalencia de mallas,
fidelidad contra TR, validación de todas las familias/esquemas ni rendimiento medido.
La herramienta de automatización no llegó a detectar esa ventana: la apertura fue manual.
