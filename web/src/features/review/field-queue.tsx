"use client";

import { Check, Pencil, CircleHelp } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { Tip } from "@/components/ui/controls";
import { ConfidenceBar } from "@/components/ui/data";
import { FieldStatusBadge } from "@/components/ui/status";
import { Badge, Button, Icon, Kbd, Skeleton } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { displayUnit, formatInterval, formatValue } from "@/lib/format";
import { riskLevel, type FieldStatus, type ReviewField } from "@/lib/mock/fields";

type Props = {
  fields: ReviewField[] | undefined;
  selectedPath: string | null;
  hoveredId: string | null;
  editingPath: string | null;
  onSelect: (f: ReviewField) => void;
  onHover: (f: ReviewField | null) => void;
  onAction: (f: ReviewField, status: FieldStatus, value?: number | string) => void;
  onEdit: (path: string | null) => void;
};

export function FieldQueue({ fields, selectedPath, hoveredId, editingPath, onSelect, onHover, onAction, onEdit }: Props) {
  const list = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<"all" | "pending">("all");
  const reviewed = fields?.filter((f) => f.status !== "candidate").length ?? 0;
  const total = fields?.length ?? 0;
  const shown = filter === "pending" ? fields?.filter((f) => f.status === "candidate" || f.path === selectedPath) : fields;

  useEffect(() => {
    if (!selectedPath || !list.current) return;
    list.current.querySelector<HTMLElement>(`[data-row="${CSS.escape(selectedPath)}"]`)?.scrollIntoView({ block: "nearest" });
  }, [selectedPath]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b border-border px-4 pt-3 pb-3">
        <div className="flex items-center justify-between">
          <p className="text-[13px] font-medium text-strong">Cola de revisión</p>
          <div className="flex gap-1 text-xs">
            {(["all", "pending"] as const).map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => setFilter(k)}
                className={cn("rounded-[6px] px-2 py-1", filter === k ? "bg-accent-soft text-accent-text" : "text-muted hover:text-text")}
              >
                {k === "all" ? "Todos" : "Por revisar"}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-2.5 flex items-center gap-3">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-sunken">
            <div
              className="h-full origin-left rounded-full bg-approved transition-transform duration-[var(--dur-slow)] ease-[var(--ease-out)]"
              style={{ transform: `scaleX(${total ? reviewed / total : 0})` }}
            />
          </div>
          <span className="text-xs text-muted">
            {reviewed} de {total}
          </span>
        </div>
        <p className="mt-2 text-xs text-faint">
          Ordenada por riesgo: primero lo que hay que confirmar; después, impacto × (1 − confianza).
        </p>
      </div>

      <div ref={list} role="listbox" aria-label="Campos por revisar" className="min-h-0 flex-1 overflow-y-auto p-2">
        {!shown
          ? Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="mb-1.5 h-14 w-full" />)
          : shown.map((f) => (
              <FieldRow
                key={f.path}
                field={f}
                selected={f.path === selectedPath}
                related={f.path !== selectedPath && f.elementId === hoveredId}
                editing={f.path === editingPath}
                onSelect={() => onSelect(f)}
                onHover={(h) => onHover(h ? f : null)}
                onAction={(status, value) => onAction(f, status, value)}
                onEdit={(on) => onEdit(on ? f.path : null)}
              />
            ))}
      </div>
    </div>
  );
}

function FieldRow({
  field,
  selected,
  related,
  editing,
  onSelect,
  onHover,
  onAction,
  onEdit,
}: {
  field: ReviewField;
  selected: boolean;
  related: boolean;
  editing: boolean;
  onSelect: () => void;
  onHover: (h: boolean) => void;
  onAction: (status: FieldStatus, value?: number | string) => void;
  onEdit: (on: boolean) => void;
}) {
  const level = riskLevel(field);
  const shownValue = field.correctedValue ?? field.value;
  const s = field.source;
  const where = s.page ? `${s.document_id} · pág. ${s.page}` : `${s.document_id} · ${s.locator}`;
  const pending = field.status === "candidate";
  const interval =
    pending && field.interval && typeof field.value === "number" ? formatInterval(field.value, field.interval, field.unit) : null;

  return (
    <div
      data-row={field.path}
      role="option"
      aria-selected={selected}
      tabIndex={-1}
      onClick={onSelect}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      className={cn(
        "mb-1 cursor-default rounded-[var(--radius-control)] border px-3 py-2.5",
        "transition-[background-color,border-color] duration-[var(--dur-fast)] ease-[var(--ease-out)]",
        selected ? "border-accent/60 bg-accent-soft/50" : related ? "border-border bg-surface-sunken" : "border-transparent hover:bg-surface-sunken",
      )}
    >
      <div className="flex items-center gap-2.5">
        <span
          className={cn("size-1.5 shrink-0 rounded-full", level === "alto" ? "bg-danger" : level === "medio" ? "bg-warning" : "bg-faint")}
          title={`Riesgo ${level}`}
        />
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] text-text">{field.label}</p>
          <p className="truncate text-[11px] text-faint">{field.group}</p>
        </div>
        <div className="text-right">
          <motion.p
            key={String(shownValue)}
            initial={{ opacity: 0.4 }}
            animate={{ opacity: 1 }}
            className={cn("text-[14px] font-medium", field.status === "corrected" ? "text-accent-text" : "text-text")}
          >
            {formatValue(shownValue, field.unit)}
          </motion.p>
          {interval ? (
            <p className="text-[11px] text-muted" title="Intervalo conforme: contiene el valor verdadero con esa probabilidad">
              {interval}
            </p>
          ) : null}
          {!pending ? (
            <FieldStatusBadge status={field.status} />
          ) : field.abstained ? (
            <span title={`Confianza ${field.confidence.toFixed(2).replace(".", ",")} por debajo del umbral de revisión`}>
              <Badge tone="warning">Confírmelo</Badge>
            </span>
          ) : (
            <ConfidenceBar value={field.confidence} calibrated={field.calibrated} />
          )}
        </div>
      </div>

      {selected ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.16 }} className="mt-2.5 border-t border-border pt-2.5">
          <p className="mb-2 text-xs text-muted">
            Evidencia: <span className="text-text">{where}</span>
            {field.status === "corrected" ? (
              <span className="text-faint"> · leído {formatValue(field.value, field.unit)}</span>
            ) : null}
          </p>
          {field.explanation ? <p className="mb-2 text-xs text-muted">{field.explanation}</p> : null}
          {editing ? (
            <EditValue
              field={field}
              onCancel={() => onEdit(false)}
              onSave={(v) => {
                onAction("corrected", v);
                onEdit(false);
              }}
            />
          ) : (
            <div className="flex flex-wrap gap-1.5">
              <Tip content="Coincide con el plano" shortcut={["A"]}>
                <Button size="sm" variant="primary" onClick={(e) => (e.stopPropagation(), onAction("accepted"))}>
                  <Icon icon={Check} size={14} /> Aceptar
                </Button>
              </Tip>
              <Tip content="Escribir el valor correcto" shortcut={["E"]}>
                <Button size="sm" onClick={(e) => (e.stopPropagation(), onEdit(true))}>
                  <Icon icon={Pencil} size={14} /> Corregir
                </Button>
              </Tip>
              <Tip content="El plano no lo da; se usa el valor como supuesto" shortcut={["S"]}>
                <Button size="sm" variant="ghost" onClick={(e) => (e.stopPropagation(), onAction("assumed"))}>
                  <Icon icon={CircleHelp} size={14} /> Supuesto
                </Button>
              </Tip>
            </div>
          )}
        </motion.div>
      ) : null}
    </div>
  );
}

function EditValue({ field, onSave, onCancel }: { field: ReviewField; onSave: (v: number | string) => void; onCancel: () => void }) {
  const numeric = typeof field.value === "number";
  const [draft, setDraft] = useState(String(field.correctedValue ?? field.value).replace(".", ","));
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => input.current?.select(), []);
  const parsed = numeric ? Number(draft.replace(/\./g, "").replace(",", ".")) : draft.trim();
  const invalid = numeric ? !Number.isFinite(parsed) || (parsed as number) < 0 : !draft.trim();

  return (
    <form
      onClick={(e) => e.stopPropagation()}
      onSubmit={(e) => {
        e.preventDefault();
        if (!invalid) onSave(parsed);
      }}
      className="flex items-center gap-1.5"
    >
      <div className="flex h-8 flex-1 items-center rounded-[var(--radius-control)] border border-border bg-surface focus-within:border-accent">
        <input
          ref={input}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Escape" && onCancel()}
          inputMode={numeric ? "decimal" : "text"}
          aria-label={`Nuevo valor de ${field.label}`}
          aria-invalid={invalid}
          className="h-full min-w-0 flex-1 bg-transparent px-2.5 text-[13px] text-text outline-none"
        />
        {displayUnit(field.unit) ? <span className="pr-2.5 text-xs text-muted">{displayUnit(field.unit)}</span> : null}
      </div>
      <Button size="sm" variant="primary" type="submit" disabled={invalid}>
        Guardar
      </Button>
      <Button size="sm" variant="ghost" onClick={onCancel}>
        <Kbd>Esc</Kbd>
      </Button>
    </form>
  );
}
