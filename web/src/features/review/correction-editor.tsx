"use client";

import { useEffect, useRef, useState } from "react";
import { Button, Kbd } from "@/components/ui/primitives";
import { displayUnit } from "@/lib/format";
import type { FieldOptions } from "@/lib/mock/api";
import type { ReviewField } from "@/lib/mock/fields";

import { parseReviewNumber } from "./review-value";

export function CorrectionEditor({ field, busy, onSave, onCancel }: {
  field: ReviewField; busy: boolean;
  onSave: (value: number | string, options: FieldOptions) => void | Promise<void>;
  onCancel: () => void;
}) {
  const numeric = typeof field.value === "number";
  const [draft, setDraft] = useState(String(field.correctedValue ?? field.value).replace(".", ","));
  const [note, setNote] = useState("");
  const [changeSource, setChangeSource] = useState(false);
  const [documentId, setDocumentId] = useState(field.source.document_id);
  const [page, setPage] = useState(String(field.source.page ?? ""));
  const [locator, setLocator] = useState(field.source.locator);
  const [box, setBox] = useState("");
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => input.current?.select(), []);
  const parsed = numeric ? parseReviewNumber(draft) : draft.trim();
  const bbox = box.trim() ? box.trim().split(/[;\s]+/).map(Number) : null;
  const badBox = bbox !== null && (bbox.length !== 4 || bbox.some((n) => !Number.isFinite(n) || n < 0 || n > 1) || bbox[0]! >= bbox[2]! || bbox[1]! >= bbox[3]!);
  const badSource = changeSource && (!documentId.trim() || !locator.trim() || !Number.isInteger(Number(page)) || Number(page) < 1 || badBox);
  const invalid = (numeric ? !Number.isFinite(parsed) : !draft.trim()) || badSource;
  const control = "w-full rounded border border-border bg-surface p-2 text-text";

  return <form onClick={(e) => e.stopPropagation()} onSubmit={(e) => {
    e.preventDefault();
    if (invalid || busy) return;
    void onSave(parsed, {
      action: "correct", explanation: note.trim() || undefined,
      source: changeSource ? {
        ...field.source, document_id: documentId.trim(), page: Number(page),
        sheet: null, cell: null, locator: locator.trim(), bbox: bbox as [number, number, number, number] | null,
        channel: "humano", grounded: null, strategy: null, model: null, prompt_sha256: null,
      } : undefined,
    });
  }} className="space-y-2 text-xs">
    <fieldset disabled={busy} className="space-y-2">
      <div className="flex items-center gap-1.5">
        <input ref={input} value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Escape" && onCancel()} inputMode={numeric ? "decimal" : "text"} aria-label={`Nuevo valor de ${field.label}`} aria-invalid={invalid} className={control} />
        <span>{displayUnit(field.unit)}</span>
        <Button size="sm" variant="primary" type="submit" disabled={invalid || busy}>Guardar</Button>
        <Button size="sm" variant="ghost" onClick={onCancel}><Kbd>Esc</Kbd></Button>
      </div>
      <label className="block">Nota de revisión (opcional)<input value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000} className={control} /></label>
      <label className="flex items-center gap-2"><input type="checkbox" checked={changeSource} onChange={(e) => setChangeSource(e.target.checked)} />Cambiar evidencia (opcional)</label>
      {changeSource && <div className="grid grid-cols-2 gap-2">
        <label>Documento de esta revisión<input value={documentId} onChange={(e) => setDocumentId(e.target.value)} className={control} /></label>
        <label>Página<input type="number" min={1} step={1} value={page} onChange={(e) => setPage(e.target.value)} className={control} /></label>
        <label className="col-span-2">Localizador<input value={locator} onChange={(e) => setLocator(e.target.value)} className={control} /></label>
        <label className="col-span-2">Región normalizada (opcional)<input value={box} onChange={(e) => setBox(e.target.value)} className={control} placeholder="x0 y0 x1 y1 · de 0 a 1, con punto decimal" /></label>
      </div>}
      {invalid && <p role="alert" className="text-warning">Comprueba el valor y, si cambias la evidencia, documento, página y región.</p>}
    </fieldset>
  </form>;
}
