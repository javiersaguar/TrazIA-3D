/*
  Cliente de propuestas de cambio de diseño (workstream K). Contrato en docs/EDICION_ASISTIDA.md.
  Una propuesta nunca modifica la revisión base; confirmar crea una revisión DRAFT nueva.
*/
import { ApiError } from "@/lib/api/client";
import { apiURL } from "@/lib/api/config";

export type Datum = "suelo" | "tangente_inferior" | "interno" | "norte";
export type ProposalStatus =
  | "draft" | "needs_clarification" | "invalid" | "ready" | "previewed"
  | "applied" | "discarded" | "stale";

export type Target = {
  target: string; path: string; label: string; group: string; unit: string;
  magnitude: string | null; rule: string; derived: boolean; datums: Datum[];
  affects: string[]; text: boolean;
  current: { value: number | string; unit: string; state: string | null; channel?: string | null };
};

export type DesignCatalog = {
  equipment_id: string; kind: string; lod: number; revision_id: string; revision: string;
  version: number; geometry_supported: boolean; targets: Target[];
  datum: { elevation: string; azimuth: string; shell_bottom_mm: number };
  families: Record<string, string>;
  derived_from: { kind: string; revision_id: string; proposal_id: string } | null;
};

export type OperationInput = { id?: string; target: string; value: number | string; unit?: string; datum?: Datum };
export type ProposalInput = {
  operations: OperationInput[]; reason: string; actor: string;
  origin?: "formulario" | "chat"; request_text?: string | null;
  clarifications?: { question: string; options: string[]; operation_id?: string | null }[];
};

export type Issue = {
  severity: "error" | "warning" | "clarification"; code: string; message: string;
  path: string | null; operation_id: string | null; options?: string[];
  allowed?: [number, number] | null; nozzle_id?: string;
};
export type Operation = {
  id: string; target: string; path: string; label: string;
  input: { text: string; unit_original: string | null; datum: Datum | null };
  before: { value: number | string; unit: string }; after: { value: number | string; unit: string };
  resolution?: string;
};
export type Element = {
  part: string; semantic_id: string; global_id: string; in_ifc: boolean; existed_before: boolean;
  geometry_changed: boolean; conflict: boolean; operations: string[];
};
export type Change = {
  path: string; operation: string; before: { value: number | string; unit: string } | null;
  after: { value: number | string; unit: string } | null; impact: string; operation_ids: string[];
};
export type Preview = {
  target_revision: string; schema: string; ifc_bytes: number; params_sha256: string;
  generator_version: string; ifc_url: string; ifc_sha256: string;
  validation: { express_rules: boolean; issues: number };
  timings_ms: Record<string, number>;
  delta: { changes: Change[] }; elements: Element[]; created_at: string;
};
export type Proposal = {
  id: string; status: ProposalStatus; kind: "cambio_diseno" | "reversion"; origin: string;
  actor: string; reason: string; request_text: string | null; input: ProposalInput;
  base: { revision_id: string; revision: string; version: number; input_sha256: string };
  target_revision: string; operations: Operation[]; issues: Issue[];
  effects: { part: string; geometry_changed: boolean; operations: string[] }[];
  derived: { total_height?: { before: number; after: number; unit: string } };
  proposal_sha256: string; preview: Preview | null; applied_revision_id: string | null;
  reverts: string | null; reverted_by: string | null; stale_reason: string | null;
  expires_at: number;
};
export type Applied = { proposal: Proposal; revision_id: string };

export const STATUS_LABEL: Record<ProposalStatus, string> = {
  draft: "Borrador", needs_clarification: "Requiere aclaración", invalid: "No válida",
  ready: "Lista para previsualizar", previewed: "Previsualizada", applied: "Aplicada",
  discarded: "Descartada", stale: "Obsoleta",
};

async function send<T>(path: string, init: RequestInit & { etag?: string; key?: string } = {}): Promise<{ data: T; etag: string | null }> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (init.etag) headers["If-Match"] = init.etag;
  if (init.method && init.method !== "GET") headers["Idempotency-Key"] = init.key ?? crypto.randomUUID();
  const response = await fetch(apiURL(path), { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : `La API respondió ${response.status}`;
    throw new ApiError(response.status, detail);
  }
  return { data: await response.json() as T, etag: response.headers.get("ETag") };
}

const id = (identity: string) => encodeURIComponent(identity);

export async function revisionIdentity(tag: string, label: string) {
  const { data, etag } = await send<{ project_id: string; revision: string; equipment: { id: string } }>(
    `/equipment/${encodeURIComponent(tag)}/revisions/${encodeURIComponent(label)}`);
  return { identity: `${data.project_id}:${data.equipment.id}:${data.revision}`, etag: etag ?? '"0"' };
}

export const getCatalog = async (identity: string) => (await send<DesignCatalog>(`/revisions/${id(identity)}/design-operations`)).data;
export const listProposals = async (identity: string) =>
  (await send<{ proposals: Proposal[] }>(`/revisions/${id(identity)}/change-proposals`)).data.proposals;
export const getProposal = async (proposal: string) => (await send<Proposal>(`/change-proposals/${id(proposal)}`)).data;

export const createProposal = async (identity: string, etag: string, body: ProposalInput) =>
  (await send<Proposal>(`/revisions/${id(identity)}/change-proposals`, { method: "POST", etag, body: JSON.stringify(body) })).data;
export const replaceProposal = async (proposal: string, body: ProposalInput) =>
  (await send<Proposal>(`/change-proposals/${id(proposal)}`, { method: "PUT", body: JSON.stringify(body) })).data;
export const startPreview = async (proposal: string) =>
  (await send<{ job_id: string; steps: number }>(`/change-proposals/${id(proposal)}/preview`, { method: "POST", body: "{}" })).data;
export const applyProposal = async (proposal: Proposal, actor: string, key: string) =>
  (await send<Applied>(`/change-proposals/${id(proposal.id)}/apply`, {
    method: "POST", key, etag: `"${proposal.base.version}"`,
    body: JSON.stringify({ actor, proposal_sha256: proposal.proposal_sha256, preview_ifc_sha256: proposal.preview?.ifc_sha256 }),
  })).data;
export const discardProposal = async (proposal: string, actor: string) =>
  (await send<Proposal>(`/change-proposals/${id(proposal)}/discard`, { method: "POST", body: JSON.stringify({ actor }) })).data;
export const revertProposal = async (proposal: string, etag: string, actor: string, reason: string) =>
  (await send<Proposal>(`/change-proposals/${id(proposal)}/revert`, { method: "POST", etag, body: JSON.stringify({ actor, reason }) })).data;

export const revisionIfcUrl = (identity: string, version: number) =>
  apiURL(`/revisions/${id(identity)}/ifc?draft=true&v=${version}`);
export const previewIfcUrl = (preview: Preview) => apiURL(`${preview.ifc_url}?sha=${preview.ifc_sha256.slice(0, 12)}`);

export type IntentDraft = {
  operations: (OperationInput & { id: string })[];
  clarifications: { question: string; options: string[]; operation_id?: string | null }[];
  rejected: string[]; notes: string[]; provider: string; request_text: string;
  applied: false; notice: string; revision_id: string; version: number;
};

/** El chat solo devuelve un borrador: no crea, valida ni confirma ninguna propuesta. */
export const interpretRequest = async (revisionId: string, text: string, selectedId: string | null, useModel: boolean) =>
  (await send<IntentDraft>("/copiloto/design-proposals", {
    method: "POST", body: JSON.stringify({ revision_id: revisionId, text, selected_id: selectedId, use_model: useModel }),
  })).data;
