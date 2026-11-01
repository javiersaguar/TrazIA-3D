"use client";

import { apiEnabled } from "@/lib/api/config";
import type { RevisionId } from "@/lib/mock/api";
import type { MarkReport, RevisionMark } from "./revision-marks";

export function RevisionMarksNotice({ revision, data, error, loading, onRetry, onSelect, onMark }: {
  revision: RevisionId; data?: MarkReport; error: Error | null; loading: boolean;
  onRetry(): void; onSelect(path: string): void; onMark(mark: RevisionMark): void;
}) {
  if (revision === "A") return null;
  if (!apiEnabled) return <p className="text-xs text-muted">Cruce de marcas: conecta la API para leer los originales.</p>;
  if (error) return <div role="alert" className="text-xs text-warning">{error.message}.
    <button type="button" className="ml-2 underline" onClick={onRetry}>Reintentar marcas</button></div>;
  if (loading || !data) return <p role="status" className="text-xs text-muted">Leyendo marcas de revisión…</p>;
  const count = data.unmarked_changes.length + data.marks_without_change.length;
  const incomplete = data.status !== "ok" && data.status !== "not_applicable";
  return <details className="rounded-lg border border-border bg-surface p-3 text-xs" data-testid="revision-mark-checks">
    <summary className="cursor-pointer text-text">Cruce de marcas de revisión · {count} {count === 1 ? "discrepancia" : "discrepancias"}{incomplete ? " · lectura parcial" : ""}</summary>
    <p className="mt-2 text-muted">Se compara A → B. Las marcas son pistas: una nube o un Δ no confirma un cambio, y su ausencia no demuestra que no lo haya.</p>
    <ul className="mt-2 space-y-2">{data.documents.map(doc => <li key={doc.document_id}>
      <span className="text-text">{doc.filename}: {doc.marks.length} marcas candidatas.</span>
      {doc.unread_pages.length ? <span className="text-warning"> Sin lectura de marcas en páginas {doc.unread_pages.join(", ")}.</span> : null}
      {!["ok", "sin_marcas", "parcial", "sin_lectura"].includes(doc.status) ? <span className="text-warning"> Original no verificable o no disponible.</span> : null}
      {doc.pages_truncated ? <span className="text-warning"> Lectura limitada a 100 páginas.</span> : null}
      <div className="mt-1 flex flex-wrap gap-2">{doc.marks.map(mark => <button type="button" key={mark.id}
        onClick={() => onMark(mark)} className="text-accent-text underline underline-offset-2">
        {mark.kind === "delta" ? "Δ" : "Nube"}{mark.label ? ` ${mark.label}` : ""} · pág. {mark.page}
      </button>)}</div>
    </li>)}</ul>
    {data.unmarked_changes.length ? <div className="mt-3"><strong className="text-warning">Cambios sin marca próxima</strong>
      <ul>{data.unmarked_changes.map(c => <li key={`${c.document_id}-${c.path}`}><button type="button" className="text-accent-text underline underline-offset-2"
        onClick={() => onSelect(c.path)}>{c.path} · {c.document_id}</button></li>)}</ul></div> : null}
    {data.marks_without_change.length ? <div className="mt-3"><strong className="text-warning">Marcas sin cambio detectado</strong>
      <ul>{data.marks_without_change.map(mark => <li key={mark.id}><button type="button" className="text-accent-text underline underline-offset-2" onClick={() => onMark(mark)}>
        {mark.kind === "delta" ? "Δ" : "Nube"} · {mark.document_id}, página {mark.page}
      </button></li>)}</ul></div> : null}
    {data.unlocated_changes.length ? <p className="mt-2 text-muted">Sin ubicación en el plano nuevo: {data.unlocated_changes.join(", ")}. No se juzgan por sus cajas antiguas.</p> : null}
  </details>;
}
