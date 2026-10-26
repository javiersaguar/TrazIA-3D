"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import type { Annotation, PlantEquipment } from "@/features/viewer3d/types";
import type { PerformanceSample } from "@/features/viewer3d/stage";

const IfcViewer = dynamic(() => import("@/features/viewer3d/ifc-viewer").then(m => m.IfcViewer), { ssr: false });
const PlantScene = dynamic(() => import("@/features/plant/plant-scene").then(m => m.PlantScene), { ssr: false });
const RevisionMorph = dynamic(() => import("@/features/delta3d/revision-morph").then(m => m.RevisionMorph), { ssr: false });
const EQUIPMENT: PlantEquipment[] = [
  { tag: "V-101", ifcUrl: "/demo/ifc/rev_b.ifc", status: "changed" },
  { tag: "V-102", ifcUrl: "/demo/ifc/rev_a.ifc", status: "draft" },
  { tag: "V-103", ifcUrl: "/demo/ifc/rev_a.ifc", status: "review" },
  { tag: "V-201", ifcUrl: "/demo/ifc/rev_a.ifc", status: "approved" },
  { tag: "V-202", ifcUrl: "/demo/ifc/rev_a.ifc", status: "draft" },
  { tag: "V-301", ifcUrl: "/demo/ifc/rev_a.ifc", status: "approved" },
];
const ANNOTATIONS: Annotation[] = [
  { id: "height", label: "Longitud de virola", value: 6000, unit: "mm", confidence: .75 },
  { id: "diameter", label: "Diámetro", value: 2000, unit: "mm", confidence: .75 },
];

export default function Lab3D() {
  const [changes, setChanges] = useState<unknown>(null), [selected, setSelected] = useState("shell");
  const [plantSelected, setPlantSelected] = useState<string | null>(null);
  const [sample, setSample] = useState<PerformanceSample | null>(null), [measureKey, setMeasureKey] = useState(0);
  const { theme, setTheme } = useTheme();
  useEffect(() => { const controller = new AbortController(); void fetch("/demo/json/changes.json", { signal: controller.signal })
    .then(r => r.json()).then(setChanges).catch(() => {}); return () => controller.abort(); }, []);
  return <main className="mx-auto max-w-[1600px] space-y-6 p-6">
    <header className="flex flex-wrap items-center justify-between gap-4">
      <div><h1 className="text-2xl font-semibold">Laboratorio 3D / TrazIA</h1>
        <p className="mt-2 text-sm text-muted">Mallas leídas de IFC sintéticos; planta ilustrativa y revisiones con GUID estables.</p></div>
      <nav className="flex gap-4 text-sm text-accent-text"><Link href="/proyecto">Proyecto</Link><Link href="/revision">Revisión</Link><Link href="/lab/firma">Plano → modelo</Link>
        <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>Cambiar tema</button></nav>
    </header>
    <section className="grid gap-5 xl:grid-cols-[1.1fr_1fr]">
      <div><h2 className="mb-3 text-lg font-semibold">Visor IFC</h2><div className="h-[680px]">
        <IfcViewer ifcUrl="/demo/ifc/rev_a.ifc" selectedId={selected} onSelect={setSelected} annotations={selected === "shell" ? ANNOTATIONS : []}
          measureKey={measureKey} onMeasure={setSample} /></div>
        <p className="mt-2 text-xs text-muted" data-testid="selected-element">Selección: {selected}</p>
      </div>
      <div><h2 className="mb-3 text-lg font-semibold">Revisiones A → B</h2><div className="h-[680px]">
        <RevisionMorph fromUrl="/demo/ifc/rev_a.ifc" toUrl="/demo/ifc/rev_b.ifc" changes={changes} />
      </div></div>
    </section>
    <section><h2 className="mb-3 text-lg font-semibold">Planta por áreas</h2><div className="h-[620px]">
      <PlantScene equipment={EQUIPMENT} onSelect={setPlantSelected} />
    </div><p className="mt-2 text-xs text-muted" data-testid="plant-selection">Equipo: {plantSelected ?? "sin selección"}</p></section>
    <section className="rounded-xl border border-border bg-surface p-5">
      <h2 className="text-lg font-semibold">Medición local</h2><p className="mt-2 text-sm text-muted">Muestreo de 5 s durante el giro. Describe este navegador y esta máquina, no otros portátiles.</p>
      <button className="mt-3 rounded-lg border border-border px-4 py-2 text-sm" onClick={() => { setSample(null); setMeasureKey(k => k + 1); }}>Medir visor durante 5 s</button>
      <output className="mt-3 block whitespace-pre-wrap font-mono text-xs text-muted" data-testid="performance-sample">{sample ? JSON.stringify(sample, null, 2) : "Sin medir"}</output>
    </section>
  </main>;
}
