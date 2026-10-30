"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import type { EquipmentKind } from "@/features/showcase3d/equipment-geometry";
import type { PerformanceSample } from "@/features/viewer3d/stage";

const ShowcaseVessel = dynamic(() => import("@/features/showcase3d").then(m => m.ShowcaseVessel), { ssr: false });
const EquipmentThumb = dynamic(() => import("@/features/showcase3d").then(m => m.EquipmentThumb), { ssr: false });
const kinds: EquipmentKind[] = ["vertical", "horizontal", "column", "exchanger", "tank"];

export default function ShowcaseLab() {
  const [mode, setMode] = useState<"real" | "particles" | "hologram">("real");
  const [kind, setKind] = useState<EquipmentKind>("vertical");
  const [measure, setMeasure] = useState(0), [sample, setSample] = useState<PerformanceSample | null>(null);
  return <main className="mx-auto max-w-[1500px] space-y-5 p-6">
    <header><h1 className="text-2xl font-semibold">Modelos ilustrativos</h1><p className="mt-2 text-sm text-muted">Geometría paramétrica independiente del IFC. No representa datos extraídos de planos.</p></header>
    <div className="flex flex-wrap gap-3">{(["real", "particles", "hologram"] as const).map(item => <button key={item} onClick={() => setMode(item)} aria-pressed={item === mode} className="rounded-lg border border-border px-4 py-2 text-sm">{item}</button>)}
      <button className="rounded-lg border border-border px-4 py-2 text-sm" onClick={() => { setSample(null); setMeasure(n => n + 1); }}>Medir 5 s</button></div>
    <div className="h-[690px] overflow-hidden rounded-xl border border-border"><ShowcaseVessel kind={kind} mode={mode} onKindChange={setKind} measureKey={measure} onMeasure={setSample} /></div>
    <div className="flex flex-wrap gap-5">{kinds.map(item => <button key={item} aria-label={`Miniatura ${item}`} onClick={() => setKind(item)} className="rounded-xl border border-border p-2"><EquipmentThumb kind={item} size={104} /></button>)}</div>
    <output data-testid="performance-sample" className="block whitespace-pre-wrap font-mono text-xs text-muted">{sample ? JSON.stringify(sample, null, 2) : "Sin medir"}</output>
  </main>;
}
