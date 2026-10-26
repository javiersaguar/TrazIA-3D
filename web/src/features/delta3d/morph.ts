import type { Bounds, IfcProduct, Vec3 } from "@/workers/ifc-protocol";
import { elementForField, elementLabel } from "../viewer3d/semantic";

export type Pair<T> = { globalId: string; before: T | null; after: T | null };
export const clampProgress = (value: number) => Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export function pairByGlobalId<T extends { globalId: string }>(before: T[], after: T[]): Pair<T>[] {
  const index = (products: T[]) => {
    const map = new Map<string, T>();
    for (const product of products) {
      if (!product.globalId || map.has(product.globalId)) throw new Error("GlobalId vacío o duplicado: no se puede emparejar de forma inequívoca");
      map.set(product.globalId, product);
    }
    return map;
  };
  const a = index(before), b = index(after);
  return [...new Set([...a.keys(), ...b.keys()])].map(globalId => ({ globalId, before: a.get(globalId) ?? null, after: b.get(globalId) ?? null }));
}

export function interpolateBounds(before: Bounds, after: Bounds, progress: number): { position: Vec3; scale: Vec3 } {
  const t = clampProgress(progress);
  const position = before.min.map((v, i) => lerp((v + before.max[i]!) / 2, (after.min[i]! + after.max[i]!) / 2, t)) as Vec3;
  const scale = before.min.map((v, i) => {
    const oldSize = before.max[i]! - v, newSize = after.max[i]! - after.min[i]!;
    return oldSize > 1e-8 ? lerp(1, newSize / oldSize, t) : 1;
  }) as Vec3;
  return { position, scale };
}

export function morphState(pair: Pair<IfcProduct>, progress: number) {
  const t = clampProgress(progress);
  if (!pair.before && pair.after) return { position: pair.after.center, scale: [1, 1, 1] as Vec3,
    sourceOpacity: 0, targetOpacity: t, exactTarget: t === 1 };
  if (pair.before && !pair.after) return { position: pair.before.center, scale: [1, 1, 1] as Vec3,
    sourceOpacity: 1 - t, targetOpacity: 0, exactTarget: false };
  if (!pair.before || !pair.after) throw new Error("Pareja vacía");
  const transform = interpolateBounds(pair.before.bounds, pair.after.bounds, t);
  const blend = Math.min(1, Math.max(0, (t - .98) / .02));
  return { ...transform, sourceOpacity: 1 - blend, targetOpacity: blend, exactTarget: t === 1 };
}

export type Change = { path: string; operation: string; before: { value: number | string; unit: string } | null;
  after: { value: number | string; unit: string } | null; affects_geometry: boolean; impact: string };
export type ChangeStep = { id: string; elementId: string; label: string; narration: string; geometry: boolean };

function isRecord(value: unknown): value is Record<string, unknown> { return value !== null && typeof value === "object"; }

export function changeSteps(input: unknown): ChangeStep[] {
  const list = isRecord(input) && Array.isArray(input.changes) ? input.changes : Array.isArray(input) ? input : [];
  const byElement = new Map<string, Change[]>();
  for (const item of list) {
    if (!isRecord(item) || typeof item.path !== "string" || typeof item.operation !== "string") continue;
    const validValue = (v: unknown) => v === null || (isRecord(v) && ["number", "string"].includes(typeof v.value) && typeof v.unit === "string");
    if (!validValue(item.before) || !validValue(item.after)) continue;
    const change = item as unknown as Change;
    const id = elementForField(change.path);
    const group = byElement.get(id) ?? [];
    group.push(change); byElement.set(id, group);
  }
  const labels: Record<string, string> = { height: "Longitud de virola", skirt_height: "Altura del faldón",
    "attributes.operating_weight": "Peso de operación", head_depth: "Profundidad de fondos", diameter: "Diámetro" };
  return [...byElement].map(([elementId, changes]) => {
    const added = changes.every(c => c.operation === "added"), removed = changes.every(c => c.operation === "removed");
    const deltas = changes.map(c => {
      if (typeof c.before?.value === "number" && typeof c.after?.value === "number" && c.before.unit === c.after.unit) {
        const difference = c.after.value - c.before.value;
        return `${difference > 0 ? "+" : ""}${difference.toLocaleString("es-ES")} ${c.after.unit}`;
      }
      return c.operation === "added" ? "nuevo" : c.operation === "removed" ? "retirado" : "modificado";
    });
    return { id: elementId, elementId,
      label: added ? "Nueva boquilla" : removed ? "Retirado" : [...new Set(deltas)].join(" · "),
      narration: added ? `${elementLabel(elementId)} se incorpora a la revisión B.` : removed ? `${elementLabel(elementId)} se retira en B.` :
        changes.map((c, i) => `${labels[c.path] ?? elementLabel(elementId)}: ${deltas[i]}.`).join(" "),
      geometry: changes.some(c => c.affects_geometry),
    };
  });
}
