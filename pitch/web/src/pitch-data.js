// Punto de edición del pitch. Los resultados de esta versión proceden de sintéticos.
// Las cifras del evento llegan por cifras-evento.js (python -m bench.cifras aplicar).
import { cifrasEvento } from "./cifras-evento.js";

const base = {
  brand: "TrazIA·3D",
  challenge: "GA2MODEL · IndesIAhack 2026",
  dataset: "Datos sintéticos",
  demoOrigin: "http://127.0.0.1:3120",
  equipment: "V-101",
  media: {
    plan: "media/ga.webp",
    planPdf: "media/GA-V101-B.pdf",
    evidence: "media/evidence.webp",
    ifcA: "media/ifc-a.webp",
    ifcB: "media/ifc-b.webp",
    outline: "media/ifc-contour.webp",
    // Rutas en public/. Dejar "" hasta incorporar una grabación autorizada.
    modelVideo: "",
    changesVideo: "",
  },
  baseline: {
    hours: "1.800–10.000",
    factors: [
      ["300–500", "equipos por proyecto"],
      ["3–5", "revisiones por equipo"],
      ["2–4 h", "de modelado manual por revisión"],
    ],
  },
  evidence: {
    path: "equipment.height",
    value: 6500,
    unit: "mm",
    document: "GA-V101",
    page: 1,
    confidence: 0.75,
  },
  study: {
    label: "Estudio 7 · Puntuación compuesta · Sintéticos",
    variants: [
      { key: "A", label: "Geometría", score: 0.578 },
      { key: "B", label: "Reglas + OCR", score: 0.609 },
      { key: "C", label: "RAG", score: 0.600 },
      { key: "D", label: "Híbrido", score: 0.708 },
    ],
    selected: "D",
    interval: "IC 95 %: 0,676–0,740",
  },
  changes: [
    { field: "Longitud de virola", before: "6.000", after: "6.500", delta: "+500 mm" },
    { field: "Altura de faldón", before: "1.200", after: "1.350", delta: "+150 mm" },
    { field: "Elevación de N3", before: "3.500", after: "3.700", delta: "+200 mm" },
    { field: "Boquilla N4", before: "—", after: "6.200", delta: "Añadida" },
  ],
  batch: {
    population: 336,
    drafts: 251,
    errors: 85,
    speedup: "1,47×",
    detail: "CPU · 4 workers frente a 1 · lote sintético del 02/11",
  },
};

const formato = (valor, decimales = 0) => valor == null ? "sin medir"
  : new Intl.NumberFormat("es-ES", { maximumFractionDigits: decimales, useGrouping: "always" }).format(valor);

const porcentaje = (valor) => valor == null ? null : valor * 100;

// Sustituye el lote sintético por el del evento y añade la medida contra los IFC de TR.
// Sin cifras devuelve el pitch tal cual: nada del evento aparece hasta que se aplica.
export function conCifras(pitchBase, escenas, cifras) {
  if (!cifras?.lote) return { pitch: pitchBase, scenes: escenas };
  const { lote, evaluacion } = cifras;
  const pitch = {
    ...pitchBase,
    dataset: "Sintéticos + agregados del reto",
    batch: {
      population: lote.revisiones,
      drafts: lote.correctas,
      errors: lote.errores,
      speedup: null,
      medianSeconds: lote.segundos_mediana,
      detail: `Dataset del reto · Azure Databricks · ${cifras.fecha}`,
    },
    evaluation: evaluacion ?? null,
  };
  const medida = evaluacion?.equipos
    ? ` Contra los IFC de referencia de TR, en ${evaluacion.equipos} equipos, el error medio del diámetro es del ${formato(porcentaje(evaluacion.error_relativo_diametro), 1)} % y encontramos el ${formato(porcentaje(evaluacion.boquillas_recall))} % de las boquillas.`
    : " La comparación con los IFC de TR todavía no tiene cifra.";
  const scenes = escenas.map((scene) => scene.id !== "scale" ? scene : {
    ...scene,
    notes: `Con el dataset del reto procesamos ${formato(lote.revisiones)} revisiones de ${formato(lote.equipos)} equipos: ${formato(lote.correctas)} IFC DRAFT y ${formato(lote.errores)} errores, con una mediana de ${formato(lote.segundos_mediana, 1)} segundos por revisión.${medida} Los DRAFT miden cobertura; la fidelidad es la comparación con la referencia.`,
  });
  return { pitch, scenes };
}

export const chapters = [
  { id: "problem", name: "Problema" },
  { id: "input", name: "Entrada" },
  { id: "reading", name: "Extracción" },
  { id: "model", name: "Modelo 3D" },
  { id: "change", name: "Cambios" },
  { id: "impact", name: "Impacto" },
];

const baseScenes = [
  {
    id: "open", chapter: "problem", seconds: 24,
    title: "Un plano cambia.", accent: "¿Qué más cambia?",
    subtitle: "Del plano 2D a un modelo 3D que conserva la evidencia de cada cota.",
    notes: "En ingeniería, una revisión puede cambiar una sola medida del plano y obligar a varias disciplinas a localizarla, interpretarla y actualizar sus modelos. Hoy vamos a seguir un equipo y dos revisiones, desde el documento de entrada hasta la decisión de quien revisa. Esta versión del recorrido utiliza un recipiente sintético.",
  },
  {
    id: "cost", chapter: "problem", seconds: 21,
    title: "Horas que se repiten.", accent: "",
    subtitle: "Trabajo de transcripción estimado por proyecto en el enunciado.",
    notes: "El reto sitúa un proyecto típico entre trescientos y quinientos equipos, con tres a cinco revisiones por equipo y dos a cuatro horas de modelado por revisión. De ahí sale este rango. Nuestro objetivo es que el ingeniero dedique su tiempo a comprobar cambios y resolver discrepancias.",
  },
  {
    id: "input", chapter: "input", seconds: 45,
    demoPath: "/documentos",
    title: "Un equipo.", accent: "Una revisión.",
    subtitle: "El plano GA y la hoja de datos entran juntos. Cada documento queda identificado por su huella.",
    notes: "Empezamos por la revisión B del equipo V-101. Al añadir el plano y su hoja técnica, el sistema conserva los originales, identifica la revisión y agrupa las fuentes. Un plano vectorial permite leer texto y tablas directamente. Si solo hay una imagen, el flujo usa OCR. Si volvemos a presentar el mismo trabajo, la caché por huella permite reutilizar el resultado. Aquí podemos abrir la demo y enseñar la entrada preparada para este equipo.",
  },
  {
    id: "trace", chapter: "reading", seconds: 36,
    demoPath: "/modelo?vista=revision",
    title: "Una cota.", accent: "Su evidencia.",
    subtitle: "La persona que revisa puede volver del valor a la zona exacta del documento.",
    notes: "Vamos a la longitud de virola. El ejemplo devuelve 6.500 milímetros y enlaza este valor con la página uno del GA. Al seleccionar el campo vemos su recorte. La confianza de esta ficha viene del lector de etiquetas de la demo; en el estudio medimos la calibración por separado. Si falta una cota crítica o las fuentes discrepan, queda pendiente para revisión.",
  },
  {
    id: "bench", chapter: "reading", seconds: 24,
    demoPath: "/bench",
    title: "Probamos cuatro", accent: "formas de leer.",
    subtitle: "El híbrido obtuvo la mayor puntuación en este estudio sobre sintéticos.",
    notes: "Comparamos una variante de geometría, otra de reglas con OCR, una de recuperación y una híbrida. En este estudio sintético D obtiene 0,708 en la métrica compuesta. La puntuación agrega varios criterios, incluida la calibración. El resultado orienta la estrategia que probaremos con el conjunto del reto.",
  },
  {
    id: "model", chapter: "model", seconds: 75,
    demoPath: "/modelo?vista=3d",
    title: "Del plano", accent: "al modelo.",
    subtitle: "Las cotas estructuradas instancian la geometría del recipiente. El IFC conserva la identidad de sus piezas.",
    notes: "Este render procede del IFC de la revisión B. Podemos abrir el modelo en vivo desde el enlace y girarlo, ver el alzado y seleccionar una boquilla. Señalamos cómo el dato de origen llega a la pieza que puede comprobar el equipo de ingeniería. La exportación empieza en estado DRAFT. Para aprobarla hace falta revisar los campos pendientes y comprobar que los originales corresponden a la huella de la revisión. Si la demo en directo falla, enseñamos el modelo de esta escena y la grabación que haya preparado el equipo.",
  },
  {
    id: "delta", chapter: "change", seconds: 75,
    demoPath: "/modelo?vista=cambios",
    title: "Una nueva revisión.", accent: "Cuatro cambios.",
    subtitle: "Comparamos A y B con la misma cámara. El delta identifica la pieza, el campo y la variación.",
    notes: "Ahora comparamos A y B. En el equipo sintético crece la virola, aumenta el faldón, se desplaza N3 y se añade N4. Leemos primero el cambio de quinientos milímetros de virola en la tabla y señalamos qué parte del modelo cambia. Después distinguimos N3, que mantiene su identidad y cambia de posición, de N4, que es una pieza nueva. Si abrimos la demo en vivo, mostramos el resaltado y dónde queda su evidencia en el plano. Es el momento de explicar por qué conservar la identidad entre revisiones evita interpretar un desplazamiento como un alta y una baja.",
  },
  {
    id: "scale", chapter: "impact", seconds: 38,
    title: "El lote escala.", accent: "La calidad se mide.",
    subtitle: "La cola distribuye trabajos, la caché reutiliza entradas y la revisión se concentra en las excepciones.",
    notes: "En un lote de 336 revisiones sintéticas obtuvimos 251 IFC DRAFT y 85 errores. Con cuatro workers CPU el lote terminó 1,47 veces más rápido que con uno en la misma máquina. El número de DRAFT mide cobertura de exportación. Para medir fidelidad hay que contrastarlos con una referencia. Con los datos del evento repetiremos ese contraste y documentaremos los casos que necesiten revisión.",
  },
  {
    id: "close", chapter: "impact", seconds: 22,
    title: "Cada cota.", accent: "Una decisión trazada.",
    subtitle: "Del documento original a la decisión de ingeniería.",
    notes: "Queremos que cada cambio llegue al equipo con la cifra, el plano donde se leyó y la pieza que modifica. La siguiente prueba es medir la fidelidad del IFC sobre la referencia del reto y cronometrar la revisión humana. Con esas dos medidas podremos hablar de ahorro con una base defendible. Gracias.",
  },
];

export const { pitch, scenes } = conCifras(base, baseScenes, cifrasEvento);
