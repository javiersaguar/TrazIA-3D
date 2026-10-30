"use client";

import { FileText, Minus, Plus, ScanLine } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { Tip } from "@/components/ui/controls";
import { Code, EmptyState, Icon, Skeleton } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import type { ReviewField } from "@/lib/mock/fields";

pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
type Props = {
  url: string;
  fields: ReviewField[];
  selectedPath: string | null;
  selectedId: string | null;
  hoveredId: string | null;
  onSelect(field: ReviewField): void;
  onHover(field: ReviewField | null): void;
};

export function PdfPanel({
  url,
  fields,
  selectedPath,
  selectedId,
  hoveredId,
  onSelect,
  onHover,
}: Props) {
  const frame = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0),
    [zoom, setZoom] = useState(1),
    [failed, setFailed] = useState(false),
    [pages, setPages] = useState(0);
  const [override, setOverride] = useState<{
    path: string | null;
    page: number;
  } | null>(null);
  const selected = fields.find((f) => f.path === selectedPath);
  const page = Math.min(
    pages || 1,
    Math.max(
      1,
      override?.path === selectedPath
        ? override.page
        : (selected?.source.page ?? 1),
    ),
  );
  const boxes = useMemo(
    () => fields.filter((f) => f.source.bbox && f.source.page === page),
    [fields, page],
  );
  const fileName = url.split("/").at(-1)?.split("?")[0];
  useEffect(() => {
    const el = frame.current;
    if (!el) return;
    const ro = new ResizeObserver(
      ([entry]) =>
        entry &&
        setWidth(Math.max(80, Math.floor(entry.contentRect.width) - 24)),
    );
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  useEffect(() => {
    if (!selectedPath || !frame.current) return;
    const box = frame.current.querySelector<HTMLElement>(
      `[data-path="${CSS.escape(selectedPath)}"]`,
    );
    box?.scrollIntoView({
      block: "center",
      inline: "center",
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
    });
  }, [selectedPath, zoom, page, width]);
  return (
    <div
      className="flex h-full min-h-0 flex-col"
      data-testid="pdf-panel"
      data-pdf-page={page}
    >
      <div className="flex h-11 shrink-0 items-center gap-2 border-b border-border px-3">
        <Icon icon={FileText} className="text-muted" />
        <Code className="truncate text-text">{fileName}</Code>
        <span className="shrink-0 text-xs text-faint">
          pág. {page}
          {pages ? ` / ${pages}` : ""}
        </span>
        <div className="ml-auto flex items-center gap-0.5">
          <Tip content="Alejar">
            <button
              type="button"
              aria-label="Alejar"
              disabled={zoom <= 1}
              onClick={() => setZoom((z) => Math.max(1, z - 0.5))}
              className="rounded-md p-1.5 text-muted disabled:opacity-40"
            >
              <Icon icon={Minus} size={14} />
            </button>
          </Tip>
          <span className="w-10 text-center text-xs text-muted">
            {Math.round(zoom * 100)} %
          </span>
          <Tip content="Acercar">
            <button
              type="button"
              aria-label="Acercar"
              disabled={zoom >= 3}
              onClick={() => setZoom((z) => Math.min(3, z + 0.5))}
              className="rounded-md p-1.5 text-muted disabled:opacity-40"
            >
              <Icon icon={Plus} size={14} />
            </button>
          </Tip>
        </div>
      </div>
      <div
        ref={frame}
        data-evidence-scroll
        className="drafting-grid relative min-h-0 flex-1 overflow-auto p-3"
      >
        {failed ? (
          <EmptyState icon={ScanLine} title="No se pudo abrir el plano">
            Comprueba la conexión y vuelve a cargar el documento.
          </EmptyState>
        ) : (
          <Document
            file={url}
            loading={<Skeleton className="aspect-[1/1.414] w-full" />}
            onLoadError={() => setFailed(true)}
            onLoadSuccess={({ numPages }) => setPages(numPages)}
            className="mx-auto flex w-fit items-start gap-3"
          >
            {pages > 1 ? (
              <nav
                className="sticky top-0 flex shrink-0 flex-col gap-2"
                aria-label="Páginas del plano"
              >
                {Array.from({ length: pages }, (_, i) => (
                  <button
                    key={i}
                    type="button"
                    aria-label={`Ver página ${i + 1}`}
                    aria-current={page === i + 1 ? "page" : undefined}
                    onClick={() =>
                      setOverride({ path: selectedPath, page: i + 1 })
                    }
                    className={cn(
                      "shrink-0 rounded-md border p-1 text-xs",
                      page === i + 1
                        ? "border-accent bg-accent-soft"
                        : "border-border bg-surface",
                    )}
                  >
                    <Page
                      pageNumber={i + 1}
                      width={64}
                      renderTextLayer={false}
                      renderAnnotationLayer={false}
                    />
                    <span className="block py-1">{i + 1}</span>
                  </button>
                ))}
              </nav>
            ) : null}
            {width > 0 ? (
              <div
                className="relative overflow-hidden rounded-[4px] shadow-lg"
                key={page}
              >
                <Page
                  pageNumber={page}
                  width={Math.max(80, width - (pages > 1 ? 84 : 0)) * zoom}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                  loading={<Skeleton className="aspect-[1/1.414]" />}
                />
                {boxes.map((f) => {
                  const [x0, y0, x1, y1] = f.source.bbox as [
                      number,
                      number,
                      number,
                      number,
                    ],
                    active = f.path === selectedPath,
                    related =
                      !active &&
                      (f.elementId === selectedId || f.elementId === hoveredId);
                  return (
                    <button
                      key={f.path}
                      type="button"
                      data-path={f.path}
                      aria-label={`Evidencia de ${f.label}`}
                      onClick={() => onSelect(f)}
                      onMouseEnter={() => onHover(f)}
                      onMouseLeave={() => onHover(null)}
                      className="group absolute -m-1 p-1"
                      style={{
                        left: `${x0 * 100}%`,
                        top: `${y0 * 100}%`,
                        width: `calc(${(x1 - x0) * 100}% + 8px)`,
                        height: `calc(${(y1 - y0) * 100}% + 8px)`,
                      }}
                    >
                      <span
                        className={cn(
                          "block h-full w-full rounded-[3px] border transition-colors",
                          active
                            ? "border-accent-strong bg-accent/20 shadow-[0_0_0_3px_var(--accent-soft)]"
                            : related
                              ? "border-accent bg-accent/10"
                              : f.status === "candidate"
                                ? "border-accent/40 bg-accent/5 group-hover:border-accent"
                                : "border-approved/50 bg-approved/10",
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
