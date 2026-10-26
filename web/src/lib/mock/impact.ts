/*
  Agrupación de cambios por elemento e impacto por disciplina.
  Reglas explicables del roadmap (F.4), pendientes de validar con ingeniería.
  No sustituyen al texto de impacto que emite el núcleo: lo complementan.
*/
import type { FieldChange } from "./diff-types";
import { elementForPath, type ElementId } from "./fields";

export type Discipline = "MEC" | "EST" | "CIV" | "PIP" | "ELE" | "I&C";

export const DISCIPLINES: Record<Discipline, string> = {
  MEC: "Mecánica",
  EST: "Estructuras",
  CIV: "Civil",
  PIP: "Piping",
  ELE: "Electricidad",
  "I&C": "Instrumentación",
};

export type Severity = "alta" | "media" | "baja";

export type ChangeGroup = {
  id: string;
  title: string;
  elementId: ElementId;
  kind: "modificado" | "nuevo" | "eliminado";
  /** Cambio principal en números, si es un campo numérico único. */
  delta?: { value: number; unit: string };
  fields: FieldChange[];
  disciplines: { code: Discipline; reason: string }[];
  severity: Severity;
  affectsGeometry: boolean;
  coreImpact: string;
};

const FIELD_NAMES: Record<string, string> = {
  height: "Longitud entre tangentes",
  diameter: "Diámetro de la virola",
  head_depth: "Altura de los fondos",
  skirt_height: "Altura del faldón",
  skirt_thickness: "Espesor del faldón",
  elevation: "elevación",
  azimuth: "orientación",
  projection: "proyección",
  "attributes.operating_weight": "Peso de operación",
  "attributes.design_pressure": "Presión de diseño",
  "attributes.design_temperature": "Temperatura de diseño",
  "attributes.material": "Material",
};

function disciplinesFor(path: string, kind: ChangeGroup["kind"]): ChangeGroup["disciplines"] {
  if (path.startsWith("nozzles.")) {
    if (kind === "nuevo") {
      return [
        { code: "PIP", reason: "Nueva conexión que hay que trazar" },
        { code: "I&C", reason: "Comprobar si es una toma de instrumento" },
      ];
    }
    return [{ code: "PIP", reason: "La tubería conectada cambia de punto" }];
  }
  if (path === "height") {
    return [
      { code: "PIP", reason: "Se desplazan las boquillas superiores" },
      { code: "EST", reason: "Plataformas y escaleras referidas a la virola" },
      { code: "CIV", reason: "Cambian cargas sobre la cimentación" },
    ];
  }
  if (path.startsWith("skirt")) {
    return [
      { code: "CIV", reason: "Cimentación y pernos de anclaje" },
      { code: "EST", reason: "Accesos referidos a la cota del faldón" },
    ];
  }
  if (path === "attributes.operating_weight") {
    return [
      { code: "CIV", reason: "Carga de operación sobre la cimentación" },
      { code: "EST", reason: "Comprobación de soportes" },
    ];
  }
  if (path.startsWith("attributes.")) {
    return [{ code: "MEC", reason: "Dato de diseño mecánico" }];
  }
  return [{ code: "MEC", reason: "Revisión general del equipo" }];
}

function severityFor(path: string, affectsGeometry: boolean): Severity {
  if (path.startsWith("nozzles.") || path === "height" || path === "diameter") return "alta";
  if (affectsGeometry || path === "attributes.operating_weight") return "media";
  return "baja";
}

/** Agrupa los cambios de campos en cambios entendibles por elemento. */
export function groupChanges(changes: FieldChange[]): ChangeGroup[] {
  const groups = new Map<string, ChangeGroup>();

  for (const change of changes) {
    const isNozzle = change.path.startsWith("nozzles.");
    const nozzleId = isNozzle ? change.path.split(".")[1] : undefined;
    const kind: ChangeGroup["kind"] =
      change.operation === "added" ? "nuevo" : change.operation === "removed" ? "eliminado" : "modificado";
    // Altas y bajas de boquillas se agrupan en una sola tarjeta por boquilla.
    const key = isNozzle && kind !== "modificado" ? `nozzle:${nozzleId}:${kind}` : change.path;

    const existing = groups.get(key);
    if (existing) {
      existing.fields.push(change);
      existing.affectsGeometry ||= change.affects_geometry;
      continue;
    }

    const leaf = change.path.split(".").at(-1) ?? change.path;
    const title = isNozzle
      ? kind === "modificado"
        ? `${nozzleId} · ${FIELD_NAMES[leaf] ?? leaf}`
        : `${nozzleId} · boquilla ${kind === "nuevo" ? "nueva" : "eliminada"}`
      : (FIELD_NAMES[change.path] ?? change.path);

    const before = change.before?.value;
    const after = change.after?.value;
    const delta =
      kind === "modificado" && typeof before === "number" && typeof after === "number"
        ? { value: after - before, unit: change.after?.unit ?? "" }
        : undefined;

    groups.set(key, {
      id: key,
      title,
      elementId: elementForPath(change.path),
      kind,
      delta,
      fields: [change],
      disciplines: disciplinesFor(change.path, kind),
      severity: severityFor(change.path, change.affects_geometry),
      affectsGeometry: change.affects_geometry,
      coreImpact: change.impact,
    });
  }

  const order: Record<Severity, number> = { alta: 0, media: 1, baja: 2 };
  return [...groups.values()].sort((a, b) => order[a.severity] - order[b.severity]);
}
