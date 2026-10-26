"use client";

/*
  STUB inicial creado por la estructura base. Esta carpeta es del responsable del 3D:
  sustituir estos componentes por la implementación real manteniendo los props de ./types.ts.
  Correspondencia de ids semánticos ↔ IFC: ver src/lib/mock/fields.ts.
*/
import type { IfcViewerProps, PlantSceneProps, RevisionMorphProps } from "./types";

function Frame({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div
      className="drafting-grid relative flex h-full min-h-[240px] w-full items-center justify-center overflow-hidden rounded-[var(--radius-card)]"
      role="img"
      aria-label={label}
    >
      {children}
      <div className="skeleton pointer-events-none absolute inset-x-6 bottom-5 h-1.5 opacity-70" />
      <p className="absolute left-4 top-3 text-xs text-muted">{label}</p>
    </div>
  );
}

function VesselOutline({ className, dashed = false }: { className?: string; dashed?: boolean }) {
  return (
    <svg viewBox="0 0 120 260" className={className} fill="none" aria-hidden>
      <g stroke="currentColor" strokeWidth="1.5" strokeDasharray={dashed ? "4 4" : undefined}>
        <path d="M20 60 Q20 20 60 20 Q100 20 100 60 V190 Q100 230 60 230 Q20 230 20 190 Z" />
        <path d="M30 222 V252 H90 V222" />
        <path d="M100 95 H116 M100 150 H116 M4 120 H20" />
        <path d="M60 20 V6" />
      </g>
    </svg>
  );
}

export function IfcViewer({ ifcUrl }: IfcViewerProps) {
  const file = ifcUrl.split("/").at(-1);
  return (
    <Frame label={`Visor 3D en preparación · ${file}`}>
      <VesselOutline className="h-[60%] max-h-72 text-accent/50" />
    </Frame>
  );
}

export function PlantScene({ equipment }: PlantSceneProps) {
  return (
    <Frame label={`Escena de planta en preparación · ${equipment.length} equipos`}>
      <div className="flex items-end gap-6">
        {equipment.slice(0, 6).map((e, i) => (
          <VesselOutline key={e.tag} className="text-accent/40" dashed={i % 2 === 1} />
        ))}
      </div>
    </Frame>
  );
}

export function RevisionMorph({ fromUrl, toUrl }: RevisionMorphProps) {
  const a = fromUrl.split("/").at(-1);
  const b = toUrl.split("/").at(-1);
  return (
    <Frame label={`Comparación 3D en preparación · ${a} → ${b}`}>
      <div className="relative h-[60%] max-h-72">
        <VesselOutline className="absolute h-full text-accent/35" dashed />
        <VesselOutline className="relative h-full translate-x-3 text-revision/60" />
      </div>
    </Frame>
  );
}
