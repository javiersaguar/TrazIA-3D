/*
  Datos de ejemplo de las secciones en boceto (docs/PLAN_FRONTEND.md, 1.6).
  Todo lo que no es DEMO-PLANT / V-101 es inventado para enseñar la pantalla y se marca así en la
  interfaz. Cuando cada sección se conecte con el núcleo, estos datos desaparecen.
*/

import type { EquipmentKind } from "@/features/showcase3d";

export type SketchProject = {
  code: string;
  name: string;
  example: boolean;
  equipment: number;
  withData: number;
  reviewed: number;
  kinds: EquipmentKind[];
  status: "En revisión" | "Aprobado" | "Sin empezar";
  updated: string;
};

export const PROJECTS: SketchProject[] = [
  { code: "DEMO-PLANT", name: "Planta de demostración", example: false, equipment: 8, withData: 1, reviewed: 0, kinds: ["vertical"], status: "En revisión", updated: "30/10/2026" },
  { code: "EJ-HDT", name: "Unidad de hidrotratamiento", example: true, equipment: 42, withData: 42, reviewed: 31, kinds: ["vertical", "column", "exchanger"], status: "En revisión", updated: "28/10/2026" },
  { code: "EJ-GNL", name: "Terminal de GNL", example: true, equipment: 18, withData: 18, reviewed: 18, kinds: ["tank", "horizontal"], status: "Aprobado", updated: "21/10/2026" },
  { code: "EJ-DST", name: "Ampliación de destilación", example: true, equipment: 27, withData: 0, reviewed: 0, kinds: ["column", "exchanger"], status: "Sin empezar", updated: "17/10/2026" },
];

export type DocStage = "recibido" | "leído" | "revisado";

export type SketchDocument = {
  name: string;
  kind: "Plano GA" | "Hoja de datos" | "Lista de boquillas";
  tag: string;
  rev: string;
  pages: number;
  stage: DocStage;
  received: string;
  example: boolean;
};

export const DOCUMENTS: SketchDocument[] = [
  { name: "GAD_V-101_revA.pdf", kind: "Plano GA", tag: "V-101", rev: "A", pages: 1, stage: "revisado", received: "26/10/2026", example: false },
  { name: "GAD_V-101_revB.pdf", kind: "Plano GA", tag: "V-101", rev: "B", pages: 1, stage: "leído", received: "28/10/2026", example: false },
  { name: "DS_E-201_revA.pdf", kind: "Hoja de datos", tag: "E-201", rev: "A", pages: 2, stage: "leído", received: "29/10/2026", example: true },
  { name: "GAD_T-301_revC.pdf", kind: "Plano GA", tag: "T-301", rev: "C", pages: 3, stage: "recibido", received: "30/10/2026", example: true },
  { name: "NOZ_C-401_revA.pdf", kind: "Lista de boquillas", tag: "C-401", rev: "A", pages: 1, stage: "recibido", received: "30/10/2026", example: true },
];

export type SketchFamily = {
  kind: EquipmentKind | "pump";
  name: string;
  fields: number | null;
  parts: string[];
  status: "Disponible" | "En desarrollo" | "Planificada";
  phase: string;
};

export const FAMILIES: SketchFamily[] = [
  { kind: "vertical", name: "Recipiente vertical", fields: 22, parts: ["Virola", "Fondos 2:1", "Faldón", "Boquillas"], status: "Disponible", phase: "F1" },
  { kind: "horizontal", name: "Recipiente horizontal", fields: null, parts: ["Virola", "Fondos", "Silletas", "Boquillas"], status: "En desarrollo", phase: "F2" },
  { kind: "column", name: "Columna", fields: null, parts: ["Virola por tramos", "Platos", "Plataformas", "Boquillas"], status: "Planificada", phase: "F3" },
  { kind: "exchanger", name: "Intercambiador de carcasa y tubos", fields: null, parts: ["Carcasa", "Canal", "Haz de tubos", "Soportes"], status: "Planificada", phase: "—" },
  { kind: "tank", name: "Tanque atmosférico", fields: null, parts: ["Envolvente", "Techo", "Fondo", "Escalera"], status: "Planificada", phase: "—" },
  { kind: "pump", name: "Bomba", fields: null, parts: ["Carcasa", "Motor", "Bancada"], status: "Planificada", phase: "—" },
];

export type SketchJob = {
  id: string;
  documents: number;
  strategy: "A" | "B" | "C" | "D";
  progress: number;
  status: "En cola" | "Procesando" | "Hecho" | "Cancelado";
  started: string;
};

export const JOBS: SketchJob[] = [
  { id: "lote-0007", documents: 12, strategy: "D", progress: 0.58, status: "Procesando", started: "30/10/2026 16:42" },
  { id: "lote-0008", documents: 4, strategy: "B", progress: 0, status: "En cola", started: "—" },
  { id: "lote-0009", documents: 30, strategy: "D", progress: 0, status: "En cola", started: "—" },
  { id: "lote-0006", documents: 8, strategy: "B", progress: 1, status: "Hecho", started: "30/10/2026 12:10" },
  { id: "lote-0005", documents: 3, strategy: "A", progress: 0.33, status: "Cancelado", started: "29/10/2026 18:03" },
];

export type SketchExport = {
  date: string;
  kind: "IFC" | "BCF" | "CSV" | "Informe PDF";
  scope: string;
  hash: string;
  state: "Borrador" | "Aprobado";
};

export const EXPORTS: SketchExport[] = [
  { date: "30/10/2026 17:05", kind: "IFC", scope: "V-101 rev B", hash: "3f9a1c07e2b4", state: "Borrador" },
  { date: "30/10/2026 16:58", kind: "BCF", scope: "V-101 rev A → B", hash: "a81d55c0f9e3", state: "Borrador" },
  { date: "29/10/2026 11:20", kind: "CSV", scope: "V-101 rev A", hash: "c02e7b9d4a16", state: "Aprobado" },
];

export type AuditEvent = {
  at: string;
  who: string;
  kind: "edición" | "aprobación" | "invalidación" | "lectura";
  text: string;
  detail?: string;
};

export const AUDIT: AuditEvent[] = [
  { at: "30/10/2026 17:02", who: "Revisor 2", kind: "invalidación", text: "La aprobación de V-101 rev A deja de valer", detail: "Cambió la altura del faldón; la huella ya no coincide." },
  { at: "30/10/2026 16:55", who: "Revisor 2", kind: "edición", text: "Faldón: 1200 → 1350 mm", detail: "Corregido sobre la cota del alzado, página 1." },
  { at: "30/10/2026 12:31", who: "Revisor 1", kind: "aprobación", text: "V-101 rev A aprobada", detail: "Vinculada a la huella c02e7b9d4a16 de los datos." },
  { at: "30/10/2026 12:18", who: "Revisor 1", kind: "edición", text: "Diámetro de la virola aceptado: 2000 mm", detail: "Cita en el cajetín y en la cota del alzado." },
  { at: "30/10/2026 12:02", who: "Sistema", kind: "lectura", text: "Lectura de GAD_V-101_revA.pdf con la estrategia B", detail: "22 campos con valor, unidad, fuente y confianza." },
];

export const TEAM = [
  { name: "Javier Saguar Antona", role: "Líder técnico, integración y extracción" },
  { name: "Iria Lozano Carrasco", role: "Frontend, diseño y 3D" },
  { name: "Miguel Vera del Castillo", role: "Geometría, IFC y familias" },
  { name: "Alejandro Cuevas Cid", role: "Evaluación, cambios y negocio" },
];
