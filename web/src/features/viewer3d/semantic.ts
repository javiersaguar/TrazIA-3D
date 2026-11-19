import type { PropertySets } from "@/workers/ifc-protocol";

/**
 * Identidad estable de un producto o ensamblaje IFC.
 *
 * Proyectos de proceso (pset TrazIA_Traceability con ProcessProject):
 * - raíz de equipo, línea o estructura → `element:TAG` (Component, o el Tag/Name del IFC);
 * - pieza agregada (ParentComponent) → `detail:element:TAG/clave`, con `clave` sacada de
 *   Component = "TAG/clave". parentElementId() la devuelve a `element:TAG`.
 */
export function semanticId(
  name: string,
  ifcType: string,
  psets: PropertySets = {},
  tag?: string,
): string {
  const trace = psets.TrazIA_Traceability;
  if (trace?.ProcessProject) {
    const component = String(trace.Component ?? tag ?? name);
    const parent = trace.ParentComponent ? String(trace.ParentComponent) : "";
    if (!parent) return `element:${component}`;
    const key = component.startsWith(`${parent}/`)
      ? component.slice(parent.length + 1)
      : component.split("/").slice(1).join("/") || component;
    return `detail:element:${parent}/${key}`;
  }
  const identity = psets.TrazIA_Identity ?? psets.GA2MODEL_Identity;
  const component = String(
    identity?.ComponentId ?? identity?.NozzleId ?? name.split("/").at(-1) ?? "",
  );
  const parent = String(identity?.ParentComponentId ?? "");
  if (parent) {
    const known: Record<string, string> = {
      shell: "shell",
      skirt: "skirt",
      top_head: "head-top",
      bottom_head: "head-bottom",
    };
    const root = known[parent] ?? `nozzle:${parent}`;
    return `detail:${root}/${component}`;
  }
  if (component === "shell" || ifcType.toUpperCase() === "IFCTANK")
    return "shell";
  if (component === "top_head") return "head-top";
  if (component === "bottom_head") return "head-bottom";
  if (component === "skirt") return "skirt";
  if (ifcType.toUpperCase() === "IFCPIPESEGMENT" || /^N\d+$/i.test(component)) {
    return `nozzle:${component}`;
  }
  return `element:${component}`;
}

/** Un detalle conserva identidad propia y apunta al elemento que tiene evidencia. */
export function parentElementId(id: string): string {
  return id.startsWith("detail:") ? id.slice(7).split("/")[0]! : id;
}

/** Un supuesto afecta solo a la pieza cuyos parámetros lo contienen. */
export function hasAssumption(id: string, psets: PropertySets): boolean {
  if (psets.Pset_TrazIA?.ClaseOrigen === "supuesto_visual") return true;
  const raw = psets.TrazIA_Traceability?.FieldsJSON;
  if (typeof raw !== "string") return false;
  try {
    const fields: unknown = JSON.parse(raw);
    if (!fields || typeof fields !== "object" || Array.isArray(fields)) return false;
    const parent = parentElementId(id);
    const related = parent.startsWith("nozzle:") ? (path: string) => path.startsWith(`nozzles.${parent.slice(7)}.`)
      : parent === "skirt" ? (path: string) => path.startsWith("skirt_")
      : parent.startsWith("head-") ? (path: string) => path === "head_depth" || path === "diameter"
      : (path: string) => path === "diameter" || path === "height";
    return Object.entries(fields).some(([path, value]) => related(path) && value && typeof value === "object"
      && "state" in value && value.state === "assumed");
  } catch { return false; }
}

export function elementForField(path: string): string {
  if (path.startsWith("nozzles.")) return `nozzle:${path.split(".")[1]}`;
  if (path.startsWith("skirt")) return "skirt";
  if (path === "head_depth") return "head-top";
  return "shell";
}

export function elementLabel(id: string): string {
  const labels: Record<string, string> = {
    shell: "Virola",
    "head-top": "Fondo superior",
    "head-bottom": "Fondo inferior",
    skirt: "Faldón",
  };
  if (id.startsWith("detail:")) {
    const component = id.slice(id.indexOf("/") + 1);
    if (component.startsWith("lug-")) return "Orejeta de izado";
    if (component.includes("/anchor-")) return "Perno de anclaje";
    if (component.includes("/bolt-")) return "Perno de brida";
    if (component === "base/ring") return "Anillo base";
    if (component === "manway/cover") return "Tapa de boca de hombre";
    if (component === "manway/davit") return "Pescante";
    if (component.startsWith("manway")) return "Boca de hombre";
    if (component.endsWith("/flange"))
      return `Brida · ${elementLabel(parentElementId(id))}`;
    return component;
  }
  return (
    labels[id] ??
    id.replace("nozzle:", "Boquilla ").replace("element:", "Elemento ")
  );
}

/** Lo mínimo para rotular un producto o un ensamblaje leído del IFC. */
export type LabelSource = {
  semanticId: string;
  name: string;
  tag?: string;
  description?: string;
  psets: PropertySets;
};

const text = (value: unknown) => (typeof value === "string" && value.trim() ? value.trim() : undefined);

/** Tag de proceso: "P-150" en la raíz y "P-150/motor-a" en una pieza. */
export function processTag(source: LabelSource): string | undefined {
  if (!source.psets.TrazIA_Traceability?.ProcessProject) return undefined;
  return text(source.psets.TrazIA_Traceability.Component) ?? text(source.tag) ?? text(source.name);
}

/** Nombre legible corto: la Description de la pieza o del equipo ("Virola", "Bomba de inyección"). */
export function shortLabel(source: LabelSource): string {
  const trace = source.psets.TrazIA_Traceability;
  if (trace?.ProcessProject) {
    const description = text(trace.Description) ?? text(source.description);
    const name = text(source.name);
    if (description) return description;
    if (name?.includes("·")) return name.split("·").slice(1).join("·").trim();
    return processTag(source) ?? source.name;
  }
  return elementLabel(source.semanticId);
}

/**
 * Rótulo «tag · nombre» para la etiqueta flotante, la leyenda y el árbol:
 * "P-150 · Bomba de inyección" en la raíz y "P-150 · Motor A" en una pieza.
 */
export function productLabel(source: LabelSource): string {
  const trace = source.psets.TrazIA_Traceability;
  if (!trace?.ProcessProject) return elementLabel(source.semanticId);
  const name = text(source.name);
  const parent = text(trace.ParentComponent);
  if (parent) {
    if (name?.includes("·")) return name;
    return `${parent} · ${shortLabel(source)}`;
  }
  const tag = processTag(source) ?? source.name;
  const description = shortLabel(source);
  return description && description !== tag ? `${tag} · ${description}` : tag;
}
