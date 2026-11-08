import type { ElementState } from "@/features/viewer3d/product-mesh";
import type { Datum, Issue, OperationInput, Preview, Target } from "./api";

export type Draft = { value: string; unit: string; datum?: Datum };
export type Drafts = Record<string, Draft>;

/** Unidades que se ofrecen por magnitud; el servidor normaliza y rechaza las ambiguas. */
export const UNITS: Record<string, string[]> = {
  length: ["mm", "m", "cm", "in", "ft"],
  angle: ["deg"],
  pressure: ["bar", "barg", "kPa", "MPa", "psi"],
  temperature: ["C", "F"],
  mass: ["kg", "t", "lb"],
};

export function unitsFor(target: Target): string[] {
  if (target.text) return [];
  if (!target.magnitude) return [target.unit];
  if (target.unit === "bara") return ["bara", "psia"];
  return UNITS[target.magnitude] ?? [target.unit];
}

/** Grupo de la selección 3D: "nozzle:N3" → boquilla N3; el resto, el equipo. */
export function groupForSelection(selectedId: string | null | undefined): string {
  const nozzle = selectedId?.match(/^(?:detail:)?nozzle:([^/]+)/);
  if (nozzle) return `boquilla:${nozzle[1]}`;
  const piece = selectedId?.match(/^element:(platform|ladder)-(.+)$/);
  return piece ? `pieza:${piece[1] === "platform" ? "platforms" : "ladders"}:${piece[2]}` : "equipo";
}

export function groups(targets: Target[]): { id: string; label: string }[] {
  const seen = new Map<string, string>();
  for (const target of targets) {
    if (seen.has(target.group)) continue;
    seen.set(target.group, target.group === "equipo" ? "Equipo"
      : target.group === "atributos" ? "Atributos técnicos"
        : target.group.startsWith("pieza:") ? `Pieza ${target.group.slice(6)}` : `Boquilla ${target.group.slice("boquilla:".length)}`);
  }
  return [...seen].map(([id, label]) => ({ id, label }));
}

/** Operaciones del lote a partir de los borradores con texto; el valor viaja como texto. */
export function toOperations(drafts: Drafts, targets: Target[]): OperationInput[] {
  const known = new Map(targets.map((t) => [t.target, t]));
  return Object.entries(drafts)
    .filter(([key, draft]) => known.has(key) && draft.value.trim() !== "")
    .map(([key, draft]) => {
      const target = known.get(key)!;
      const operation: OperationInput = { target: key, value: draft.value.trim() };
      if (!target.text && draft.unit) operation.unit = draft.unit;
      if (draft.datum && target.datums.length > 1) operation.datum = draft.datum;
      return operation;
    });
}

/** Firma estable de lo escrito: si cambia, la previsualización anterior deja de valer. */
export function draftSignature(operations: OperationInput[], reason: string): string {
  return JSON.stringify([operations.map((o) => [o.target, o.value, o.unit ?? "", o.datum ?? ""]), reason.trim()]);
}

export function issuesFor(target: string, path: string, issues: Issue[], operationIds: string[]): Issue[] {
  return issues.filter((issue) => issue.path === path || issue.path === target
    || (issue.operation_id !== null && operationIds.includes(issue.operation_id)));
}

/** Estados del visor: conflicto en rojo, pieza regenerada en el color de revisión. */
export function elementStates(preview: Preview | null, issues: Issue[]): Record<string, ElementState> {
  const states: Record<string, ElementState> = {};
  for (const element of preview?.elements ?? []) {
    if (element.geometry_changed || element.operations.length) states[element.semantic_id] = "changed";
    if (element.conflict) states[element.semantic_id] = "conflict";
  }
  for (const issue of issues) {
    if (issue.code === "nozzle_conflict" && issue.nozzle_id) states[`nozzle:${issue.nozzle_id}`] = "conflict";
  }
  return states;
}

const OPTION_PHRASE: Record<string, string> = {
  total_height: "altura total", height: "longitud entre tangentes",
  elevation: "elevación", azimuth: "azimut", diameter: "diámetro", projection: "proyección",
};

/** Texto que resuelve una aclaración sin que el intérprete tenga que suponer nada. */
export function clarifiedText(text: string, option: string): string {
  const key = option.split(".").at(-1) ?? option;
  return `${text.trim()} (${OPTION_PHRASE[key] ?? option})`;
}

/** Borradores del formulario a partir de las operaciones que propone el chat. */
export function draftsFromOperations(operations: OperationInput[], targets: Target[]): Drafts {
  const known = new Map(targets.map((t) => [t.target, t]));
  const drafts: Drafts = {};
  for (const operation of operations) {
    const target = known.get(operation.target);
    if (!target) continue;
    drafts[operation.target] = {
      value: String(operation.value), unit: operation.unit ?? target.unit,
      datum: operation.datum ?? target.datums[0],
    };
  }
  return drafts;
}
