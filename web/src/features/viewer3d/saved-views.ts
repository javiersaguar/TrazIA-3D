import type { CameraPose } from "./camera-link";

export type SavedView = { id: string; name: string; pose: CameraPose };
export const viewsKey = (url: string) => `trazia.ifc.views.v1:${url}`;
export function validPose(value: unknown): value is CameraPose {
  if (!value || typeof value !== "object") return false;
  const pose = value as CameraPose;
  const vector = (v: unknown): v is [number, number, number] =>
    Array.isArray(v) && v.length === 3 && v.every(n => typeof n === "number" && Number.isFinite(n));
  return vector(pose.eye) && vector(pose.target) && Number.isFinite(pose.zoom)
    && pose.zoom >= 5 && pose.zoom <= 650
    && pose.eye.some((v, i) => Math.abs(v - pose.target[i]!) > 1e-6);
}
export function readViews(raw: string | null): SavedView[] {
  try {
    const values: unknown = JSON.parse(raw ?? "[]");
    if (!Array.isArray(values)) return [];
    return values.filter((value): value is SavedView => !!value && typeof value.id === "string"
      && typeof value.name === "string" && value.name.length > 0 && value.name.length <= 40
      && validPose(value.pose)).slice(0, 8);
  } catch { return []; }
}
