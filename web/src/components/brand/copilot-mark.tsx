import { useId } from "react";
import { cn } from "@/lib/cn";

/**
 * Marca del copiloto: un bocadillo con el perfil achaflanado de la D del logo y dos «ojos».
 * Hereda el tamaño de la caja; el color sale del celeste de marca.
 */
export function CopilotMark({ className }: { className?: string }) {
  const id = `cm${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  return (
    <svg viewBox="0 0 24 24" className={cn("block", className)} aria-hidden="true" fill="none">
      <defs>
        <linearGradient id={id} x1="4" y1="3" x2="20" y2="21" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#95ddfc" />
          <stop offset="0.55" stopColor="#2aa8f2" />
          <stop offset="1" stopColor="#0b6fb8" />
        </linearGradient>
      </defs>
      {/* Bocadillo: lado izquierdo recto, derecho achaflanado como la D, cola abajo a la izquierda */}
      <path
        d="M5 4.5h8.6l5.4 4.4v6.2l-5.4 4.4H9.4L5.6 22v-2.5H5a1 1 0 0 1-1-1V5.5a1 1 0 0 1 1-1Z"
        stroke={`url(#${id})`}
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <rect x="8.6" y="10" width="2" height="3.4" rx="1" fill={`url(#${id})`} />
      <rect x="13" y="10" width="2" height="3.4" rx="1" fill={`url(#${id})`} />
    </svg>
  );
}
