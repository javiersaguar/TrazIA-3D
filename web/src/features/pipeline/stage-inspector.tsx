"use client";

import { X } from "lucide-react";
import { Button, Icon } from "@/components/ui/primitives";
import type { PipelineEvent, StageDef } from "@/lib/mock/pipeline";
import { stageProgress } from "./stage-progress";

export function StageInspector({ jobLabel, def, events, actual, jobStatus, inputFiles, connectionError, onClose }: {
  jobLabel: string; def: StageDef; events: PipelineEvent[]; actual: boolean; jobStatus: string | null;
  inputFiles: string[]; connectionError: string | null; onClose: () => void;
}) {
  const data = stageProgress(def.id, actual ? events : [], actual ? jobStatus : null, actual ? inputFiles : []);
  const statusLabel = ({ queued: "en cola", running: "en curso", done: "finalizado", error: "fallido", cancelled: "cancelado", timeout: "tiempo agotado" } as Record<string, string>)[jobStatus ?? ""] ?? "sin estado";
  const state = !actual ? "Sin trabajo real" : data.errors ? "Con errores" : data.skipped && !data.ok ? "Omitida" : jobStatus === "done" && data.ok ? "Finalizada" : data.rows.length ? "Resultados recibidos" : "Sin eventos de esta fase";
  return <aside aria-label="Detalle de la etapa" className="absolute top-3 right-3 z-20 max-h-[calc(100%-24px)] w-[360px] max-w-[calc(100%-24px)] overflow-auto rounded-xl border border-accent/60 bg-surface p-4 shadow-2xl">
    <div className="flex items-start justify-between gap-3"><div><p className="font-mono text-[10px] uppercase tracking-wider text-accent-text">Inspector de fase</p><h3 className="mt-1 text-lg font-semibold text-strong">{def.name}</h3></div><Button size="sm" variant="ghost" aria-label="Cerrar detalle de etapa" onClick={onClose}><Icon icon={X} size={16} /></Button></div>
    <p className="mt-2 text-[13px] leading-relaxed text-muted">{def.description}</p>
    <div className="mt-4 border-t border-border pt-3">
      <p className="text-xs font-semibold text-strong">{actual ? "Datos reales del trabajo" : "Sin datos reales de ejecución"}</p>
      {actual ? <p className="mt-1 break-all font-mono text-[10px] text-faint">Último trabajo: {jobLabel}</p> : null}
      <p className="mt-1 text-xs text-muted">{state}{actual && jobStatus ? ` · trabajo ${statusLabel}` : " · la explicación no ejecuta esta fase"}</p>
      {connectionError ? <p role="status" className="mt-2 text-xs text-danger">{connectionError} Se conservan los últimos datos recibidos.</p> : null}
      <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
        {[["Eventos OK", data.ok], ["Errores", data.errors], ["Omisiones", data.skipped]].map(([label, value]) => <div key={label}><dt className="text-muted">{label}</dt><dd className="mt-1 font-mono text-lg font-semibold text-strong">{actual ? value : "—"}</dd></div>)}
      </dl>
      <div className="mt-4 rounded-lg border border-border bg-surface-sunken p-3" data-testid="stage-progress">
        <p className="text-xs font-medium text-strong">{def.id === "ingest" ? "Cobertura de documentos" : "Progreso del tramo"}</p>
        {actual && data.percent !== null ? <><p className="mt-1 text-lg font-semibold text-accent-text">{data.percent} % <span className="text-xs font-normal text-muted">· queda {data.remaining} %</span></p><div role="progressbar" aria-label="Progreso comunicado de la fase" aria-valuenow={data.percent} aria-valuemin={0} aria-valuemax={100} className="mt-2 h-1.5 overflow-hidden rounded-full bg-border"><div className="h-full origin-left bg-accent" style={{ transform: `scaleX(${data.percent / 100})` }} /></div></> : <p className="mt-2 text-sm text-muted">{actual ? "Porcentaje pendiente no informado por la API" : "Porcentaje real no disponible"}</p>}
        <p className="mt-2 text-[11px] leading-relaxed text-muted">{actual ? data.basis : "La animación didáctica tiene su propio ritmo; no representa procesamiento medido."}</p>
      </div>
    </div>
    <div className="mt-4"><h4 className="text-xs font-semibold text-strong">Últimos datos comunicados</h4>
      {data.rows.length ? <ul className="mt-2 space-y-2">{data.rows.slice(0, 6).map(row => <li key={row.id} className="rounded-lg border border-border p-2 text-xs"><p className="break-all font-mono text-accent-text">{row.file || "Equipo / modelo"} · {row.status}</p><p className="mt-1 leading-relaxed text-muted">{row.detail}</p></li>)}</ul> : <p className="mt-2 text-xs text-muted">Todavía no hay datos comunicados para esta fase.</p>}
      <p className="mt-3 text-[10px] leading-relaxed text-faint">Estos mensajes son el detalle disponible del servidor. No son una vista de todos los valores intermedios ni una estimación del tiempo restante.</p>
    </div>
  </aside>;
}
