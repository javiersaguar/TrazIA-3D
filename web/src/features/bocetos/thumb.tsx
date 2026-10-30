"use client";

import { Cog } from "lucide-react";
import dynamic from "next/dynamic";

import { Icon } from "@/components/ui/primitives";
import type { EquipmentKind } from "@/features/showcase3d";

// Miniatura 3D ilustrativa del Agente 2 (contrato EquipmentThumb), sin three en el SSR
const EquipmentThumb = dynamic(() => import("@/features/showcase3d").then((m) => m.EquipmentThumb), {
  ssr: false,
  loading: () => <div className="size-full" aria-hidden />,
});

/** Miniatura de una familia. La bomba aún no tiene modelo ilustrativo: se muestra su icono. */
export function FamilyThumb({ kind, size = 96 }: { kind: EquipmentKind | "pump"; size?: number }) {
  if (kind === "pump") {
    return (
      <div className="drafting-grid flex items-center justify-center rounded-[var(--radius-control)] text-faint" style={{ width: size, height: size }} aria-hidden>
        <Icon icon={Cog} size={Math.round(size / 3)} />
      </div>
    );
  }
  return (
    <div style={{ width: size, height: size }}>
      <EquipmentThumb kind={kind} size={size} />
    </div>
  );
}
