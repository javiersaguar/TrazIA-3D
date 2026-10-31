import type { PropertySets } from "@/workers/ifc-protocol";

export function semanticId(
  name: string,
  ifcType: string,
  psets: PropertySets = {},
): string {
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
