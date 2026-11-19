import type { ProcessEnvironmentId } from "@/features/viewer3d/types";
import index from "./catalog.json";

type Documents = { plan: string; workbook: string };
export type Parameter = "length" | "width" | "height" | "dn" | "rack_z";
export type EditFields = Partial<Record<Parameter, { min: number; max: number; step: number }>>;
export type ProcessProject = {
  id: string;
  code: string;
  name: string;
  setting: string;
  description: string;
  preset: ProcessEnvironmentId;
  equipment: { tag: string; name: string; family: string; service: string; editFields: EditFields }[];
  lines: { tag: string; start: string; end: string; fluid: string; editFields: EditFields }[];
  changes: { tag: string; label: string; before: number; after: number; unit: string }[];
  documents: Record<"A" | "B", Documents & { archive: string; equipment: Record<string, Documents | undefined> }>;
  states: Record<string, { file: string; bytes: number; triangles: number; transport: string; transportBytes: number }>;
};

export const processProjects: ProcessProject[] = index.map(project => {
  const { preset } = project;
  if (preset !== "ocean" && preset !== "coast" && preset !== "desert" && preset !== "industrial") {
    throw new Error(`Entorno desconocido en el catálogo: ${preset}`);
  }
  return { ...project, preset };
});
export const processAsset = (project: ProcessProject, filename: string) => `/demo/proceso/${project.id}/${filename}`;
