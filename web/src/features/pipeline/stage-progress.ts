import type { PipelineEvent, StageId } from "@/lib/mock/pipeline";

/** Los eventos OK no son un denominador de trabajo pendiente. Solo la ingesta
 * conoce sus documentos de entrada; las otras fases no publican unidades totales. */
export function stageProgress(stage: StageId, events: PipelineEvent[], jobStatus: string | null, inputFiles: string[]) {
  const rows = events.filter(event => event.stage === stage);
  const errors = rows.filter(event => event.status === "error").length;
  const skipped = rows.filter(event => event.status === "omitido").length;
  const ok = rows.filter(event => event.status === "ok").length;
  let percent: number | null = null;
  let basis = "La API no informa unidades totales para este tramo.";
  if (stage === "ingest" && inputFiles.length > 0 && new Set(inputFiles).size === inputFiles.length) {
    const seen = new Set(rows.filter(row => inputFiles.includes(row.file)).map(row => row.file));
    percent = Math.floor(seen.size / inputFiles.length * 100);
    basis = `${seen.size} de ${inputFiles.length} documentos con respuesta de ingesta (incluye errores y duplicados).`;
  } else if (jobStatus === "done" && ok > 0 && errors === 0) {
    percent = 100;
    basis = "Tramo con resultados y trabajo finalizado por el servidor.";
  }
  return { rows, ok, errors, skipped, percent, remaining: percent === null ? null : 100 - percent, basis };
}
