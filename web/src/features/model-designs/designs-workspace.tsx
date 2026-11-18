"use client";

import { Download, Eye, EyeOff, RotateCcw, Search } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { IfcViewer } from "@/components/three";
import { FullscreenFrame } from "@/components/shell/fullscreen";
import { Badge, Button, Icon, Panel } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { useDesignEdits } from "./edits-store";
import { applyEdits, designByTag, DESIGNS, designMeshes, envelope, FAMILY_NAMES, isPristine, type DesignSpec } from "./parametric";
import { useDesignIfc } from "./use-design-ifc";

const ORIGIN_LABEL: Record<DesignSpec["origin"], string> = {
  industrial: "IFC publicado del catálogo",
  boceto: "Boceto GA: IFC generado a partir de su envolvente",
};
const DIMENSIONS = [
  { key: "width", label: "Ancho", index: 0 },
  { key: "height", label: "Alto", index: 1 },
  { key: "depth", label: "Fondo", index: 2 },
] as const;
const mm = (value: number) => `${Math.round(value).toLocaleString("es-ES")} mm`;
const control = "w-full rounded-[var(--radius-control)] border border-border bg-surface px-2 py-1 text-[13px] text-text tabular-nums";

/** Modelo › Diseños: todos los diseños del catálogo en 3D, con sus medidas editables en directo. */
export function DesignsWorkspace() {
  const params = useSearchParams();
  const router = useRouter();
  const selected = designByTag(params.get("diseno")) ?? DESIGNS[0]!;
  const choose = (tag: string) => router.replace(`/modelo?vista=disenos&diseno=${encodeURIComponent(tag)}`, { scroll: false });
  return (
    <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)_320px]">
      <DesignList selected={selected.tag} onChoose={choose} />
      <DesignEditor key={selected.tag} design={selected} />
    </div>
  );
}

function DesignList({ selected, onChoose }: { selected: string; onChoose(tag: string): void }) {
  const [query, setQuery] = useState("");
  const edits = useDesignEdits((s) => s.edits);
  const groups = useMemo(() => {
    const text = query.trim().toLowerCase();
    const map = new Map<string, DesignSpec[]>();
    for (const design of DESIGNS) {
      const family = FAMILY_NAMES[design.family] ?? design.family;
      if (text && !`${design.tag} ${design.name} ${family}`.toLowerCase().includes(text)) continue;
      map.set(family, [...(map.get(family) ?? []), design]);
    }
    return [...map.entries()];
  }, [query]);
  return (
    <Panel className="flex max-h-[760px] flex-col overflow-hidden">
      <div className="space-y-3 border-b border-border p-4">
        <div>
          <h2 className="font-semibold text-strong">Diseños</h2>
          <p className="text-xs text-muted">{DESIGNS.length} equipos conceptuales sintéticos. El V-101 del pipeline está en Revisión.</p>
          <Link href="/documentos?vista=proyectos" className="mt-1 inline-block text-xs text-accent-text hover:underline">Ver complejos de proceso completos</Link>
        </div>
        <label className="relative block">
          <span className="sr-only">Buscar diseño</span>
          <Icon icon={Search} size={14} className="pointer-events-none absolute top-1/2 left-2 -translate-y-1/2 text-faint" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar por tag, nombre o familia"
            className={cn(control, "pl-7")} />
        </label>
      </div>
      <nav aria-label="Catálogo de diseños" className="flex-1 overflow-y-auto p-2">
        {groups.length ? groups.map(([family, designs]) => (
          <section key={family} className="mb-2">
            <h3 className="px-2 py-1 text-xs font-medium text-muted">{family}</h3>
            <ul>
              {designs.map((design) => (
                <li key={design.tag}>
                  <button type="button" onClick={() => onChoose(design.tag)} aria-current={design.tag === selected ? "true" : undefined}
                    className={cn("flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-[13px]",
                      design.tag === selected ? "bg-accent-soft text-strong" : "text-text hover:bg-surface-sunken")}>
                    <span className="min-w-0">
                      <span className="block truncate">{design.name}</span>
                      <span className="font-mono text-[11px] text-faint">{design.tag}</span>
                    </span>
                    {!isPristine(edits[design.tag]) ? <Badge tone="warning">Editado</Badge> : null}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )) : <p className="p-3 text-sm text-muted">Ningún diseño coincide con «{query}».</p>}
      </nav>
    </Panel>
  );
}

/**
 * Campo de una medida. Mientras se escribe se aplica en directo solo lo que ya está en rango
 * (para que «5600» no salte al mínimo con el primer «5»); al salir o pulsar Intro se ajusta al rango.
 */
function DimensionInput({ id, min, max, value, onCommit, describedBy }: {
  id: string; min: number; max: number; value: number; describedBy: string; onCommit(value: number): void;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const finish = () => {
    if (draft !== null && draft.trim() !== "") onCommit(Number(draft));
    setDraft(null);
  };
  return (
    <input id={id} type="number" inputMode="numeric" min={min} max={max} step={10} value={draft ?? value}
      aria-describedby={describedBy} className={control}
      onChange={(e) => {
        setDraft(e.target.value);
        const next = Number(e.target.value);
        if (e.target.value.trim() !== "" && next >= min && next <= max) onCommit(next);
      }}
      onBlur={finish}
      onKeyDown={(e) => {
        if (e.key === "Enter") finish();
        if (e.key === "Escape") setDraft(null);
      }} />
  );
}

function DesignEditor({ design }: { design: DesignSpec }) {
  const edits = useDesignEdits((s) => s.edits[design.tag]);
  const setDimension = useDesignEdits((s) => s.setDimension);
  const setPart = useDesignEdits((s) => s.setPart);
  const reset = useDesignEdits((s) => s.reset);
  const pristine = isPristine(edits);
  const current = useMemo(() => applyEdits(design, edits), [design, edits]);
  const ifc = useDesignIfc(current, !pristine);
  const original = useMemo(() => envelope(designMeshes(design)), [design]);
  const now = useMemo(() => envelope(designMeshes(current)), [current]);
  const family = FAMILY_NAMES[design.family] ?? design.family;
  return (
    <>
      <Panel className="min-w-0 p-3">
        <FullscreenFrame
          testId="design-viewer"
          height="h-[640px]"
          title={<span className="flex flex-wrap items-baseline gap-2">{design.name} <span className="font-mono text-xs font-normal text-faint">{design.tag}</span></span>}
          description={`${family} · ${pristine ? ORIGIN_LABEL[design.origin] : "IFC4 regenerado en este navegador con tus cambios"} · DRAFT sintético`}
          actions={<>
            {pristine ? <Badge>Original</Badge> : <Badge tone="warning">Editado</Badge>}
            {ifc.url ? <a href={ifc.url} download={ifc.filename ?? undefined}
              className="inline-flex items-center gap-1 text-sm text-accent-text underline-offset-2 hover:underline">
              <Icon icon={Download} size={14} />Descargar IFC</a> : null}
          </>}
        >
          <div className="flex h-full flex-col gap-2">
            <p role="status" aria-live="polite" data-testid="design-ifc-status"
              data-state={ifc.error ? "error" : ifc.building ? "building" : "ready"}
              className={cn("text-xs tabular-nums", ifc.error ? "text-danger" : "text-muted")}>
              {ifc.error ? `No se pudo generar el IFC: ${ifc.error}`
                : ifc.building ? "Regenerando IFC…"
                  : ifc.generated ? `IFC ${pristine ? "generado" : "regenerado"} en ${Math.max(1, Math.round(ifc.ms ?? 0))} ms · ${ifc.parts} piezas`
                    : `IFC publicado · ${ifc.parts} piezas`}
            </p>
            <div className="min-h-0 flex-1">{ifc.url ? <IfcViewer ifcUrl={ifc.url} holdPrevious /> : null}</div>
          </div>
        </FullscreenFrame>
      </Panel>

      <Panel className="flex max-h-[760px] flex-col overflow-hidden">
        <div className="flex items-start justify-between gap-2 border-b border-border p-4">
          <div>
            <h2 className="font-semibold text-strong">Cambios en directo</h2>
            <p className="text-xs text-muted">Cada cambio reescribe el IFC y el visor lo vuelve a leer.</p>
          </div>
          <Button size="sm" disabled={pristine} onClick={() => reset(design.tag)}><Icon icon={RotateCcw} size={14} />Restablecer</Button>
        </div>
        <div className="flex-1 space-y-5 overflow-y-auto p-4">
          <fieldset className="space-y-3">
            <legend className="text-sm font-medium text-strong">Envolvente</legend>
            {DIMENSIONS.map(({ key, label, index }) => {
              const base = design.size[index]!;
              const value = current.size[index]!;
              const min = Math.round(base * 0.3), max = Math.round(base * 3);
              const set = (raw: number) => {
                if (!Number.isFinite(raw)) return;
                const clamped = Math.min(max, Math.max(min, Math.round(raw)));
                setDimension(design.tag, key, clamped === base ? undefined : clamped);
              };
              return (
                <div key={key} className="grid grid-cols-[44px_minmax(0,1fr)_84px] items-center gap-2 text-[13px]">
                  <label htmlFor={`dim-${key}`} className="text-muted">{label}</label>
                  <input type="range" aria-label={`${label} (deslizador)`} min={min} max={max} step={10} value={value}
                    onChange={(e) => set(Number(e.target.value))} className="w-full min-w-0 accent-[var(--accent)]" />
                  <DimensionInput id={`dim-${key}`} min={min} max={max} value={value} onCommit={set}
                    describedBy={`dim-${key}-base`} />
                  <span id={`dim-${key}-base`} className="col-span-3 -mt-1 text-right text-[11px] text-faint">
                    {value === base ? "como el original" : `original ${mm(base)} · ${value > base ? "+" : ""}${mm(value - base)}`}
                  </span>
                </div>
              );
            })}
          </fieldset>

          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-strong">Piezas</legend>
            <p className="text-xs text-muted">Oculta una pieza o cambia su tamaño sobre su centro, dentro de la envolvente.</p>
            {design.parts.map((part) => {
              const edit = edits?.parts?.[part.name];
              const hidden = !!edit?.hidden;
              const scale = edit?.scale ?? 1;
              return (
                <div key={part.name} className={cn("rounded-md border border-border p-2", hidden && "opacity-60")}>
                  <div className="flex items-center justify-between gap-2 text-[13px]">
                    <span className="truncate" title={part.name}>{part.name}</span>
                    <button type="button" aria-pressed={!hidden} aria-label={`${hidden ? "Mostrar" : "Ocultar"} ${part.name}`}
                      onClick={() => setPart(design.tag, part.name, { hidden: !hidden })}
                      className="rounded p-1 text-muted hover:bg-surface-sunken hover:text-text">
                      <Icon icon={hidden ? EyeOff : Eye} size={14} />
                    </button>
                  </div>
                  <label className="mt-1 grid grid-cols-[1fr_44px] items-center gap-2 text-[11px] text-muted">
                    <input type="range" aria-label={`Tamaño de ${part.name}`} min={0.5} max={1.5} step={0.05} value={scale}
                      disabled={hidden} onChange={(e) => setPart(design.tag, part.name, { scale: Number(e.target.value) })}
                      className="accent-[var(--accent)]" />
                    <span className="text-right tabular-nums">{Math.round(scale * 100)} %</span>
                  </label>
                </div>
              );
            })}
          </fieldset>

          <section className="space-y-1 rounded-md bg-surface-sunken p-3 text-xs text-muted">
            <p className="font-medium text-text">Medidas del IFC</p>
            <p className="tabular-nums">Ancho {mm(now.width)} · Fondo {mm(now.depth)} · Alto {mm(now.height)}</p>
            {!pristine ? <p className="tabular-nums">Antes: {mm(original.width)} · {mm(original.depth)} · {mm(original.height)}</p> : null}
            <p>Geometría conceptual sintética. Los cambios se guardan en este navegador y no crean una revisión:
              para una propuesta trazable del V-101 usa <Link href="/modelo?vista=editar" className="text-accent-text underline-offset-2 hover:underline">Proponer cambios</Link>.</p>
          </section>
        </div>
      </Panel>
    </>
  );
}
