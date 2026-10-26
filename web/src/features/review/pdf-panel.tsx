"use client";

import { FileText, Minus, Plus, ScanLine } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { Tip } from "@/components/ui/controls";
import { Code, EmptyState, Icon, Skeleton } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import type { ReviewField } from "@/lib/mock/fields";

// Worker copiado a public/ por scripts/copy-pdf-worker.mjs
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

type Props = {
  url: string;
  fields: ReviewField[];
  selectedPath: string | null;
  selectedId: string | null;
  hoveredId: string | null;
  onSelect: (field: ReviewField) => void;
  onHover: (field: ReviewField | null) => void;
};

/** Plano PDF con los recuadros de evidencia (bbox normalizada, origen arriba a la izquierda). */
export function PdfPanel({ url, fields, selectedPath, selectedId, hoveredId, onSelect, onHover }: Props) {
  const frame = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [failed, setFailed] = useState(false);
  const boxes = useMemo(() => fields.filter((f) => f.source.bbox && f.source.page === 1), [fields]);
  const fileName = url.split("/").at(-1);

  useEffect(() => {
    const el = frame.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => entry && setWidth(Math.floor(entry.contentRect.width) - 24));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Acerca la vista al recuadro del campo seleccionado (desplazamiento suave, interrumpible por el usuario).
  useEffect(() => {
    if (!selectedPath || !frame.current) return;
    const box = frame.current.querySelector<HTMLElement>(`[data-path="${CSS.escape(selectedPath)}"]`);
    if (!box) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    box.scrollIntoView({ block: "center", inline: "center", behavior: reduce ? "auto" : "smooth" });
  }, [selectedPath, zoom]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-11 items-center gap-2 border-b border-border px-3">
        <Icon icon={FileText} className="text-muted" />
        <Code className="truncate text-text">{fileName}</Code>
        <span className="text-xs text-faint">pág. 1</span>
        <div className="ml-auto flex items-center gap-0.5">
          <Tip content="Alejar">
            <button type="button" aria-label="Alejar" onClick={() => setZoom((z) => Math.max(1, z - 0.5))} className="rounded-[6px] p-1.5 text-muted hover:bg-surface-sunken hover:text-text disabled:opacity-40" disabled={zoom <= 1}>
              <Icon icon={Minus} size={14} />
            </button>
          </Tip>
          <span className="w-10 text-center text-xs text-muted">{Math.round(zoom * 100)} %</span>
          <Tip content="Acercar">
            <button type="button" aria-label="Acercar" onClick={() => setZoom((z) => Math.min(3, z + 0.5))} className="rounded-[6px] p-1.5 text-muted hover:bg-surface-sunken hover:text-text disabled:opacity-40" disabled={zoom >= 3}>
              <Icon icon={Plus} size={14} />
            </button>
          </Tip>
        </div>
      </div>

      <div ref={frame} className="drafting-grid relative min-h-0 flex-1 overflow-auto p-3">
        {failed ? (
          <EmptyState icon={ScanLine} title="No se pudo abrir el plano">
            Comprueba que {fileName} existe en public/demo/docs y vuelve a cargar la página.
          </EmptyState>
        ) : (
          <Document
            file={url}
            loading={<Skeleton className="aspect-[1/1.414] w-full" />}
            onLoadError={() => setFailed(true)}
            className="mx-auto w-fit"
          >
            {width > 0 ? (
              <div className="relative overflow-hidden rounded-[4px] shadow-[0_1px_0_var(--border),0_8px_24px_-12px_rgb(0_0_0/0.4)]">
                <Page
                  pageNumber={1}
                  width={width * zoom}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                  loading={<Skeleton className="aspect-[1/1.414]" />}
                />
                {boxes.map((f) => {
                  const [x0, y0, x1, y1] = f.source.bbox as [number, number, number, number];
                  const selected = f.path === selectedPath;
                  const related = !selected && (f.elementId === selectedId || f.elementId === hoveredId);
                  return (
                    <button
                      key={f.path}
                      type="button"
                      data-path={f.path}
                      aria-label={`Evidencia de ${f.label}`}
                      onClick={() => onSelect(f)}
                      onMouseEnter={() => onHover(f)}
                      onMouseLeave={() => onHover(null)}
                      // Zona de clic algo mayor que el texto (hit slop) sin desplazar el recuadro visible
                      className="group absolute -m-1 p-1"
                      style={{ left: `${x0 * 100}%`, top: `${y0 * 100}%`, width: `calc(${(x1 - x0) * 100}% + 8px)`, height: `calc(${(y1 - y0) * 100}% + 8px)` }}
                    >
                      <span
                        className={cn(
                          "block h-full w-full rounded-[3px] border transition-[background-color,border-color,box-shadow] duration-[var(--dur-fast)] ease-[var(--ease-out)]",
                          selected
                            ? "border-accent-strong bg-accent/20 shadow-[0_0_0_3px_var(--accent-soft)]"
                            : related
                              ? "border-accent bg-accent/10"
                              : f.status === "candidate"
                                ? "border-accent/40 bg-accent/5 group-hover:border-accent group-hover:bg-accent/15"
                                : "border-approved/50 bg-approved/10 group-hover:border-approved",
                        )}
                      />
                    </button>
                  );
                })}
              </div>
            ) : null}
          </Document>
        )}
      </div>
    </div>
  );
}
