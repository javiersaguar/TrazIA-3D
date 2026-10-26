import type { PropertySets } from "@/workers/ifc-protocol";

export function semanticId(name: string, ifcType: string, psets: PropertySets = {}): string {
  const identity = psets.TrazIA_Identity ?? psets.GA2MODEL_Identity;
  const component = String(identity?.ComponentId ?? identity?.NozzleId ?? name.split("/").at(-1) ?? "");
  if (component === "shell" || ifcType.toUpperCase() === "IFCTANK") return "shell";
  if (component === "top_head") return "head-top";
  if (component === "bottom_head") return "head-bottom";
  if (component === "skirt") return "skirt";
  if (ifcType.toUpperCase() === "IFCPIPESEGMENT" || /^N\d+$/i.test(component)) {
    return `nozzle:${component}`;
  }
  return `element:${component}`;
}

export function elementForField(path: string): string {
  if (path.startsWith("nozzles.")) return `nozzle:${path.split(".")[1]}`;
  if (path.startsWith("skirt")) return "skirt";
  if (path === "head_depth") return "head-top";
  return "shell";
}

export function elementLabel(id: string): string {
  const labels: Record<string, string> = {
    shell: "Virola", "head-top": "Fondo superior", "head-bottom": "Fondo inferior", skirt: "Faldón",
  };
  return labels[id] ?? id.replace("nozzle:", "Boquilla ").replace("element:", "Elemento ");
}
