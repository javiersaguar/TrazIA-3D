import type { Target } from "./api";
import { groups } from "./form";

export type EditableElement = { id: string; label: string; semantic: string | null; targets: string[] };

/** Piezas del equipo actual, sin crear otra representación geométrica. */
export function editableElements(targets: Target[], kind: string): EditableElement[] {
  const result: EditableElement[] = groups(targets).map(group => ({
    ...group, semantic: group.id.startsWith("boquilla:") ? `nozzle:${group.id.slice(9)}`
      : group.id.startsWith("pieza:platforms:") ? `element:platform-${group.id.slice(16)}`
        : group.id.startsWith("pieza:ladders:") ? `element:ladder-${group.id.slice(14)}` : null,
    targets: targets.filter(t => t.group === group.id).map(t => t.target),
  }));
  const add = (id: string, label: string, semantic: string, keys: string[]) => {
    const available = keys.filter(key => targets.some(t => t.target === key));
    if (available.length) result.push({id, label, semantic, targets: available});
  };
  if (kind === "vertical_vessel") {
    add("shell", "Virola", "shell", ["diameter", "height", "total_height"]);
    add("head-top", "Fondo superior", "head-top", ["diameter", "head_depth"]);
    add("head-bottom", "Fondo inferior", "head-bottom", ["diameter", "head_depth"]);
    add("skirt", "Faldón", "skirt", ["diameter", "skirt_height", "skirt_thickness"]);
  } else if (kind === "horizontal_vessel") {
    add("shell", "Virola", "shell", ["horizontal.diameter", "horizontal.length"]);
    for (const [id, label] of [["head-top", "Fondo derecho"], ["head-bottom", "Fondo izquierdo"]])
      add(id!, label!, id!, ["horizontal.diameter", "horizontal.head_depth"]);
    for (let i = 0; i < 2; i++) add(`saddle-${i+1}`, `Silleta ${i+1}`, `element:saddle-${i+1}`,
      ["horizontal.support_height", "horizontal.saddle_width", "horizontal.saddle_span", `horizontal.saddle_positions.${i}`]);
  } else if (kind === "tank") {
    add("shell", "Cuerpo del tanque", "shell", ["tank.diameter", "tank.height"]);
    add("roof", "Techo", "element:roof", ["tank.diameter", "tank.roof_height"]);
  } else if (kind === "column") {
    const sections = [...new Set(targets.filter(t => t.target.startsWith("column.sections.")).map(t => t.target.split(".")[2]!))];
    sections.forEach((id, i) => add(`section-${id}`, `Tramo ${id}`, i ? `element:section-${id}` : "shell",
      targets.filter(t => t.target.startsWith(`column.sections.${id}.`)).map(t => t.target)));
  }
  return result;
}

