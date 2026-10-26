import type { Revision, Source } from "@/lib/types/revision";

/** Estado de revisión humana de un campo en la UI. */
export type FieldStatus = "candidate" | "accepted" | "corrected" | "assumed";

export type FieldGroup = "Identificación" | "Envolvente" | "Soporte" | "Boquillas" | "Datos de diseño";

/**
 * Ids semánticos compartidos entre plano, 3D y lista de campos.
 * Correspondencia con el IFC generado por el núcleo (atributo Name):
 *   "shell"       ↔ IfcTank "V-101"
 *   "head-top"    ↔ "V-101/top_head"
 *   "head-bottom" ↔ "V-101/bottom_head"
 *   "skirt"       ↔ "V-101/skirt"
 *   "nozzle:N1"   ↔ IfcPipeSegment "V-101/N1"
 */
export type ElementId = "shell" | "head-top" | "head-bottom" | "skirt" | `nozzle:${string}`;

export type ReviewField = {
  /** Ruta en el contrato, p. ej. "nozzles.N3.elevation". */
  path: string;
  label: string;
  group: FieldGroup;
  elementId: ElementId;
  value: number | string;
  unit: string;
  source: Source;
  confidence: number;
  /** Peso 0–1 del daño que haría un error en este campo (reglas del roadmap E.2). */
  impact: number;
  /** impacto × (1 − confianza): ordena la cola de revisión. */
  risk: number;
  status: FieldStatus;
  correctedValue?: number | string;
};

const DIMENSIONS = [
  { key: "diameter", label: "Diámetro de la virola", group: "Envolvente", elementId: "shell", impact: 1 },
  { key: "height", label: "Longitud entre tangentes", group: "Envolvente", elementId: "shell", impact: 0.9 },
  { key: "head_depth", label: "Altura de los fondos", group: "Envolvente", elementId: "head-top", impact: 0.6 },
  { key: "skirt_height", label: "Altura del faldón", group: "Soporte", elementId: "skirt", impact: 0.8 },
  { key: "skirt_thickness", label: "Espesor del faldón", group: "Soporte", elementId: "skirt", impact: 0.5 },
] as const;

const NOZZLE_FIELDS = [
  { key: "elevation", label: "elevación", impact: 1 },
  { key: "azimuth", label: "orientación", impact: 1 },
  { key: "diameter", label: "diámetro", impact: 0.7 },
  { key: "projection", label: "proyección", impact: 0.6 },
] as const;

const ATTRIBUTE_LABELS: Record<string, { label: string; impact: number }> = {
  design_pressure: { label: "Presión de diseño", impact: 0.5 },
  design_temperature: { label: "Temperatura de diseño", impact: 0.5 },
  material: { label: "Material", impact: 0.4 },
  operating_weight: { label: "Peso de operación", impact: 0.7 },
};

function field(
  path: string,
  label: string,
  group: FieldGroup,
  elementId: ElementId,
  impact: number,
  data: { value: number | string; unit?: string; source: Source; state?: string },
): ReviewField {
  const confidence = data.source.confidence;
  return {
    path,
    label,
    group,
    elementId,
    value: data.value,
    unit: data.unit ?? "1",
    source: data.source,
    confidence,
    impact,
    risk: impact * (1 - confidence),
    status: data.state === "corrected" || data.state === "assumed" ? data.state : data.state === "accepted" || data.source.reviewed ? "accepted" : "candidate",
  };
}

/** Aplana una revisión del contrato en la lista de campos revisables, ordenada por riesgo. */
export function flattenRevision(revision: Revision): ReviewField[] {
  const eq = revision.equipment;
  const out: ReviewField[] = [field("tag", "Tag del equipo", "Identificación", "shell", 0.4, eq.tag)];

  for (const d of DIMENSIONS) {
    const dimension = eq[d.key];
    if (dimension) out.push(field(d.key, d.label, d.group, d.elementId, d.impact, dimension));
  }

  for (const nozzle of eq.nozzles) {
    for (const f of NOZZLE_FIELDS) {
      out.push(
        field(
          `nozzles.${nozzle.id}.${f.key}`,
          `${nozzle.id} · ${f.label}`,
          "Boquillas",
          `nozzle:${nozzle.id}`,
          f.impact,
          nozzle[f.key],
        ),
      );
    }
  }

  for (const [key, attr] of Object.entries(eq.attributes ?? {})) {
    if (!attr) continue;
    const meta = ATTRIBUTE_LABELS[key] ?? { label: key, impact: 0.4 };
    out.push(field(`attributes.${key}`, meta.label, "Datos de diseño", "shell", meta.impact, attr));
  }

  return out.sort((a, b) => b.risk - a.risk || b.impact - a.impact || a.path.localeCompare(b.path));
}

export function riskLevel(f: Pick<ReviewField, "impact">): "alto" | "medio" | "bajo" {
  if (f.impact >= 0.9) return "alto";
  if (f.impact >= 0.6) return "medio";
  return "bajo";
}

/** Elemento 3D afectado por una ruta del contrato (también para los cambios). */
export function elementForPath(path: string): ElementId {
  if (path.startsWith("nozzles.")) return `nozzle:${path.split(".")[1] ?? ""}`;
  if (path.startsWith("skirt")) return "skirt";
  if (path === "head_depth") return "head-top";
  return "shell";
}
