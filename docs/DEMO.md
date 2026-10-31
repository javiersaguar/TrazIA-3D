# Guion de la demo · 6 minutos

Sigue la estructura de [ROADMAP J.1](ROADMAP.md#j-pitch-presentación-y-negocio): plano → dato →
modelo → cambio → decisión. Es el guion de la web; Streamlit (`uv run trazia serve`) queda solo
como reserva interna.

Hasta el 25/11 todo lo que se enseña es **sintético** y se dice al empezar. Las cifras salen de
[ESTUDIO.md](ESTUDIO.md) el mismo día del ensayo, nunca de memoria. Desde el 25/11 se sustituyen por
las medidas en el dataset de TR, siempre separadas de las sintéticas.

## Antes de subir al escenario

```powershell
uv sync --frozen --extra dev --extra api --extra ocr
$env:TRAZIA_OFFLINE = "1"                     # solo cachés: sin red ni inferencia nueva
uv run --extra api python -m trazia.api       # API en 127.0.0.1:8000
```

```powershell
# En otra consola, desde web/
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000"
pnpm build; pnpm start                        # http://localhost:3000
```

Sin `NEXT_PUBLIC_API_URL`, la web sigue funcionando con los datos sintéticos de `public/demo/`.
Ese es el **plan B** si cae la API. El **plan C** es el vídeo (tarea 4.6), abierto en otra pestaña.

Comprobar en este orden, 30 minutos antes:

1. Recorrer las rutas del guion una vez, para que el IFC y los PDF queden en caché del navegador.
2. Tema oscuro; modo claro solo si la sala es muy luminosa. 1920×1080 y ratón físico.
3. Antes de la primera demo en una máquina nueva: `TRAZIA_OFFLINE=1` no crea pesos ni cachés
   que no existan. Hay que prepararlos con red ([modo offline](BACKEND_2026-10-30.md)).

## Recorrido

| Tiempo | Pantalla | Qué se hace | Qué se dice |
| --- | --- | --- | --- |
| 0:00–0:45 | `/proyecto` | Planta con los equipos del lote | «La geometría viaja como documento, no como dato.» Avisar: datos sintéticos |
| 0:45–1:30 | `/documentos` → `/pipeline` | Abrir el paquete del equipo y ver las etapas | Hash de cada original, lectura en cascada, todo local |
| 1:30–2:30 | `/revision` | Seleccionar un campo: valor, recorte del plano, confianza e intervalo | «Cada valor cita su región. Si no se puede citar, no entra.» Enseñar un campo en abstención |
| 2:30–3:45 | `/lab/firma` → `/modelo` | Plano que se convierte en modelo; aislar una boquilla | «Lo que veis es el IFC, no un dibujo aparte.» Citar puertos, trazabilidad y aprobación dentro del IFC |
| 3:45–5:00 | `/cambios` | Morph de A a B y grafo de impacto; exportar BCF | N3 sube 200 mm, faldón +150 mm, virola +500 mm, peso +800 kg, N4 nueva. «Qué cambió, cuánto, dónde y a quién afecta» |
| 5:00–6:00 | `/estudio` → `/lote` | Tabla A/B/C/D y resultado del lote | «Probamos las estrategias que proponéis y elegimos con datos.» Límites, en voz alta |

Fin alternativo si sobra tiempo: modificar un valor tras aprobar. La aprobación desaparece y vuelve
DRAFT, porque está ligada a la huella de los datos.

## Lo que se dice sobre los límites

Decirlo antes de que lo pregunten:

- Las cifras son sintéticas hasta medir contra los IFC de TR. Citar siempre por tipo de documento:
  la media mezcla vectorial y escaneado en la proporción que eligió nuestro generador.
- La calibración aguanta en proveedores conocidos y no en proveedores no vistos. La ordenación por
  riesgo sí sirve: por eso la revisión empieza por lo más dudoso.
- La salida automática es siempre DRAFT. Un DRAFT puede tener boquillas sin colocar, y el contrato
  dice cuáles; para aprobar hacen falta revisión humana, originales verificados y tres boquillas.
- «Alucinación 0 %» significa que el número está en la región citada, no que sea el número correcto:
  el fallo que no mide esa cifra es leer un dato real en el campo equivocado.
- Un intervalo conforme garantiza su cobertura si los datos se parecen a los de calibración. Con un
  proveedor nuevo es una comprobación empírica, no una garantía.
