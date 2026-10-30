"use client";

import { FileUp } from "lucide-react";
import { useRef, useState, type DragEvent } from "react";

import { Badge, Icon, Panel, PanelHeader } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { DOCUMENTS, type DocStage, type SketchDocument } from "@/lib/mock/bocetos";

const STAGES: DocStage[] = ["recibido", "leído", "revisado"];

function StageTrack({ stage }: { stage: DocStage }) {
  const at = STAGES.indexOf(stage);
  return (
    <div className="flex items-center gap-1.5" aria-label={`Estado: ${stage}`}>
      {STAGES.map((s, i) => (
        <span key={s} className="flex items-center gap-1.5">
          {i > 0 ? <span className={cn("h-px w-4", i <= at ? "bg-accent" : "bg-border-strong")} aria-hidden /> : null}
          <span
            title={s}
            className={cn("size-2 rounded-full", i < at ? "bg-accent" : i === at ? "bg-accent ring-3 ring-accent-soft" : "bg-border-strong")}
            aria-hidden
          />
        </span>
      ))}
      <span className="ml-1.5 text-[12px] text-muted capitalize">{stage}</span>
    </div>
  );
}

export function DocumentsSketch() {
  const [docs, setDocs] = useState<(SketchDocument & { local?: boolean })[]>(DOCUMENTS);
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  function add(files: FileList | null) {
    if (!files) return;
    const today = new Date().toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit", year: "numeric" });
    const pdfs = [...files].filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    setDocs((d) => [
      ...pdfs.map((f) => ({ name: f.name, kind: "Plano GA" as const, tag: "—", rev: "—", pages: 0, stage: "recibido" as const, received: today, example: true, local: true })),
      ...d,
    ]);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setOver(false);
    add(e.dataTransfer.files);
  }

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
        className={cn(
          "flex flex-col items-center justify-center gap-2 rounded-[var(--radius-panel)] border border-dashed px-6 py-10 text-center transition-[border-color,background-color] duration-200",
          over ? "border-accent bg-accent-soft" : "border-border-strong bg-surface",
        )}
      >
        <span className={cn("flex size-11 items-center justify-center rounded-full border transition-transform duration-200", over ? "scale-110 border-accent text-accent" : "border-border text-muted")}>
          <Icon icon={FileUp} size={20} />
        </span>
        <p className="text-[15px] font-medium text-strong">Suelta aquí los PDF de los planos GA y hojas de datos</p>
        <p className="text-[13px] text-muted">
          o{" "}
          <button type="button" onClick={() => input.current?.click()} className="text-accent-text underline-offset-2 hover:underline">
            elígelos en tu equipo
          </button>
          . En el boceto se quedan en esta pestaña: no se suben ni se procesan.
        </p>
        <input ref={input} type="file" accept=".pdf,application/pdf" multiple className="sr-only" onChange={(e) => add(e.target.files)} />
      </div>

      <Panel>
        <PanelHeader title="Bandeja de documentos" description="Cada documento pasa por recibido, leído y revisado." />
        <div className="overflow-x-auto px-3 pb-3">
          <table className="w-full min-w-[720px] border-separate border-spacing-0 text-[13px]">
            <thead>
              <tr className="text-left text-xs text-muted">
                {["Documento", "Tipo", "Equipo", "Rev.", "Páginas", "Estado", "Recibido"].map((h, i, a) => (
                  <th
                    key={h}
                    className={cn(
                      "border-y border-border bg-surface-sunken px-3 py-2.5 font-medium",
                      i === 0 && "rounded-l-[var(--radius-control)] border-l",
                      i === a.length - 1 && "rounded-r-[var(--radius-control)] border-r",
                    )}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.name + d.received} className="animate-[row-in_var(--dur-slow)_var(--ease-out)]">
                  <td className="border-b border-border px-3 py-2.5">
                    <span className="font-mono text-[12px] text-text">{d.name}</span>
                    {d.local ? <Badge className="ml-2">en esta pestaña</Badge> : d.example ? <span className="ml-2 text-[11px] text-faint">ejemplo</span> : null}
                  </td>
                  <td className="border-b border-border px-3 py-2.5 text-muted">{d.kind}</td>
                  <td className="border-b border-border px-3 py-2.5 font-mono text-[12px]">{d.tag}</td>
                  <td className="border-b border-border px-3 py-2.5">{d.rev}</td>
                  <td className="border-b border-border px-3 py-2.5 tabular-nums">{d.pages || "—"}</td>
                  <td className="border-b border-border px-3 py-2.5">
                    <StageTrack stage={d.stage} />
                  </td>
                  <td className="border-b border-border px-3 py-2.5 text-muted tabular-nums">{d.received}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
