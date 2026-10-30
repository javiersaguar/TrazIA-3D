"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useState } from "react";
import type { EquipmentKind } from "../showcase3d/equipment-geometry";

const HologramToReal = dynamic(() => import("@/features/hologram").then(m => m.HologramToReal), { ssr: false });
const ShowcaseVessel = dynamic(() => import("@/features/showcase3d").then(m => m.ShowcaseVessel), { ssr: false });
const EquipmentThumb = dynamic(() => import("@/features/showcase3d").then(m => m.EquipmentThumb), { ssr: false });
const kinds: { kind: EquipmentKind; label: string }[] = [
  {kind:"vertical",label:"Recipiente vertical"},{kind:"horizontal",label:"Horizontal con silletas"},
  {kind:"column",label:"Columna"},{kind:"exchanger",label:"Intercambiador"},{kind:"tank",label:"Tanque"},
];
export function ModelWorkspace() {
  const [layout, setLayout] = useState<"side" | "inplace">("side");
  const [kind, setKind] = useState<EquipmentKind>("vertical");
  return <div className="space-y-6" data-testid="model-workspace">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-2xl font-semibold">Modelo 3D</h1>
      <p className="mt-2 max-w-3xl text-sm text-muted">El holograma y el acero comparten la geometría leída del IFC. El barrido explica la transición; no añade piezas al archivo.</p></div>
      <Link className="rounded-lg border border-border px-4 py-2 text-sm text-accent-text" href="/revision">Abrir en Revisión</Link></header>
    <div className="flex flex-wrap items-center justify-between gap-3"><span className="font-mono text-xs text-warning">Datos sintéticos · rev B · IFC DRAFT</span>
      <div role="group" aria-label="Disposición de la transición" className="flex gap-2">
        <button className="rounded-lg border border-border px-3 py-2 text-xs" aria-pressed={layout === "side"} onClick={() => setLayout("side")}>Lado a lado</button>
        <button className="rounded-lg border border-border px-3 py-2 text-xs" aria-pressed={layout === "inplace"} onClick={() => setLayout("inplace")}>Sobre el modelo</button></div></div>
    <section className="h-[650px] overflow-hidden rounded-xl border border-border" aria-label="Materialización del IFC"><HologramToReal source="ifc" layout={layout} /></section>
    <section className="space-y-4"><div><h2 className="text-lg font-semibold">Familias ilustrativas</h2><p className="mt-1 text-sm text-muted">Modelos paramétricos para explorar formas. No proceden del IFC ni de planos reales.</p></div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">{kinds.map(item => <button key={item.kind} onClick={() => setKind(item.kind)} aria-pressed={kind === item.kind} aria-label={`Explorar ${item.label}`}
        className="flex items-center gap-3 rounded-xl border border-border bg-surface p-3 text-left text-xs"><EquipmentThumb kind={item.kind} size={76} /><span>{item.label}</span></button>)}</div>
      <div className="h-[550px] overflow-hidden rounded-xl border border-border"><ShowcaseVessel kind={kind} mode="real" onKindChange={setKind} /></div>
    </section>
  </div>;
}
