import { create } from "zustand";
import { persist } from "zustand/middleware";

import { DOCUMENTS, FAMILIES as FAMILY_INFO, PROJECTS as SAMPLE_PROJECTS, type DocStage, type SketchFamily } from "@/lib/mock/bocetos";

/*
  Catálogo de Documentos: familias, proyectos y diseños, guardado en este navegador.
  Los ejemplos (salvo DEMO-PLANT / V-101) son inventados y se marcan como tales en la interfaz.
*/

export type Family = { id: string; name: string; custom?: boolean };
export type ProjectStatus = "En revisión" | "Aprobado" | "Sin empezar";
export type ProjectStats = { equipment: number; withData: number; reviewed: number; status: ProjectStatus; updated: string };
export type Project = { id: string; name: string; code?: string; example?: boolean; stats?: ProjectStats };
export type DocKind = "Plano GA" | "Hoja de datos" | "Lista de boquillas" | "Otro";
export type Design = {
  id: string;
  name: string;
  family: string;
  project: string;
  filename?: string;
  size?: number;
  /** Documento de V-101 que abre la demo del modelo. */
  demo?: boolean;
  /** Documento inventado para enseñar la pantalla. */
  example?: boolean;
  kind?: DocKind;
  tag?: string;
  rev?: string;
  pages?: number;
  stage?: DocStage;
  received?: string;
};

export const FAMILIES: Family[] = [
  { id: "vertical", name: "Recipientes verticales" },
  { id: "horizontal", name: "Recipientes horizontales" },
  { id: "column", name: "Columnas" },
  { id: "exchanger", name: "Intercambiadores" },
  { id: "tank", name: "Tanques" },
  { id: "pump", name: "Bombas" },
  { id: "compressor", name: "Compresores" },
  { id: "generic", name: "Envolventes de reserva" },
];

/** Ficha de cada familia: piezas, estado y campos de revisión. */
export type FamilyInfo = Omit<SketchFamily, "kind" | "name">;
const EXTRA_INFO: Record<string, FamilyInfo> = {
  compressor: { fields: null, parts: ["Carcasa", "Accionamiento", "Bancada"], status: "Planificada", phase: "—" },
  generic: { fields: null, parts: ["Envolvente LOD 1", "Boquillas"], status: "Disponible", phase: "F1" },
};
export function familyInfo(id: string): FamilyInfo | undefined {
  const known = FAMILY_INFO.find((f) => f.kind === id);
  if (known) return { fields: known.fields, parts: known.parts, status: known.status, phase: known.phase };
  return EXTRA_INFO[id];
}

const PROJECT_IDS: Record<string, string> = { "DEMO-PLANT": "demo", "EJ-HDT": "ej-hdt", "EJ-GNL": "ej-gnl", "EJ-DST": "ej-dst" };
const SEED_PROJECTS: Project[] = SAMPLE_PROJECTS.map((p) => ({
  id: PROJECT_IDS[p.code] ?? p.code.toLowerCase(),
  name: p.name,
  code: p.code,
  example: p.example,
  stats: { equipment: p.equipment, withData: p.withData, reviewed: p.reviewed, status: p.status, updated: p.updated },
}));
/** Familias de los proyectos de ejemplo, aunque aún no tengan documentos en el catálogo. */
export const PROJECT_KINDS: Record<string, string[]> = Object.fromEntries(
  SAMPLE_PROJECTS.map((p) => [PROJECT_IDS[p.code] ?? p.code.toLowerCase(), p.kinds]),
);

const TAG_FAMILY: Record<string, [family: string, project: string]> = {
  "V-101": ["vertical", "demo"],
  "E-201": ["exchanger", "ej-hdt"],
  "T-301": ["tank", "ej-gnl"],
  "C-401": ["column", "ej-dst"],
};
const SEED_DESIGNS: Design[] = DOCUMENTS.map((d) => {
  const [family, project] = TAG_FAMILY[d.tag] ?? ["generic", "demo"];
  return {
    id: `seed-${d.name}`,
    name: d.name,
    filename: d.name,
    family,
    project,
    demo: !d.example,
    example: d.example,
    kind: d.kind,
    tag: d.tag,
    rev: d.rev,
    pages: d.pages,
    stage: d.stage,
    received: d.received,
  };
});

/** Equipo leído del nombre del archivo (GAD_V-101_revB.pdf → V-101), si lo trae. */
export function tagFromFilename(filename: string): string | undefined {
  return filename.match(/(?:^|[_\s-])([A-Z]{1,3}-?\d{2,4}[A-Z]?)(?=[_\s.-]|$)/)?.[1];
}
export function kindFromFilename(filename: string): DocKind {
  const f = filename.toUpperCase();
  if (f.startsWith("GAD") || f.includes("_GA")) return "Plano GA";
  if (f.startsWith("DS") || f.endsWith(".XLSX") || f.endsWith(".XLS")) return "Hoja de datos";
  if (f.startsWith("NOZ")) return "Lista de boquillas";
  return f.endsWith(".PDF") ? "Plano GA" : "Otro";
}

type Catalogue = {
  families: Family[];
  projects: Project[];
  designs: Design[];
  addFamily(name: string): string;
  addProject(name: string): string;
  addDesign(design: Design): void;
  assign(id: string, family: string, project: string): void;
};

type Persisted = Pick<Catalogue, "families" | "projects" | "designs">;

export const useCatalogue = create<Catalogue>()(
  persist(
    (set) => ({
      families: FAMILIES,
      projects: SEED_PROJECTS,
      designs: SEED_DESIGNS,
      addFamily: (name) => {
        const id = crypto.randomUUID();
        set((s) => ({ families: [...s.families, { id, name: name.trim(), custom: true }] }));
        return id;
      },
      addProject: (name) => {
        const id = crypto.randomUUID();
        set((s) => ({ projects: [...s.projects, { id, name: name.trim() }] }));
        return id;
      },
      addDesign: (design) => set((s) => ({ designs: [design, ...s.designs] })),
      assign: (id, family, project) =>
        set((s) => ({ designs: s.designs.map((d) => (d.id === id ? { ...d, family, project } : d)) })),
    }),
    {
      name: "trazia.catalogue.v1",
      version: 2,
      // v1 solo traía DEMO-PLANT y un diseño de V-101: se añaden los ejemplos sin tocar lo del usuario
      migrate: (stored, version) => {
        const s = stored as Persisted;
        if (version >= 2) return s;
        const designs = s.designs.filter((d) => d.id !== "demo-v101");
        const projects = s.projects.map((p) => SEED_PROJECTS.find((q) => q.id === p.id) ?? p);
        return {
          families: s.families,
          projects: [...projects, ...SEED_PROJECTS.filter((p) => !projects.some((q) => q.id === p.id))],
          designs: [...designs, ...SEED_DESIGNS.filter((d) => !designs.some((q) => q.id === d.id))],
        };
      },
    },
  ),
);

async function database() {
  return new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open("trazia.documents.v1", 1);
    request.onupgradeneeded = () => request.result.createObjectStore("files");
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
export async function saveDocument(id: string, file: File) {
  const db = await database();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction("files", "readwrite");
      tx.objectStore("files").put(file, id);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
export async function loadDocument(id: string): Promise<Blob | undefined> {
  const db = await database();
  try {
    return await new Promise((resolve, reject) => {
      const request = db.transaction("files", "readonly").objectStore("files").get(id);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}
