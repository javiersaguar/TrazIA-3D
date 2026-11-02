"use client";

import { Box, Cog, Shapes, type LucideIcon } from "lucide-react";
import dynamic from "next/dynamic";

import { Icon } from "@/components/ui/primitives";
import type { EquipmentKind } from "@/features/showcase3d";

// Miniatura 3D ilustrativa del Agente 2 (contrato EquipmentThumb), sin three en el SSR
const EquipmentThumb = dynamic(() => import("@/features/showcase3d").then((m) => m.EquipmentThumb), {
  ssr: false,
  loading: () => <div className="size-full" aria-hidden />,
});

const MODELLED: EquipmentKind[] = ["vertical", "horizontal", "column", "exchanger", "tank"];
const FALLBACK: Record<string, LucideIcon> = { pump: Cog, compressor: Cog, generic: Box };

/** Miniatura de una familia. Las que aún no tienen modelo ilustrativo muestran un icono. */
export function FamilyThumb({ kind, size = 96 }: { kind: string; size?: number }) {
  if (!MODELLED.includes(kind as EquipmentKind)) {
    return (
      <div
        className="drafting-grid flex shrink-0 items-center justify-center rounded-[var(--radius-control)] text-faint"
        style={{ width: size, height: size }}
        aria-hidden
      >
        <Icon icon={FALLBACK[kind] ?? Shapes} size={Math.round(size / 3)} />
      </div>
    );
  }
  return (
    <div className="shrink-0" style={{ width: size, height: size }}>
      <EquipmentThumb kind={kind as EquipmentKind} size={size} />
    </div>
  );
}
