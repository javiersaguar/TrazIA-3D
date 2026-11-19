"use client";

import { ArrowLeft, ChevronRight, Crosshair } from "lucide-react";
import { useState } from "react";
import { Badge, Button, Icon, Panel } from "@/components/ui/primitives";
import type { PlantProductInfo } from "@/features/viewer3d/types";
import { apiEnabled } from "@/lib/api/config";
import { cn } from "@/lib/cn";
import type { EditFields, Parameter } from "./catalog";

export type Inputs = Record<string, Partial<Record<Parameter, string>>>;

const parameters: Record<Parameter, { title: string; unit: string; prop: string }> = {
  length: { title: "Largo nominal", unit: "m", prop: "NominalLengthM" },
  width: { title: "Ancho o diámetro", unit: "m", prop: "NominalWidthM" },
  height: { title: "Altura nominal", unit: "m", prop: "NominalHeightM" },
  dn: { title: "Diámetro nominal DN", unit: "mm", prop: "NominalDiameterMM" },
  rack_z: { title: "Cota sobre cubierta", unit: "m", prop: "RackHeightM" },
};
const numeric = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 3 });
const control = "min-w-0 rounded-md border border-border bg-canvas px-2.5 py-1.5 text-sm text-text";

function readable(key: string) {
  return key.replace(/MM$/, " (mm)").replace(/M$/, " (m)").replace(/([a-záéíóú])([A-Z])/g, "$1 $2");
}

function title(item: PlantProductInfo) {
  return item.parentId ? (item.label ?? item.name).split(" · ").slice(1).join(" · ") || item.name : item.label ?? item.name;
}

export function ComponentInspector({
  products, selected, select, editFields, inputs, dimensions, setDimensions, onInput,
  onPreview, onReset, busy, error, draft,
}: {
  products: Map<string, PlantProductInfo>;
  selected?: string;
  select(id: string): void;
  editFields?: EditFields;
  inputs: Inputs;
  dimensions: boolean;
  setDimensions(value: boolean): void;
  onInput(tag: string, field: Parameter, value: string): void;
  onPreview(): void;
  onReset(): void;
  busy: boolean;
  error: string;
  draft: boolean;
}) {
  const [query, setQuery] = useState("");
  const item = selected ? products.get(selected) : undefined;
  const parent = item?.parentId ? products.get(item.parentId) : undefined;
  const editOwner = parent ?? item;
  const trace = item?.psets.TrazIA_Traceability;
  const dimensionsIfc = Object.entries(item?.psets.TrazIA_Dimensiones ?? {});
  const extent = item ? [0, 2, 1].map(axis => item.bounds.max[axis]! - item.bounds.min[axis]!) : [];
  const children = item?.childIds?.map(id => products.get(id)).filter(child => child !== undefined) ?? [];
  const roots = [...products.values()].filter(product => !product.parentId);
  const filtered = roots.filter(product => title(product).toLocaleLowerCase("es").includes(query.trim().toLocaleLowerCase("es")));
  const pending = Object.values(inputs).flatMap(Object.values).filter(value => value !== "").length;
  const fields = Object.entries(editFields ?? {}) as [Parameter, NonNullable<EditFields[Parameter]>][];

  return <Panel className="overflow-hidden" aria-label="Ficha de componente">
    <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
      <h2 className="text-sm font-semibold text-strong">Ficha de componente</h2>
      {item ? <Button size="sm" onClick={() => select(parent?.semanticId ?? "")}>
        <Icon icon={ArrowLeft} size={14} /> {parent ? "Al conjunto" : "A la planta"}
      </Button> : null}
    </div>
    {!item ? <div className="space-y-3 p-4">
      <label className="grid gap-1 text-xs font-medium text-muted">Buscar equipos y líneas
        <input type="search" className={control} value={query} onChange={event => setQuery(event.target.value)} />
      </label>
      <p className="text-xs text-muted">Selecciona un conjunto en el visor o en la lista.</p>
      <ul className="max-h-64 divide-y divide-border overflow-auto" aria-label="Componentes de planta">
        {filtered.map(product => <li key={product.semanticId}>
          <button type="button" className="flex w-full items-center justify-between gap-3 rounded px-2 py-2 text-left text-sm text-text hover:bg-surface-raised"
            onClick={() => select(product.semanticId)}>
            {title(product)} <Icon icon={ChevronRight} size={14} />
          </button>
        </li>)}
      </ul>
      {!filtered.length && roots.length ? <p className="text-sm text-muted">Ningún componente coincide.</p> : null}
    </div> : <div className="space-y-3 p-4">
      <div>
        <p className="font-mono text-xs text-accent-text">{item.tag}</p>
        <h3 className="mt-1 text-base font-semibold leading-tight text-strong">{title(item)}</h3>
        <p className="mt-1 text-xs text-muted">{String(trace?.Service ?? trace?.Fluid ?? item.description ?? item.ifcType)}</p>
      </div>
      <div className="rounded-lg border border-border bg-canvas p-2.5">
        <div className="flex items-center justify-between gap-2">
          <h4 className="text-xs font-semibold text-muted">Envolvente IFC</h4>
          <button type="button" aria-pressed={dimensions} onClick={() => setDimensions(!dimensions)}
            className={cn("inline-flex items-center gap-1 rounded border px-2 py-1 text-xs", dimensions ? "border-accent text-accent-text" : "border-border text-text")}>
            <Icon icon={Crosshair} size={12} /> Cotas en 3D
          </button>
        </div>
        <dl className="mt-2 grid grid-cols-3 gap-1">
          {["Largo X", "Fondo Y", "Alto Z"].map((label, i) => <div key={label}>
            <dt className="text-[11px] text-muted">{label}</dt>
            <dd className="font-mono text-xs text-strong">{numeric.format(extent[i]!)} m</dd>
          </div>)}
        </dl>
      </div>
      <details open={dimensionsIfc.length > 0 && dimensionsIfc.length <= 5}>
        <summary className="cursor-pointer text-sm font-semibold text-strong">Propiedades IFC</summary>
        <dl className="mt-2 grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-1.5 break-words text-xs text-muted">
          <dt>Clase</dt><dd className="text-right font-mono text-text">{item.ifcType}</dd>
          <dt>GUID</dt><dd className="text-right font-mono text-text">{item.globalId}</dd>
          {dimensionsIfc.map(([key, value]) => <div key={key} className="contents">
            <dt>{readable(key)}</dt>
            <dd className="text-right font-mono text-text">
              {typeof value === "number" ? numeric.format(value) : String(value ?? "—")}
            </dd>
          </div>)}
        </dl>
      </details>
      {children.length ? <details key={item.semanticId} open>
        <summary className="cursor-pointer text-sm font-semibold text-strong">Piezas del conjunto · {children.length}</summary>
        <ul className="mt-2 max-h-48 divide-y divide-border overflow-auto" aria-label="Piezas del conjunto">
          {children.map(child => <li key={child.semanticId}>
            <button type="button" className="flex w-full items-center justify-between gap-2 px-2 py-2 text-left text-xs text-text hover:bg-surface-raised"
              onClick={() => select(child.semanticId)}>
              {title(child)} <Icon icon={ChevronRight} size={13} />
            </button>
          </li>)}
        </ul>
      </details> : null}
      {fields.length && editOwner?.tag ? <form className="space-y-2 border-t border-border pt-3"
        onSubmit={event => { event.preventDefault(); onPreview(); }}>
        <h4 className="text-sm font-semibold text-strong">{parent ? `Ensayar cambios en ${editOwner.tag}` : "Ensayar cambios"}</h4>
        {apiEnabled ? fields.map(([field, range]) => {
          const parameter = parameters[field];
          const current = editOwner.psets.TrazIA_Traceability?.[parameter.prop];
          const tag = editOwner.tag!;
          return <label key={field} className="grid grid-cols-[1fr_6.5rem] items-center gap-2 text-xs text-text">
            <span>{parameter.title} · {parameter.unit}
              {typeof current === "number" ? <small className="mt-1 block text-muted">Actual {numeric.format(current)}</small> : null}
            </span>
            <input type="number" className={control} min={range.min} max={range.max} step={range.step}
              disabled={busy} value={inputs[tag]?.[field] ?? ""} placeholder={typeof current === "number" ? String(current) : undefined}
              onChange={event => onInput(tag, field, event.target.value)} />
          </label>;
        }) : <p className="text-xs text-muted">Conecta la API para generar un IFC con tus cotas.</p>}
        {apiEnabled ? <div className="flex flex-wrap gap-2">
          <Button type="submit" size="sm" variant="primary" disabled={!pending || busy}>
            {busy ? "Generando IFC…" : "Previsualizar borrador"}
          </Button>
          {pending || draft ? <Button type="button" size="sm" disabled={busy} onClick={onReset}>Descartar borrador</Button> : null}
        </div> : null}
      </form> : null}
    </div>}
    {draft || pending || error ? <div className="space-y-1 border-t border-border px-4 py-3 text-xs text-muted">
      {draft ? <Badge tone="warning">IFC DRAFT · Ensayo sintético</Badge> : null}
      {pending ? <p>{pending} {pending === 1 ? "parámetro introducido" : "parámetros introducidos"}</p> : null}
      {error ? <p role="alert" className="text-strong">{error}</p> : null}
    </div> : null}
  </Panel>;
}
