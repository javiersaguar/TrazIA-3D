"use client";

import { ArrowLeft, Download, FileSpreadsheet, FileText, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useState, useSyncExternalStore } from "react";
import { IfcViewer } from "@/components/three";
import { Badge, Button, Icon, Panel, PanelHeader } from "@/components/ui/primitives";
import type { ElementState } from "@/features/viewer3d/product-mesh";
import type { ProcessEnvironmentId } from "@/features/viewer3d/types";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { processAsset, type ProcessProject } from "./catalog";

const scenarios: Record<ProcessEnvironmentId, string> = {
  ocean: "Mar abierto", desert: "Desierto", coast: "Costa y muelle", industrial: "Complejo industrial",
};
const control = "h-9 rounded-[var(--radius-control)] border border-border bg-surface px-3 text-[13px] text-text";
const link = "inline-flex items-center gap-1 text-sm font-medium text-accent-text underline-offset-2 hover:underline";
const listen = (callback: () => void) => {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
};

export function ProcessProjectWorkspace({ project }: { project: ProcessProject }) {
  const key = `trazia:entorno:${project.id}`;
  const persisted = useSyncExternalStore(listen, () => {
    try { return window.localStorage.getItem(key); } catch { return null; }
  }, () => null);
  const [localScenario, setScenario] = useState<ProcessEnvironmentId>();
  const scenario = localScenario ?? (persisted && Object.hasOwn(scenarios, persisted) ? persisted as ProcessEnvironmentId : project.preset);
  function chooseScenario(next: ProcessEnvironmentId) {
    setScenario(next);
    try { window.localStorage.setItem(key, next); } catch { /* La selección sigue activa en esta vista. */ }
  }

  const [applied, setApplied] = useState<string[]>([]);
  const [selected, setSelected] = useState<string>();
  const [documentRevision, setDocumentRevision] = useState<"A" | "B">("A");
  const suffix = project.changes.map(change => applied.includes(change.tag) ? "1" : "0").join("");
  const revision = applied.length === 0 ? "A" : applied.length === project.changes.length ? "B" : null;
  const state = project.states[suffix]!;
  const url = processAsset(project, state.file);
  const docs = project.documents[revision ?? documentRevision];
  const elementStates: Record<string, ElementState> = Object.fromEntries(applied.map(tag => [`element:${tag}`, "changed"]));
  const selectedTag = selected?.replace(/^element:/, "");
  const info = project.equipment.find(item => item.tag === selectedTag);
  const route = project.lines.find(item => item.tag === selectedTag);

  function loadRevision(next: "A" | "B") {
    setDocumentRevision(next);
    setApplied(next === "B" ? project.changes.map(change => change.tag) : []);
    setSelected(undefined);
  }

  return <div className="space-y-5">
    <Link href="/documentos?vista=proyectos" className={link}><Icon icon={ArrowLeft} size={15} /> Proyectos</Link>
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-muted">{project.code}</span>
          <Badge tone="warning">Datos sintéticos</Badge>
        </div>
        <h1 className="text-2xl font-semibold text-strong">{project.name}</h1>
        <p className="text-sm text-muted">{project.description}</p>
      </div>
      <label className="grid gap-1 text-xs text-muted">Entorno del visor
        <select className={control} value={scenario} onChange={e => chooseScenario(e.target.value as ProcessEnvironmentId)}>
          {Object.entries(scenarios).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
    </header>

    <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
      <Panel className="overflow-hidden">
        <PanelHeader title="Modelo de planta"
          description={`${project.equipment.length} equipos · ${project.lines.length} líneas · ${formatNumber(state.triangles)} triángulos IFC`}
          actions={<a href={url} download className={link}><Icon icon={Download} size={15} /> Descargar IFC</a>} />
        <div className="h-[min(64vh,660px)] min-h-[350px] px-3 pb-3">
          <IfcViewer ifcUrl={url} scenario={scenario} holdPrevious selectedId={selected} onSelect={setSelected}
            elementStates={elementStates} />
        </div>
        <p className="min-h-9 px-4 pb-3 text-xs text-muted">
          {info ? `${info.tag} · ${info.name} · ${info.service}`
            : route ? `${route.tag} · ${route.fluid} · ${route.start} → ${route.end}`
              : "Selecciona un equipo o una tubería para consultar su tag y servicio."}
        </p>
      </Panel>

      <Panel className="space-y-4 p-4">
        <div className="flex items-start justify-between gap-2">
          <h2 className="font-semibold text-strong">Cambios por pieza</h2>
          <Badge tone={revision ? "neutral" : "warning"}>{revision ? `Rev. ${revision}` : "Ensayo parcial"}</Badge>
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Cargar revisión">
          <Button size="sm" aria-pressed={revision === "A"} onClick={() => loadRevision("A")}>Revisión A</Button>
          <Button size="sm" aria-pressed={revision === "B"} onClick={() => loadRevision("B")}>Revisión B</Button>
        </div>
        <div className="space-y-2">
          {project.changes.map(change => (
            <label key={change.tag} className={cn("flex cursor-pointer items-start gap-3 rounded-md border p-3",
              applied.includes(change.tag) ? "border-accent bg-accent-soft" : "border-border")}>
              <input type="checkbox" className="mt-1 accent-[var(--color-accent)]" checked={applied.includes(change.tag)}
                onChange={event => {
                  setSelected(`element:${change.tag}`);
                  setApplied(current => event.target.checked ? [...current, change.tag] : current.filter(tag => tag !== change.tag));
                }} />
              <span className="text-sm">
                <span className="block font-mono text-xs text-accent-text">{change.tag}</span>
                <span className="block font-medium">{change.label}</span>
                <span className="text-xs text-muted">{formatNumber(change.before)} → {formatNumber(change.after)} {change.unit}</span>
              </span>
            </label>
          ))}
        </div>
        {applied.length ? <Button size="sm" onClick={() => loadRevision("A")}><Icon icon={RotateCcw} size={14} /> Restablecer A</Button> : null}
        {!revision ? <p className="text-xs text-muted">El IFC descargado contiene solo los cambios seleccionados. Las hojas adjuntas corresponden a A o B.</p> : null}
      </Panel>
    </div>

    <Panel>
      <PanelHeader title="Planos y hojas de datos"
        description="Cada revisión tiene el GA de implantación y un plano y un Excel por equipo."
        actions={<label className="flex items-center gap-2 text-xs text-muted">Revisión documental
          <select className={control} value={revision ?? documentRevision}
            onChange={event => {
              const next = event.target.value as "A" | "B";
              if (revision) loadRevision(next);
              else setDocumentRevision(next);
            }}>
            <option value="A">A</option><option value="B">B</option>
          </select>
        </label>} />
      <div className="flex flex-wrap gap-4 px-5 pb-4">
        <a className={link} href={processAsset(project, docs.plan)} target="_blank" rel="noreferrer"><Icon icon={FileText} size={16} /> GA de implantación</a>
        <a className={link} href={processAsset(project, docs.workbook)} download><Icon icon={FileSpreadsheet} size={16} /> Excel de equipos, líneas y cambios</a>
        <a className={link} href={processAsset(project, docs.archive)} download><Icon icon={Download} size={16} /> Descargar dossier ZIP</a>
      </div>
      <div className="overflow-x-auto px-5 pb-4">
        <table className="w-full min-w-[565px] text-left text-sm">
          <thead><tr>{["Equipo", "Servicio", "Plano", "Datos"].map(column => <th key={column} className="py-2 pr-3 text-xs font-medium text-muted" scope="col">{column}</th>)}</tr></thead>
          <tbody>
            {project.equipment.map(item => {
              const files = docs.equipment[item.tag]!;
              return <tr key={item.tag} className={cn("border-t border-border", selectedTag === item.tag && "bg-accent-soft")}>
                <th scope="row" className="py-2 pr-3">
                  <button type="button" onClick={() => setSelected(`element:${item.tag}`)} className="text-left hover:underline">
                    <span className="mr-2 font-mono text-xs text-accent-text">{item.tag}</span>{item.name}
                  </button>
                </th>
                <td className="py-2 pr-3 text-muted">{item.service}</td>
                <td className="py-2 pr-3"><a className={link} href={processAsset(project, files.plan)} target="_blank" rel="noreferrer" aria-label={`PDF de ${item.tag}`}>PDF</a></td>
                <td className="py-2"><a className={link} href={processAsset(project, files.workbook)} download aria-label={`XLSX de ${item.tag}`}>XLSX</a></td>
              </tr>;
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  </div>;
}
