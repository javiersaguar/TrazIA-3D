"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import { FullscreenFrame } from "@/components/shell/fullscreen";
import type { Annotation, PlantEquipment } from "@/features/viewer3d/types";
import type { PerformanceSample } from "@/features/viewer3d/stage";

const IfcViewer = dynamic(() => import("@/features/viewer3d/ifc-viewer").then((m) => m.IfcViewer), { ssr: false });
const PlantScene = dynamic(() => import("@/features/plant/plant-scene").then((m) => m.PlantScene), { ssr: false });
const RevisionMorph = dynamic(() => import("@/features/delta3d/revision-morph").then((m) => m.RevisionMorph), { ssr: false });

const EQUIPMENT: PlantEquipment[] = [
  { tag: "V-101", ifcUrl: "/demo/ifc/rev_b.ifc", status: "changed" },
  { tag: "V-102", ifcUrl: "/demo/ifc/rev_a.ifc", status: "draft" },
  { tag: "V-103", ifcUrl: "/demo/ifc/rev_a.ifc", status: "review" },
  { tag: "V-201", ifcUrl: "/demo/ifc/rev_a.ifc", status: "approved" },
  { tag: "V-202", ifcUrl: "/demo/ifc/rev_a.ifc", status: "draft" },
  { tag: "V-301", ifcUrl: "/demo/ifc/rev_a.ifc", status: "approved" },
];
const ANNOTATIONS: Annotation[] = [
  { id: "height", label: "Longitud de virola", value: 6000, unit: "mm", confidence: 0.75 },
  { id: "diameter", label: "Diámetro", value: 2000, unit: "mm", confidence: 0.75 },
];

/*
  Laboratorio 3D: lo experimental que no está en Modelo. Visor con cotas sobre el modelo y medición de
  rendimiento, planta y comparación A → B a tamaño completo. El IFC del equipo, el holograma y la
  galería están en Modelo › Modelo 3D.
*/
export default function Lab3D() {
  const [changes, setChanges] = useState<unknown>(null);
  const [selected, setSelected] = useState("shell");
  const [plantSelected, setPlantSelected] = useState<string | null>(null);
  const [sample, setSample] = useState<PerformanceSample | null>(null);
  const [measureKey, setMeasureKey] = useState(0);
  const measure = () => {
    setSample(null);
    setMeasureKey((k) => k + 1);
  };
  useEffect(() => {
    const controller = new AbortController();
    void fetch("/demo/json/changes.json", { signal: controller.signal })
      .then((r) => r.json())
      .then(setChanges)
      .catch(() => {});
    return () => controller.abort();
  }, []);

  return (
    <div className="space-y-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-strong">Laboratorio 3D</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted">
            Pruebas del visor sobre IFC sintéticos: cotas sobre el modelo, rendimiento, planta por áreas y comparación de revisiones a
            tamaño completo. El modelo del equipo está en Modelo.
          </p>
        </div>
      </header>

      <FullscreenFrame
        title="Cotas y rendimiento del visor"
        description="Cotas trazables sobre el modelo, corte y vistas guardadas. El muestreo dura 5 s durante el giro y describe este navegador y esta máquina, no otros portátiles."
        height="h-[640px]"
        actions={
          <button className="h-8 rounded-[var(--radius-control)] border border-border px-3 text-[12px] text-muted hover:text-text" onClick={measure}>
            Medir visor durante 5 s
          </button>
        }
      >
        <IfcViewer
          ifcUrl="/demo/ifc/rev_a.ifc"
          selectedId={selected}
          onSelect={setSelected}
          annotations={selected === "shell" ? ANNOTATIONS : []}
          measureKey={measureKey}
          onMeasure={setSample}
          performanceSample={sample}
          onRequestMeasure={measure}
        />
      </FullscreenFrame>
      <div className="-mt-7 flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted">
        <p data-testid="selected-element">Selección: {selected}</p>
        <output className="block whitespace-pre-wrap font-mono" data-testid="performance-sample">
          {sample ? JSON.stringify(sample, null, 2) : "Sin medir"}
        </output>
      </div>

      <FullscreenFrame title="Revisiones A → B" description="Las piezas se emparejan por GlobalId entre los dos IFC sintéticos." height="h-[680px]">
        <RevisionMorph fromUrl="/demo/ifc/rev_a.ifc" toUrl="/demo/ifc/rev_b.ifc" changes={changes} />
      </FullscreenFrame>

      <FullscreenFrame title="Planta por áreas" description="Disposición ilustrativa; las repeticiones de equipos no proceden de planos." height="h-[680px]">
        <PlantScene equipment={EQUIPMENT} onSelect={setPlantSelected} />
      </FullscreenFrame>
      <p className="-mt-7 text-xs text-muted" data-testid="plant-selection">
        Equipo: {plantSelected ?? "sin selección"}
      </p>
    </div>
  );
}
