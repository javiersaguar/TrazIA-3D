import { describe, expect, it } from "vitest";
import { stageProgress } from "./stage-progress";
import type { PipelineEvent } from "@/lib/mock/pipeline";
const event = (stage: string, file: string, status: PipelineEvent["status"] = "ok"): PipelineEvent => ({ id: `${stage}-${file}-${status}`, stage, file, status, detail: "Dato del servidor", at: 1 });

describe("progreso respaldado por eventos", () => {
  it("cuenta documentos conocidos y conserva errores, sin confundir cobertura con éxito", () => {
    const rows = [event("ingest", "a.pdf"), event("ingest", "a.pdf"), event("ingest", "b.pdf", "error")];
    expect(stageProgress("ingest", rows.slice(0, 2), "running", ["a.pdf", "b.pdf"]).percent).toBe(50);
    expect(stageProgress("ingest", rows, "error", ["a.pdf", "b.pdf"])).toMatchObject({ percent: 100, errors: 1, remaining: 0 });
  });
  it("no usa OK/total de eventos como porcentaje de procesamiento", () => {
    expect(stageProgress("extract_ocr", [event("extract_ocr", "a.pdf")], "running", []).percent).toBeNull();
    expect(stageProgress("extract_ocr", [event("extract_ocr", "a.pdf")], "cancelled", []).percent).toBeNull();
  });
  it("solo cierra tramos observados sin error al finalizar un trabajo correctamente", () => {
    expect(stageProgress("ifc", [event("ifc", "modelo.ifc")], "done", [])).toMatchObject({ percent: 100, remaining: 0 });
    expect(stageProgress("ifc", [], "done", []).percent).toBeNull();
    expect(stageProgress("ifc", [event("ifc", "modelo.ifc", "error")], "done", []).percent).toBeNull();
  });
  it("no infiere un denominador ante nombres ambiguos ni cuenta omisiones como éxito", () => {
    expect(stageProgress("ingest", [event("ingest", "a.pdf")], "running", ["a.pdf", "a.pdf"]).percent).toBeNull();
    expect(stageProgress("extract_vision", [event("extract_vision", "a.pdf", "omitido")], "done", [])).toMatchObject({ percent: null, skipped: 1, ok: 0 });
  });
});
