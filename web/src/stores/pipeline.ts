"use client";

import { create } from "zustand";
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

type Step = Omit<PipelineEvent, "id" | "at">;

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
    steps.push({ stage, file, status: "omitido", detail: "Etapa aún no implementada en el núcleo." });

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

type PipelineState = {
  running: boolean;
  revision: string | null;
  lastFinishedAt: number | null;
  events: PipelineEvent[];
  stages: Record<StageId, StageRunState>;
  activeStage: StageId | null;
  start: (rev: Revision) => void;
};

let timer: ReturnType<typeof setInterval> | null = null;

export const usePipeline = create<PipelineState>()((set, get) => ({
  running: false,
  revision: null,
  lastFinishedAt: null,
  events: [],
  stages: initialStages(),
  activeStage: null,

  start: (rev) => {
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
