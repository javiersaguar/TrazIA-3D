import type { StageId } from "@/lib/mock/pipeline";

export type Strategy = "a_vision" | "b_reglas" | "c_rag" | "d_hibrido";
export const PROFILES: Record<Strategy, { name: string; detail: string; channels: StageId[] }> = {
  a_vision: { name: "A · Visión + 3D", detail: "Los trazos aportan la geometría; las cotas fijan la escala. El modelo visual depende del proveedor configurado.", channels: ["extract_ocr", "extract_vision", "geometry2d", "extract_hdm"] },
  b_reglas: { name: "B · Datos + reglas", detail: "Texto, tablas y hoja de datos. OCR cuando el documento o la variante lo requieren; los valores ausentes no se inventan.", channels: ["extract_labels", "extract_tables", "extract_ocr", "extract_hdm"] },
  c_rag: { name: "C · Recuperación", detail: "Una plantilla aprobada indica dónde mirar. Cada valor debe comprobarse en el documento actual.", channels: ["rag", "extract_ocr", "extract_hdm"] },
  d_hibrido: { name: "D · Híbrido", detail: "Combina reglas, recuperación, memoria aprobada y geometría; detector y visión dependen de su configuración. La fusión resuelve las evidencias.", channels: ["extract_labels", "extract_tables", "extract_ocr", "extract_hdm", "rag", "memory", "geometry2d", "extract_detector", "extract_vision"] },
};
export const CONDITIONAL: Partial<Record<StageId, string>> = {
  extract_ocr: "Según documento / variante", extract_vision: "Según proveedor", extract_detector: "Según configuración",
  memory: "Solo revisión anterior aprobada", rag: "Requiere biblioteca aprobada", calibrate: "Con calibración disponible",
};
export const NODE_WIDTH = 200;
export const NODE_HEIGHT = 96;

/** Mapa lógico: todos los canales ocupan una sola columna. Los colectores quedan
 * en pasillos vacíos, nunca dentro de otra tarjeta. No representa paralelismo real. */
export function graphModel(strategy: Strategy, observed: StageId[] = []) {
  const channels = [...new Set([...PROFILES[strategy].channels, ...observed.filter(id => !["ingest", "classify", "reconcile", "calibrate", "family", "ifc", "validate"].includes(id))])];
  const center = (channels.length - 1) * 112 / 2;
  const positions: Partial<Record<StageId, { x: number; y: number }>> = {
    ingest: { x: 0, y: center }, classify: { x: 240, y: center },
    reconcile: { x: 760, y: center }, calibrate: { x: 1000, y: center },
    family: { x: 1240, y: center }, ifc: { x: 1480, y: center }, validate: { x: 1720, y: center },
  };
  channels.forEach((id, i) => { positions[id] = { x: 480, y: i * 112 }; });
  const ids: StageId[] = ["ingest", "classify", ...channels, "reconcile", "calibrate", "family", "ifc", "validate"];
  const edges: [StageId, StageId][] = [["ingest", "classify"], ...channels.flatMap(id => [["classify", id], [id, "reconcile"]] as [StageId, StageId][]), ["reconcile", "calibrate"], ["calibrate", "family"], ["family", "ifc"], ["ifc", "validate"]];
  return { ids, channels, positions, edges };
}
