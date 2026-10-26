/*
  Definición de las etapas del pipeline tal como existen hoy en src/trazia.
  `available: false` = está en el roadmap pero no implementado: se muestra como "Próximamente"
  y la repetición simulada la salta. No se inventan latencias ni costes.
*/

export type StageId =
  | "ingest"
  | "classify"
  | "extract_labels"
  | "extract_tables"
  | "extract_ocr"
  | "extract_vision"
  | "extract_hdm"
  | "reconcile"
  | "family"
  | "ifc"
  | "validate";

export type StageDef = {
  id: StageId;
  name: string;
  code: string;
  description: string;
  available: boolean;
  /** Módulo del núcleo que la implementa. */
  module?: string;
};

export const STAGES: StageDef[] = [
  {
    id: "ingest",
    name: "Ingesta",
    code: "ingest",
    description: "Registra cada PDF y Excel con su SHA-256, páginas, regiones de texto y celdas.",
    available: true,
    module: "ingest.py",
  },
  {
    id: "classify",
    name: "Clasificación",
    code: "classify",
    description: "Agrupa documentos por TAG y revisión y detecta el GA dentro de un paquete.",
    available: false,
  },
  {
    id: "extract_labels",
    name: "Etiquetas del plano",
    code: "extract.labels",
    description: "Lee parámetros rotulados en el texto del GA y guarda página y región.",
    available: true,
    module: "extraction.py",
  },
  {
    id: "extract_tables",
    name: "Tablas vectoriales",
    code: "extract.tables",
    description: "Reconstruye la tabla de boquillas a partir de líneas y palabras del PDF.",
    available: false,
  },
  {
    id: "extract_ocr",
    name: "OCR",
    code: "extract.ocr",
    description: "Lee planos escaneados e imágenes con cajas de texto.",
    available: false,
  },
  {
    id: "extract_vision",
    name: "Visión",
    code: "extract.vlm",
    description: "Interpreta vistas y cotas con un modelo multimodal que debe citar la región.",
    available: false,
  },
  {
    id: "extract_hdm",
    name: "Hoja de datos",
    code: "extract.hdm",
    description: "Lee presión, temperatura, material y pesos de la hoja de datos en Excel.",
    available: true,
    module: "extraction.py",
  },
  {
    id: "reconcile",
    name: "Normalización",
    code: "reconcile",
    description: "Convierte unidades, junta candidatos y bloquea valores contradictorios.",
    available: true,
    module: "extraction.py · model.py",
  },
  {
    id: "family",
    name: "Familia",
    code: "family",
    description: "Instancia el recipiente vertical: virola, fondos, faldón y boquillas.",
    available: true,
    module: "model.py",
  },
  {
    id: "ifc",
    name: "IFC",
    code: "ifc",
    description: "Escribe el IFC4 DRAFT con GUID estables y trazabilidad por elemento.",
    available: true,
    module: "ifc.py",
  },
  {
    id: "validate",
    name: "Validación",
    code: "validate",
    description: "Comprueba geometría y deja el modelo listo para revisión humana.",
    available: true,
    module: "model.py · review.py",
  },
];

/** Aristas del grafo: los extractores corren en paralelo entre clasificación y normalización. */
export const STAGE_EDGES: [StageId, StageId][] = [
  ["ingest", "classify"],
  ["classify", "extract_labels"],
  ["classify", "extract_tables"],
  ["classify", "extract_ocr"],
  ["classify", "extract_vision"],
  ["classify", "extract_hdm"],
  ["extract_labels", "reconcile"],
  ["extract_tables", "reconcile"],
  ["extract_ocr", "reconcile"],
  ["extract_vision", "reconcile"],
  ["extract_hdm", "reconcile"],
  ["reconcile", "family"],
  ["family", "ifc"],
  ["ifc", "validate"],
];

export type PipelineEvent = {
  id: string;
  stage: StageId;
  file: string;
  status: "ok" | "omitido" | "error";
  detail: string;
  /** Segundos desde el inicio de la repetición. */
  at: number;
};
