/*
  Contrato del 3D ilustrativo (docs/PLAN_FRONTEND.md, «Contratos entre agentes»).
  Dueño: Agente 2. Las firmas son fijas; solo se añaden props opcionales.
  Este archivo es un stub del paso 0: dibuja un hueco hasta que llegue la escena real.
  Se consume con next/dynamic({ ssr: false }).
*/

import { cn } from "@/lib/cn";

export type EquipmentKind = "vertical" | "horizontal" | "column" | "exchanger" | "tank";

export const EQUIPMENT_KINDS: EquipmentKind[] = ["vertical", "horizontal", "column", "exchanger", "tank"];

export type ShowcaseVesselProps = {
  kind?: EquipmentKind;
  mode?: "particles" | "hologram" | "real";
  interactive?: boolean;
  onKindChange?(kind: EquipmentKind): void;
  hud?: boolean;
  className?: string;
};

export type EquipmentThumbProps = { kind: EquipmentKind; size?: number };

export function ShowcaseVessel({ className }: ShowcaseVesselProps) {
  return (
    <div className={cn("drafting-grid flex h-full w-full items-center justify-center", className)}>
      <span className="font-mono text-[11px] text-faint">3D ilustrativo · pendiente</span>
    </div>
  );
}

export function EquipmentThumb({ size = 96 }: EquipmentThumbProps) {
  return <div className="drafting-grid rounded-[var(--radius-control)]" style={{ width: size, height: size }} aria-hidden="true" />;
}
