# Revisión del ROADMAP · 28/10/2026

Corte de código: `10f649d` (Lectura y Plataforma integradas en main). Trabajo aislado en
`TrazIA-3D-prueba-carga`, rama `chore/roadmap-cpu`. No se tocan los tres cambios locales de
escala presentes en el worktree main. La medición se cerró sin commit ni push; su publicación
posterior en GitHub está autorizada por el usuario.

## Casillas corregidas antes de continuar

18 tareas ya implementadas: 2.3, 2.6, 2.7, 2.8, C.3, C.5, C.7, E.4,
F.1, F.2, F.7, F.8, G.6, G.7, H.2, H.4, H.5 y H.6. Cada entrada del ROADMAP
incluye su código o prueba de referencia. Las pruebas son ejecutables en CPU; ninguna casilla
supone precisión garantizada en documentos reales.

## Tareas que siguen abiertas

- 0.1–0.4 y 0.9: requieren información, inscripción o coordinación del equipo.
- 0.10: Qwen 4B y RapidOCR tienen medidas; Qwen 8B y PaddleOCR-VL no.
- 1.9: falta un segundo proveedor real y conocer la plataforma; los mocks no cierran el criterio.
- 2.1 y 2.2: B/RapidOCR existen; no se da por completado VESOR ni PaddleOCR-VL.
- 2.4: tener entrenamiento y conversión de etiquetas no acredita un detector ajustado/medido.
- 2.5: C v1 utiliza una huella ligera y texto; no ColQwen2/ColSmol.
- 2.11: falta tabla completa A/B/C/D en S-dev con intervalos; el banco v1 no la sustituye.
- 3.2: hay canal de memoria, pero el código actual acepta DRAFT como revisión anterior.
- 3.3 y 3.4: faltan calibración/conformal y fusión aprendida/selector medidos en reservado.
- 3.7: la evidencia versionada de escala todavía es parcial; los cambios locales de main no
  se cuentan como una ejecución terminada ni se modifican aquí.
- H.1 y H.3: `POST /estudio` devuelve 503; no se simula un ejecutor ni un estudio completado.
- G.3/G.4/G.8/G.9: hay métricas e informes parciales; no se confunden IoU de cajas,
  intervalos bootstrap y cobertura conforme, ni se da por hecha la visualización del error.
- F.5: los marcadores siguen siendo heurísticos y no se da por validada su detección.
- F.4 y F.6 se completan en esta tanda con reglas de coordinación y Markdown; BCF 3.0
  permanece sin implementar (se entrega 2.1).
- Tareas de UI, entrenamiento, modelos y mediciones GPU: fuera de esta tanda.

## Medición anterior

La ejecución de carga del 27/10 se interrumpió antes de cerrar las ablaciones de D.
Se conservan generación de 40 equipos, banco, B inicial, biblioteca y las condiciones ya medidas
bajo generated/bench. No se contabilizan el comparativo ni las tres pasadas pytest como finalizados.
La reanudación debe utilizar esos checkpoints y registrar la interrupción, sin inventar tiempos.

## Trabajo siguiente sin GPU

Exportación CSV/Excel de campos con trazabilidad (C.6), artefactos del banco en CI (G.6),
y completar la medición CPU pendiente. Validación y resultados se añadirán al terminar.

## Implementación CPU de esta tanda

- **C.6**: `trazia fields` produce CSV UTF-8 y XLSX con valores, unidades, estado,
  evidencia, SHA, intervalos y alternativas. Lectura de revisión sin mutación ni aprobación;
  texto de documentos literal en Excel, formato inválido/texto truncable rechazado.
- **F.3/F.4**: delta con categorías y reglas explicadas de disciplinas, severidad y acción.
  Peso/faldón → Civil/Estructuras; conexiones → Piping; servicio instrumental → I&C;
  presión/temperatura → Mecánica/Procesos. Los cambios solo de procedencia son documentales.
- **F.6**: salida Markdown del mismo delta JSON, fuentes y huellas de las dos revisiones;
  BCF 2.1 permanece disponible. No requiere un visor ni un modelo de IA.
- **G.6**: CI ahora conserva report.md/report.json/cases.json de un banco CLI de dos equipos.
  Las pruebas de regresión siguen ejecutándose; el paso de archivado usa always() para conservar los artefactos disponibles tras un fallo.
- README: se corrige la descripción obsoleta que negaba la existencia de OCR y estrategias.

Pruebas dirigidas: 29 pasan en 15,74 s para exportación e impacto; tras añadir Markdown,
las 10 pruebas de exportación pasan en 0,40 s. Ruff global y formato pasan (119 archivos).
Los comandos del banco CLI de CI pasan localmente: dos equipos, tres estilos, sin GPU.
Al cerrar la medición solo se habían comprobado los comandos de CI localmente.

Un primer intento dirigido de pytest.exe fue bloqueado por Control de aplicaciones (4551);
se comprobó con `python -m pytest`. Después el lanzador funcionó: las tres pasadas completas
usaron el comando exacto `uv run pytest -q`, sin necesitar el fallback por módulo.

Medición CPU completada: 1.200 condiciones únicas, diez variantes, 2.400 revisiones; cada
variante usa los mismos 40 equipos con tres estilos y dos revisiones, bootstrap de 1.000
remuestreos por equipo. Se reutilizaron 843 condiciones completas del 27/10 y se midieron las
357 restantes el 28/10; reanudación y estadística: 1.280,52 s. No se inventa la duración de
pared del tramo interrumpido. El [informe versionado](evidencias/cpu-2026-10-28/prueba_carga.md)
y los [JSON y scripts de reproducción](evidencias/cpu-2026-10-28/README.md) conservan el detalle.
Las diez variantes registran cero llamadas externas; no se llama a Ollama ni a un proveedor.
Este banco v1 no cierra 2.11 ni G.8 para S-dev/S-reservado v2.

Tres pasadas consecutivas con `uv run pytest -q`:

| Pasada | Resultado | Pared | Tiempo pytest |
| --- | --- | --- | --- |
| 1 | 225 passed, 0 fallos | 195,33 s | 193,59 s |
| 2 | 225 passed, 0 fallos | 157,40 s | 156,09 s |
| 3 | 225 passed, 0 fallos | 155,00 s | 153,68 s |

Cada pasada muestra una advertencia conocida de Starlette/HTTPX. No hay pruebas omitidas.
Las 18 casillas corregidas al inicio y las cuatro tareas nuevas (C.6, F.3, F.4, F.6) tienen
validación CPU. La configuración de CI se comprobó localmente antes de publicar.
El commit y el push posteriores incluyen estas evidencias, por autorización del usuario.
No se ejecuta entrenamiento, inferencia de visión, aplicación 3D ni benchmark de GPU.
