"use client";
import dynamic from "next/dynamic";
import { useState } from "react";
import type { PerformanceSample } from "@/features/viewer3d/stage";
const HologramToReal = dynamic(
  () => import("@/features/hologram").then((m) => m.HologramToReal),
  { ssr: false },
);
export default function HologramLab() {
  const [source, setSource] = useState<"procedural" | "ifc">("procedural");
  const [sample, setSample] = useState<PerformanceSample | null>(null),
    [measureKey, setMeasureKey] = useState(0);
  const [layout, setLayout] = useState<"side" | "inplace">("side");
  return (
    <main className="mx-auto max-w-[1600px] space-y-4 p-6">
      <h1 className="text-2xl font-semibold">Holograma y materialización</h1>
      <div className="flex gap-3">
        {(["procedural", "ifc"] as const).map((v) => (
          <button
            className="rounded-lg border border-border px-4 py-2"
            key={v}
            onClick={() => setSource(v)}
          >
            {v}
          </button>
        ))}
        <button
          className="rounded-lg border border-border px-4 py-2"
          onClick={() => setLayout((v) => (v === "side" ? "inplace" : "side"))}
        >
          Cambiar disposición
        </button>
        <button
          className="rounded-lg border border-border px-4 py-2"
          onClick={() => {
            setSample(null);
            setMeasureKey((v) => v + 1);
          }}
        >
          Medir 5 s
        </button>
      </div>
      <div className="h-[780px] rounded-xl border border-border">
        <HologramToReal
          source={source}
          layout={layout}
          measureKey={measureKey}
          onMeasure={setSample}
        />
      </div>
      <output
        data-testid="hologram-performance"
        className="block whitespace-pre-wrap font-mono text-xs"
      >
        {sample ? JSON.stringify(sample) : "Sin medir"}
      </output>
    </main>
  );
}
