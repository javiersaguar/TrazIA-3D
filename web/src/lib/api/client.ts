import type { Revision } from "@/lib/types/revision";
import type { BenchExtractor, EquipmentRow, FieldUpdate, RevisionId } from "../mock/api";
import type { BenchReport } from "../mock/bench-types";
import type { StudyResponse } from "../mock/estudio-types";
import type { DiffReport } from "../mock/diff-types";
import { flattenRevision, type ReviewField } from "../mock/fields";
import { apiURL, rememberVersion, revisionVersion } from "./config";
import type { components } from "./schema";

type FieldInput = components["schemas"]["FieldInput"];
export type JobInput = components["schemas"]["JobInput"];
export type StageEvent = { id: number; job_id: string; stage: string; status: "ok" | "omitido" | "error"; file: string; detail: string; created_at: number };
export type JobStatus = { id: string; status: "queued" | "running" | "done" | "error" | "cancelled" | "timeout"; attempts: number; error: string | null; run: components["schemas"]["RunInfo"] | null; warnings: string[]; created_at: number; revision_id: string | null };

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); this.name = "ApiError"; }
}

async function checked(response: Response) {
  if (response.ok) return response;
  const body = await response.json().catch(() => null);
  throw new ApiError(response.status, typeof body?.detail === "string" ? body.detail : `La API respondió ${response.status}`);
}

async function get<T>(path: string): Promise<T> {
  return (await checked(await fetch(apiURL(path)))).json() as Promise<T>;
}

export async function apiRevision(rev: RevisionId): Promise<Revision> {
  const response = await checked(await fetch(apiURL(`/equipment/V-101/revisions/${rev}`)));
  const data = await response.json() as Revision;
  rememberVersion(rev, `${data.project_id}:${data.equipment.id}:${data.revision}`, response.headers.get("ETag"));
  return data;
}

export async function apiFields(rev: RevisionId): Promise<ReviewField[]> {
  return flattenRevision(await apiRevision(rev));
}

// Serializar las acciones de una revisión evita que dos pulsaciones rápidas usen el mismo ETag.
const writes = new Map<string, Promise<unknown>>();
export async function apiUpdate(update: FieldUpdate): Promise<ReviewField> {
  const body: FieldInput = {
    state: update.action === "reject" ? "abstained" : update.status,
    actor: update.actor ?? "Revisor local", seconds: update.seconds,
    review_session_id: update.reviewSessionId, action: update.action,
    expected: update.expected,
    explanation: update.explanation, source: update.source ? {
      ...update.source, bbox: update.source.bbox ? update.source.bbox.map(Number) as [number, number, number, number] : null,
    } : undefined,
  };
  if (update.correctedValue !== undefined) body.value = update.correctedValue;
  return writeField(update, "PATCH", `fields/${encodeURIComponent(update.path)}`, body);
}

export function apiUndo(update: FieldUpdate, auditId: number): Promise<ReviewField> {
  return writeField(update, "POST", `audit/${auditId}/undo`, {
    actor: update.actor ?? "Revisor local", seconds: update.seconds, review_session_id: update.reviewSessionId,
  });
}

async function writeField(update: FieldUpdate, method: "PATCH" | "POST", suffix: string, body: object): Promise<ReviewField> {
  const previous = writes.get(update.rev) ?? Promise.resolve();
  const action = previous.catch(() => undefined).then(async () => {
    if (!revisionVersion(update.rev)) await apiRevision(update.rev);
    const version = revisionVersion(update.rev);
    if (!version) throw new ApiError(428, "La API no ha devuelto la versión de la revisión");
    const raw = await fetch(apiURL(`/revisions/${encodeURIComponent(version.identity)}/${suffix}`), {
      method, headers: { "Content-Type": "application/json", "If-Match": version.etag, "Idempotency-Key": update.idempotencyKey },
      body: JSON.stringify(body),
    });
    if (raw.status === 412) await apiRevision(update.rev).catch(() => undefined);
    const pendingExport = raw.status === 503 ? await raw.clone().json().catch(() => null) : null;
    const response = pendingExport?.persisted && pendingExport?.revision
      ? new Response(JSON.stringify(pendingExport.revision), { status: 200, headers: raw.headers })
      : await checked(raw);
    const revision = await response.json() as Revision;
    rememberVersion(update.rev, version.identity, response.headers.get("ETag"));
    const field = flattenRevision(revision).find(f => f.path === update.path);
    if (!field) throw new ApiError(422, "La API no devolvió el campo modificado");
    const auditId = response.headers.get("X-Audit-Id");
    if (auditId) field.auditId = Number(auditId);
    if (pendingExport?.persisted) field.saveWarning = pendingExport.detail;
    return field;
  });
  writes.set(update.rev, action);
  try { return await action; } finally { if (writes.get(update.rev) === action) writes.delete(update.rev); }
}

export async function apiExportCorrections() {
  return checked(await fetch(apiURL("/correcciones/export"), { method: "POST" }));
}

export const apiChanges = () => get<DiffReport>("/diff?from=A&to=B");
export const apiStudy = () => get<StudyResponse>("/estudio");
export const apiBench = (extractor: BenchExtractor) => get<BenchReport>(`/bench?extractor=${extractor}`);
export async function apiEquipment(): Promise<EquipmentRow[]> {
  const rows = await get<EquipmentRow[]>("/equipment");
  const labels: Record<string, string> = { vertical_vessel: "Recipiente vertical", horizontal_vessel: "Recipiente horizontal", column: "Columna", tank: "Tanque", pump: "Bomba", compressor: "Compresor", generic: "Genérico" };
  return rows.map(row => ({ ...row, kind: labels[row.kind] ?? row.kind, ifcUrl: apiURL(row.ifcUrl) }));
}

export async function uploadDocument(file: File, documentId?: string, revision = "A"): Promise<{ id: string; filename: string; sha256: string }> {
  const form = new FormData(); form.append("file", file);
  if (documentId) form.append("document_id", documentId);
  form.append("revision", revision);
  return (await checked(await fetch(apiURL("/documents"), { method: "POST", body: form,
    headers: { "Idempotency-Key": crypto.randomUUID() } }))).json();
}

export async function startJob(body: JobInput): Promise<string> {
  const response = await checked(await fetch(apiURL("/equipment/V-101/jobs"), { method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify(body) }));
  return (await response.json() as { job_id: string }).job_id;
}
export const getJob = (identity: string) => get<JobStatus>(`/jobs/${encodeURIComponent(identity)}`);
export async function cancelJob(identity: string) {
  await checked(await fetch(apiURL(`/jobs/${encodeURIComponent(identity)}/cancel`), { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() } }));
}

export function subscribeJob(identity: string, onStage: (event: StageEvent) => void, onComplete: (status: string) => void, onError: () => void) {
  let closed = false;
  const stream = new EventSource(apiURL(`/jobs/${encodeURIComponent(identity)}/events`));
  stream.addEventListener("stage", message => {
    try { onStage(JSON.parse((message as MessageEvent).data) as StageEvent); } catch { onError(); }
  });
  stream.addEventListener("complete", message => {
    const data = JSON.parse((message as MessageEvent).data) as { status: string };
    closed = true; stream.close(); onComplete(data.status);
  });
  stream.onerror = () => { if (!closed) onError(); }; // EventSource reanuda con Last-Event-ID; no se sustituyen eventos por mocks.
  return () => { closed = true; stream.close(); };
}


export type CopilotAnswer = components["schemas"]["CopilotAnswer"];
export async function askCopilot(rev: RevisionId, question: string, path?: string, signal?: AbortSignal): Promise<CopilotAnswer> {
  const identity = revisionVersion(rev)?.identity ?? rev;
  const body: components["schemas"]["CopilotInput"] = { question, revision_id: identity,
    ...(path ? { path } : {}), ...(rev === "B" ? { previous_id: revisionVersion("A")?.identity ?? "A" } : {}) };
  return (await checked(await fetch(apiURL("/copiloto"), { method: "POST", signal,
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }))).json() as Promise<CopilotAnswer>;
}
