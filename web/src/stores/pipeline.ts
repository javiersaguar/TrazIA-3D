"use client";

import { create } from "zustand";
import { apiEnabled, apiURL } from "@/lib/api/config";
import { cancelJob, getPipelineJob, startJob, subscribeJob, uploadDocument, type EquipmentJobInput, type JobStatus } from "@/lib/api/client";
import type { Revision } from "@/lib/types/revision";
import { STAGES, type PipelineEvent, type StageId } from "@/lib/mock/pipeline";

/*
  Repetición simulada del pipeline sobre los documentos sintéticos de una revisión.
  Los recuentos (campos, atributos, boquillas, páginas) salen del JSON real de la demo;
  el ritmo es artificial y por eso no se muestran latencias.
*/

export type StageRunState = {
  status: "idle" | "running" | "done" | "skipped";
  ok: number;
  total: number;
  lastEventAt: number | null;
};

type Step = Omit<PipelineEvent, "id" | "at" | "stage"> & { stage: StageId };

const STEP_MS = 420;

function initialStages(): Record<StageId, StageRunState> {
  return Object.fromEntries(
    STAGES.map((s) => [s.id, { status: "idle", ok: 0, total: 0, lastEventAt: null }]),
  ) as Record<StageId, StageRunState>;
}

/** Guion de eventos a partir del contenido real de la revisión. */
export function buildScript(rev: Revision): Step[] {
  const ga = rev.documents.find((d) => d.filename.toLowerCase().endsWith(".pdf"));
  const hdm = rev.documents.find((d) => d.filename.toLowerCase().endsWith(".xlsx"));
  const eq = rev.equipment;
  const gaFields = 1 + 5 + eq.nozzles.length * 4;
  const attrs = Object.keys(eq.attributes ?? {}).length;
  const ifcName = `rev_${rev.revision.toLowerCase()}.ifc`;
  const steps: Step[] = [];
  const skip = (stage: StageId, file: string) =>
    steps.push({ stage, file, status: "omitido", detail: "Etapa no incluida en esta repetición simulada." });

  if (ga) steps.push({ stage: "ingest", file: ga.filename, status: "ok", detail: `SHA-256 registrado · ${ga.page_count ?? 1} página con capa de texto.` });
  if (hdm) steps.push({ stage: "ingest", file: hdm.filename, status: "ok", detail: "SHA-256 registrado · hoja HDM leída por celdas." });
  if (ga) skip("classify", ga.filename);
  if (ga) steps.push({ stage: "extract_labels", file: ga.filename, status: "ok", detail: `${gaFields} campos candidatos con página y región.` });
  if (ga) {
    skip("extract_tables", ga.filename);
    skip("extract_ocr", ga.filename);
    skip("extract_vision", ga.filename);
  }
  if (hdm) steps.push({ stage: "extract_hdm", file: hdm.filename, status: "ok", detail: `${attrs} atributos con celda de origen.` });
  steps.push({ stage: "reconcile", file: `${eq.tag.value}`, status: "ok", detail: "Sin conflictos · longitudes en mm y ángulos en grados." });
  steps.push({ stage: "family", file: `${eq.tag.value}`, status: "ok", detail: `Recipiente vertical · ${eq.nozzles.length} boquillas radiales.` });
  steps.push({ stage: "ifc", file: ifcName, status: "ok", detail: "IFC4 DRAFT con GUID estables por elemento." });
  steps.push({ stage: "validate", file: ifcName, status: "ok", detail: "Geometría válida · pendiente de revisión humana." });
  return steps;
}

export type PipelineSubmission = {
  files: File[];
  input: Omit<EquipmentJobInput, "documents">;
};
type PipelineState = {
  running: boolean;
  revision: string | null;
  lastFinishedAt: number | null;
  events: PipelineEvent[];
  stages: Record<StageId, StageRunState>;
  activeStage: StageId | null;
  jobId: string | null;
  jobRun: JobStatus["run"];
  jobStatus: string | null;
  jobStrategy: string | null;
  inputFiles: string[];
  warnings: string[];
  error: string | null;
  resultId: string | null;
  start: (rev: Revision, strategy?: string) => void;
  submit: (submission: PipelineSubmission, key: string) => Promise<string | undefined>;
  follow: (id: string) => void;
  cancel: () => void;
};

let timer: ReturnType<typeof setInterval> | null = null;

type Setter = (update: Partial<PipelineState> | ((state: PipelineState) => Partial<PipelineState>)) => void;
let closeEvents: (() => void) | null = null;

const isRunning = (status: JobStatus["status"]) => status === "queued" || status === "running";
const message = (error: unknown) => error instanceof Error ? error.message : String(error);
const freshRun = () => ({
  running: true, error: null, warnings: [], jobRun: null, jobId: null,
  jobStatus: "queued", events: [], stages: initialStages(), activeStage: null,
  resultId: null, lastFinishedAt: null,
});

async function followJob(id: string, set: Setter, get: () => PipelineState) {
  closeEvents?.();
  set({ jobId: id });
  try {
    const job = await getPipelineJob(id);
    if (get().jobId !== id) return;
    if (job.kind !== "pipeline") throw new Error("El enlace no corresponde a un trabajo del pipeline.");
    set({ jobStatus: job.status, jobStrategy: job.strategy ?? null, inputFiles: job.documents ?? [] });

    closeEvents = subscribeJob(id, event => {
      set(state => {
        if (state.jobId !== id || state.events.some(e => e.id === String(event.id))) return {};
        const at = Math.max(0, event.created_at - job.created_at);
        const events = [{ ...event, id: String(event.id), at }, ...state.events];
        const definition = STAGES.find(d => d.id === event.stage);
        if (!definition) return { events };
        const previous = state.stages[definition.id];
        const next: StageRunState = { status: event.status === "omitido" ? "skipped" : "done",
          ok: previous.ok + (event.status === "ok" ? 1 : 0),
          total: previous.total + (event.status === "omitido" ? 0 : 1), lastEventAt: event.created_at * 1000 };
        return { events, error: null, jobStatus: isRunning(job.status) ? "running" : job.status,
          stages: { ...state.stages, [definition.id]: next }, activeStage: definition.id };
      });
    }, () => {
      if (get().jobId !== id) return;
      closeEvents = null;
      void getPipelineJob(id).then(result => set(state => state.jobId === id ? {
        running: false, activeStage: null, jobStatus: result.status, warnings: result.warnings,
        lastFinishedAt: Date.now(), resultId: result.revision_id, jobRun: result.run,
        error: result.status === "done" ? null : result.error ?? (result.status === "cancelled" ? "Trabajo cancelado" : "El trabajo no terminó correctamente."),
      } : {})).catch(() => set(state => state.jobId === id ? {
        running: false, activeStage: null, error: "No se pudo recuperar el resultado. Vuelve a conectar el trabajo.",
      } : {}));
    }, () => set(state => state.jobId === id ? { error: "Conexión de eventos interrumpida. La API intentará reanudarla." } : {}));
  } catch (error) {
    if (get().jobId === id) set({ running: false, jobStatus: "error", error: message(error) });
  }
}

export const usePipeline = create<PipelineState>()((set, get) => ({
  running: false,
  revision: null,
  lastFinishedAt: null,
  events: [],
  stages: initialStages(),
  activeStage: null,

  jobId: null, jobRun: null, jobStatus: null, jobStrategy: null, inputFiles: [], warnings: [], error: null, resultId: null,
  cancel: () => {
    const id = get().jobId;
    if (!id) return;
    void cancelJob(id).catch(error => set(state => state.jobId === id ? { error: message(error) } : {}));
  },
  follow: (id) => {
    set({ ...freshRun(), revision: null, inputFiles: [], jobStrategy: null });
    void followJob(id, set, get);
  },
  submit: async ({ input, files }, key) => {
    if (!apiEnabled || get().running) return;
    set({ ...freshRun(), revision: input.revision ?? null, inputFiles: files.map(file => file.name), jobStrategy: input.strategy ?? null });
    try {
      const documents = [];
      for (const [index, file] of files.entries()) {
        const doc = await uploadDocument(file, undefined, input.revision, `${key}-${index}`);
        documents.push(doc.id);
      }
      const id = await startJob({ ...input, documents }, key);
      void followJob(id, set, get);
      return id;
    } catch (error) {
      set({ running: false, jobStatus: "error", error: message(error) });
    }
  },
  start: (rev, strategy = "b_reglas") => {
    if (apiEnabled) {
      if (get().running) return;
      set({ ...freshRun(), inputFiles: rev.documents.map(d => d.filename), revision: rev.revision, jobStrategy: strategy });
      void (async () => {
        try {
          const identity = `${rev.project_id}:${rev.equipment.id}:${rev.revision}`;
          const revision = `${rev.revision}-run-${Date.now().toString(36)}`;
          const documents = await Promise.all(rev.documents.map(async document => {
            const response = await fetch(apiURL(`/revisions/${encodeURIComponent(identity)}/documents/${encodeURIComponent(document.id)}`));
            if (!response.ok) throw new Error(`No se pudo leer ${document.filename}`);
            return (await uploadDocument(new File([await response.blob()], document.filename), document.id, document.revision)).id;
          }));
          const id = await startJob({ documents, tag: rev.equipment.tag.value, project_id: rev.project_id,
            equipment_id: rev.equipment.id, revision, strategy, dataset: rev.dataset });
          void followJob(id, set, get);
        } catch (error) {
          set({ running: false, jobStatus: "error", error: message(error) });
        }
      })();
      return;
    }
    if (get().running) return;
    if (timer) clearInterval(timer);
    const script = buildScript(rev);
    const startedAt = Date.now();
    let i = 0;
    set({ running: true, revision: rev.revision, events: [], stages: initialStages(), activeStage: null });

    timer = setInterval(() => {
      const step = script[i];
      if (!step) {
        if (timer) clearInterval(timer);
        timer = null;
        set({ running: false, activeStage: null, lastFinishedAt: Date.now() });
        return;
      }
      const now = Date.now();
      const event: PipelineEvent = { ...step, id: `${startedAt}-${i}`, at: (now - startedAt) / 1000 };
      set((s) => {
        const prev = s.stages[step.stage];
        const next: StageRunState =
          step.status === "omitido"
            ? { ...prev, status: "skipped", lastEventAt: now }
            : {
                status: "done",
                ok: prev.ok + (step.status === "ok" ? 1 : 0),
                total: prev.total + 1,
                lastEventAt: now,
              };
        return {
          events: [event, ...s.events],
          stages: { ...s.stages, [step.stage]: next },
          activeStage: step.stage,
        };
      });
      i += 1;
    }, STEP_MS);
  },
}));
