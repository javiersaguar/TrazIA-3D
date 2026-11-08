"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useState } from "react";

import { IfcViewer } from "@/components/three";
import { FullscreenFrame } from "@/components/shell/fullscreen";
import { Segmented } from "@/components/ui/controls";
import { DEMO } from "@/lib/mock/api";
import { useSelection } from "@/stores/selection";
import { useUi } from "@/stores/ui";
import type { EquipmentKind } from "../showcase3d/equipment-geometry";

const HologramToReal = dynamic(() => import("@/features/hologram").then((m) => m.HologramToReal), { ssr: false });
const ShowcaseVessel = dynamic(() => import("@/features/showcase3d").then((m) => m.ShowcaseVessel), { ssr: false });
const EquipmentThumb = dynamic(() => import("@/features/showcase3d").then((m) => m.EquipmentThumb), { ssr: false });

const KINDS: { kind: EquipmentKind; label: string }[] = [
  { kind: "vertical", label: "Recipiente vertical" },
  { kind: "horizontal", label: "Horizontal con silletas" },
  { kind: "column", label: "Columna" },
  { kind: "exchanger", label: "Intercambiador" },
  { kind: "tank", label: "Tanque" },
];

/** Pestaña Modelo 3D: el IFC del equipo, su materialización y la galería ilustrativa. */
export function ModelWorkspace() {
  const revision = useUi((s) => s.revision);
  const setRevision = useUi((s) => s.setRevision);
  const selected = useSelection((s) => s.selectedId);
  const select = useSelection((s) => s.setSelected);
  const [layout, setLayout] = useState<"side" | "inplace">("side");
  const [kind, setKind] = useState<EquipmentKind>("vertical");

  return (
    <div className="space-y-10" data-testid="model-workspace">
      <FullscreenFrame
        title="IFC generado"
        description="La geometría procede del IFC. Selecciona una pieza para consultar sus propiedades; la selección se mantiene al volver a Revisión."
        height="h-[min(75vh,800px)] min-h-[480px]"
        actions={
          <>
            <span className="text-[12px] text-warning">Datos sintéticos · V-101 · IFC DRAFT</span>
            <Link href="/modelo?vista=editar" className="rounded-[var(--radius-control)] border border-border px-2.5 py-1 text-xs hover:bg-surface-sunken">
              {selected?.startsWith("nozzle:") ? `Proponer cambios en ${selected.slice(7)}` : "Proponer cambios"}
            </Link>
            <Segmented
              label="Revisión del modelo"
              value={revision}
              onChange={setRevision}
              options={[
                { value: "A", label: "Rev A" },
                { value: "B", label: "Rev B" },
              ]}
            />
          </>
        }
      >
        <IfcViewer ifcUrl={DEMO.revisions[revision].ifc} selectedId={selected ?? undefined} onSelect={select} />
      </FullscreenFrame>

      <FullscreenFrame
        title="Del holograma al modelo"
        description="El holograma y el acero comparten la geometría leída del IFC. El barrido explica la transición; no añade piezas al archivo."
        height="h-[650px]"
        testId="model-hologram"
        actions={
          <Segmented<"side" | "inplace">
            label="Disposición de la transición"
            value={layout}
            onChange={setLayout}
            options={[
              { value: "side", label: "Lado a lado" },
              { value: "inplace", label: "Sobre el modelo" },
            ]}
          />
        }
      >
        <HologramToReal source="ifc" layout={layout} />
      </FullscreenFrame>

      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-strong">Familias ilustrativas</h2>
          <p className="mt-1 text-sm text-muted">Modelos paramétricos para explorar formas. No proceden del IFC ni de planos reales.</p>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
          {KINDS.map((item) => (
            <button
              key={item.kind}
              onClick={() => setKind(item.kind)}
              aria-pressed={kind === item.kind}
              aria-label={`Explorar ${item.label}`}
              className="flex items-center gap-3 rounded-xl border border-border bg-surface p-3 text-left text-xs aria-pressed:border-accent aria-pressed:text-accent-text"
            >
              <EquipmentThumb kind={item.kind} size={76} />
              <span>{item.label}</span>
            </button>
          ))}
        </div>
        <FullscreenFrame height="h-[550px]">
          <ShowcaseVessel kind={kind} mode="real" onKindChange={setKind} />
        </FullscreenFrame>
      </section>
    </div>
  );
}
