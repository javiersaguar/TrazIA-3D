/*
  Capa de mocks que imita la futura API (docs/ROADMAP.md, sección H).
  Cada función es async y lee los archivos sintéticos de public/demo/.
  Para conectar la API real basta con sustituir el cuerpo por fetch al endpoint indicado.
*/
import { apiEnabled, revisionResource } from "../api/config";
import { apiUpdate, apiUndo } from "../api/client";
import type { Revision, Source } from "@/lib/types/revision";
import type { BenchReport } from "./bench-types";
import type { DiffReport } from "./diff-types";
import { flattenRevision, type FieldStatus, type ReviewField } from "./fields";
import type { StudyResponse } from "./estudio-types";

export type RevisionId = "A" | "B";

const LATENCY_MS = 260;
const wait = (ms = LATENCY_MS) => new Promise((r) => setTimeout(r, ms));

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`No se pudo leer ${url} (${res.status})`);
  return (await res.json()) as T;
}

export const DEMO = {
  project: "DEMO-PLANT",
  tag: "V-101",
  revisions: {
    A: {
      json: "/demo/json/vessel_rev_a.json",
      get ifc() { return revisionResource("A", "ifc"); },
      get pdf() { return revisionResource("A", "pdf"); },
    },
    B: {
      json: "/demo/json/vessel_rev_b.json",
      get ifc() { return revisionResource("B", "ifc"); },
      get pdf() { return revisionResource("B", "pdf"); },
    },
  },
  changes: "/demo/json/changes.json",
} as const;

/** GET /equipment/{tag}/revisions/{rev} */
export async function getRevision(rev: RevisionId): Promise<Revision> {
  const [data] = await Promise.all([getJson<Revision>(DEMO.revisions[rev].json), wait()]);
  return data;
}

/* Estado de revisión en memoria: hace de "servidor" mientras no exista la API. */
const reviewStore = new Map<string, ReviewField>();
const idempotency = new Map<string, ReviewField>();
const key = (rev: RevisionId, path: string) => `${rev}:${path}`;

/** Campos revisables con su estado actual. */
export async function getReviewFields(rev: RevisionId): Promise<ReviewField[]> {
  const revision = await getRevision(rev);
  return flattenRevision(revision).map((f) => {
    const stored = reviewStore.get(key(rev, f.path));
    return stored ? { ...f, ...stored } : f;
  });
}

export type FieldOptions = {
  source?: Source;
  explanation?: string;
  actor?: string;
  seconds?: number;
  reviewSessionId?: string;
  action?: "accept" | "correct" | "assume" | "reject";
};
export type FieldUpdate = FieldOptions & {
  expected?: Record<string, unknown>;
  rev: RevisionId;
  path: string;
  status: FieldStatus;
  correctedValue?: number | string;
  /** Cabecera Idempotency-Key: repetir la misma petición devuelve el mismo resultado. */
  idempotencyKey: string;
};

/** PATCH /revisions/{id}/fields/{path} */
export async function updateField(update: FieldUpdate, current: ReviewField): Promise<ReviewField> {
  if (apiEnabled) return apiUpdate(update);
  const seen = idempotency.get(update.idempotencyKey);
  if (seen) return seen;
  await wait(220);
  const corrected = update.status === "corrected";
  const source = update.source ?? (corrected ? {
    ...current.source, channel: "humano" as const, grounded: null, strategy: null, model: null, prompt_sha256: null,
  } : current.source);
  const result: ReviewField = {
    ...current, status: update.status, correctedValue: update.correctedValue,
    interval: corrected ? null : current.interval,
    source: { ...source, reviewed: update.status === "accepted" || corrected },
    calibrated: source.channel !== "humano" && source.confidence_raw != null && source.confidence_raw !== source.confidence,
    explanation: update.action === "reject" ? `Rechazado por el revisor. ${update.explanation ?? "Hace falta una lectura nueva."}` : update.explanation ?? current.explanation,
    abstained: update.action === "reject",
    conflict: false,
    risk: current.impact * (1 - source.confidence) + (update.action === "reject" ? 1 : 0),
  };
  reviewStore.set(key(update.rev, update.path), result);
  idempotency.set(update.idempotencyKey, result);
  return result;
}

export async function undoField(update: FieldUpdate, before: ReviewField, auditId?: number): Promise<ReviewField> {
  if (apiEnabled) {
    if (auditId === undefined) throw new Error("Esta acción no tiene auditoría confirmada para deshacer");
    return apiUndo(update, auditId);
  }
  const seen = idempotency.get(update.idempotencyKey);
  if (seen) return seen;
  await wait(100);
  reviewStore.set(key(update.rev, update.path), before);
  idempotency.set(update.idempotencyKey, before);
  return before;
}

/** GET /diff?from=A&to=B */
export async function getChanges(): Promise<DiffReport> {
  const [data] = await Promise.all([getJson<DiffReport>(DEMO.changes), wait()]);
  return data;
}

export type BenchExtractor = "etiquetas" | "combinado";

/** GET /bench?extractor=… — informe del bench sobre el conjunto sintético (bench/report.py). */
export async function getBench(extractor: BenchExtractor): Promise<BenchReport> {
  const [data] = await Promise.all([getJson<BenchReport>(`/demo/json/bench-${extractor}.json`), wait(200)]);
  return data;
}

/** GET /estudio — sin backend se sirve el último estudio publicado por Lectura (sintético). */
export async function getStudy(): Promise<StudyResponse> {
  const [data] = await Promise.all([getJson<StudyResponse>("/demo/json/estudio.json"), wait(200)]);
  return data;
}

export type EquipmentRow = {
  tag: string;
  kind: string;
  area: string;
  revisions: RevisionId[];
  status: "draft" | "review" | "approved" | "changed";
  ifcUrl: string;
  /** true = equipo de relleno para la escena de planta; no tiene datos detrás. */
  illustrative: boolean;
};

/** GET /equipment — solo V-101 tiene datos; el resto rellena la escena de planta y se rotula así. */
export async function getEquipment(): Promise<EquipmentRow[]> {
  await wait(180);
  return [
    { tag: "V-101", kind: "Recipiente vertical", area: "Unidad 100", revisions: ["A", "B"], status: "changed", ifcUrl: DEMO.revisions.B.ifc, illustrative: false },
    { tag: "V-102", kind: "Recipiente vertical", area: "Unidad 100", revisions: [], status: "draft", ifcUrl: DEMO.revisions.A.ifc, illustrative: true },
    { tag: "V-103", kind: "Recipiente vertical", area: "Unidad 100", revisions: [], status: "review", ifcUrl: DEMO.revisions.A.ifc, illustrative: true },
    { tag: "V-201", kind: "Recipiente vertical", area: "Unidad 200", revisions: [], status: "approved", ifcUrl: DEMO.revisions.A.ifc, illustrative: true },
    { tag: "V-202", kind: "Recipiente vertical", area: "Unidad 200", revisions: [], status: "draft", ifcUrl: DEMO.revisions.A.ifc, illustrative: true },
    { tag: "V-301", kind: "Recipiente vertical", area: "Unidad 300", revisions: [], status: "approved", ifcUrl: DEMO.revisions.A.ifc, illustrative: true },
  ];
}
