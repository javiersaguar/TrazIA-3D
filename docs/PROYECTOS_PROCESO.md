# Proyectos sintéticos de petróleo y gas

En **Documentos → Proyectos → Proyectos 3D de petróleo y gas** se puede abrir cada
complejo, elegir su entorno en el visor y cambiar entre las revisiones A y B.
La preferencia de entorno se guarda por proyecto en el navegador. El contraste
visual se aplica a cualquier proyecto. El escenario base identifica la
implantación para la que se prepararon los planos.

**Neutro · estudio** muestra el mismo IFC con luz de estudio y rejilla.
Mar abierto tiene oleaje, espuma alrededor de los apoyos, gaviotas y un
buque de apoyo. Costa y muelle tiene oleaje con abrigo, un metanero y un
remolcador. En Desierto se animan las plantas rodantes y el polvo. Las
unidades vecinas de la refinería tienen chimeneas con vapor y balizas.
El control de pausa es independiente del giro de la cámara. El movimiento se
detiene fuera del visor visible y se desactiva con la preferencia de
movimiento reducido del sistema.

| Proyecto | Escenario base | Cambios ensayables |
| --- | --- | --- |
| SIM-MAR · Plataforma de producción | Mar abierto | Virola del separador V-110 y elevación del tramo GS-04 |
| SIM-DES · Planta de tratamiento de gas | Desierto | Altura de columna TEG C-230 y diámetro del spool DG-14 |
| SIM-GNL · Terminal de almacenamiento | Costa y muelle | Envolvente de tanque T-340 y desvío de línea LNG-21 |
| SIM-REF · Ampliación de refinería | Complejo industrial | Altura del reactor R-440 y elevación de la conexión LP-33 |

El primer clic selecciona el equipo o línea y el siguiente baja a la pieza.
La cámara calcula un encuadre en perspectiva según el tamaño, la elevación y
la visibilidad. Las piezas que siguen tapando la selección se atenúan y
**Aislar selección** permite inspeccionarla sola. Desde la ficha se abren las
piezas IFC, sus propiedades e identificadores y las cotas X, Y y Z. <kbd>Esc</kbd>
sube al conjunto o a la vista general. Alzado y Planta son vistas ortográficas.

Los cambios preparados de la revisión B se pueden aplicar también por
separado. Con la API conectada, **Ensayar cambios** admite las dimensiones
del equipo y los parámetros de la línea publicados en su ficha. La API
regenera la planta, comprueba el IFC4 y mantiene los GUID de los elementos
que conservan su identidad. Los puertos coinciden con sus conexiones.
El ensayo es un IFC DRAFT descargable. Los planos y Excel corresponden a
las revisiones documentales A y B.

La cubierta de SIM-MAR está a +16 m en el sistema local del modelo. El IFC
incluye el entramado de vigas y la estructura arriostrada de seis patas,
con defensas, escala y pasarela de embarque. Los equipos y líneas de los
cuatro complejos incorporan detalles según su familia, como bridas con
pernos, volantes de válvula, descansillos o ventiladores con aspas y guardas.
Los planos y las listas proceden de esa geometría. El agua, las dunas y las
plantas rodantes se dibujan en el visor como contexto visual.

## Planos, listas y carga al pipeline

Cada proyecto aporta dos dossiers ZIP, uno por revisión. Cada dossier contiene
el IFC de planta, el GA de implantación A3, el libro general con listas de
equipos, líneas, puntos de trazado, componentes y cambios, y un PDF y un
Excel para cada uno de los siete equipos. Los ficheros emplean coordenadas
locales y están rotulados como sintéticos.

Para practicar la entrada por API, descarga el PDF y el XLSX **del mismo
equipo y revisión**. Selecciónalos juntos en **Pipeline → Procesar planos y
hojas de datos**. Usa B · Reglas y el origen sintético. El flujo reconstruye
su envolvente LOD 1 desde seis cotas explícitas y guarda las evidencias.
El detalle de planta, los soportes y las uniones se consultan en el IFC
del dossier. La carga web admite una revisión por trabajo.

## Regeneración y rendimiento

```powershell
uv sync --frozen --extra dev --extra api
uv run --extra dev --extra api python scripts/make_process_projects.py
uv run --extra dev --extra api python -m pytest -q tests/test_process_projects.py
```

La definición común vive en `src/trazia/process_catalog/process_projects.py`. El generador
produce los archivos de `web/public/demo/proceso/` y el catálogo del
frontend. Valida el esquema IFC4 y aplica un presupuesto por variante de
3,5 MB descargables, 900 KB de transporte y 95.000 triángulos.
Las piezas repetidas reutilizan mallas mediante `IfcMappedItem`.
El navegador descomprime el IFC de demostración en el worker y solicita una
sola variante al abrir el proyecto. Las miniaturas WebP se regeneran con
`uv run python scripts/miniaturas_proceso.py` y capturan la revisión A.

Los escenarios se inspiran en tipos de proyectos publicados por Técnicas
Reunidas. Las distribuciones, materiales, dimensiones y cambios del
catálogo son conceptuales y se han generado para TrazIA-3D.

- Mar abierto y desierto. Proyectos Lower Zakum y Jafurah en los
  [resultados de Técnicas Reunidas](https://www.tecnicasreunidas.es/wp-content/uploads/2025/11/Tecnicas-Reunidas-9M-2025-Results-Release-ESP-FINAL-6.11.25-21h.pdf).
- Costa con muelle. [Terminal de regasificación de gas natural](https://www.tecnicasreunidas.es/es/proyecto/lng-terminal-de-regasificacion-de-gas-natural/).
- Complejo industrial. [Modernización y ampliación de la refinería BAPCO](https://www.tecnicasreunidas.es/es/proyecto/bapco-modernization-program/).
