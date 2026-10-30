/*
  Contrato de la transición holograma → modelo real (docs/PLAN_FRONTEND.md, «Contratos entre agentes»).
  Dueño: Agente 2. Las firmas son fijas; solo se añaden props opcionales.
  Este archivo es un stub del paso 0: dibuja un hueco hasta que llegue la escena real.
  Se consume con next/dynamic({ ssr: false }).
*/

import { cn } from "@/lib/cn";

export type HologramToRealProps = {
  /** "ifc" lee la geometría del IFC generado; "procedural" usa los modelos ilustrativos. */
  source: "procedural" | "ifc";
  layout?: "side" | "inplace";
  /** 0–1 controlado desde fuera (scroll); sin él, autoplay. */
  progress?: number;
  autoplay?: boolean;
  callouts?: boolean;
  className?: string;
};

export function HologramToReal({ className }: HologramToRealProps) {
  return (
    <div className={cn("drafting-grid flex h-full w-full items-center justify-center", className)}>
      <span className="font-mono text-[11px] text-faint">Holograma → modelo · pendiente</span>
    </div>
  );
}
