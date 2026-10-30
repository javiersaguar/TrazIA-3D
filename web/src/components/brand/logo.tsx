import { useId, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { FULL_VIEWBOX, LOGO_FACES, MARK_VIEWBOX, WORD_VIEWBOX, type LogoFace } from "./logo-geometry";

export const MARK_FACES = LOGO_FACES.filter((f) => !f.role.startsWith("w-"));
export const WORD_FACES = LOGO_FACES.filter((f) => f.role.startsWith("w-"));

/** Color de una parada de tinta: mezcla entre --logo-ink-lo y --logo-ink-hi según el tono del original. */
export function inkStop(tone: number): string {
  const pct = Math.round(tone * 100);
  return `color-mix(in oklab, var(--logo-ink-hi) ${pct}%, var(--logo-ink-lo))`;
}

/** Degradados de las caras, con ids únicos por instancia. */
export function FaceGradients({ faces, uid }: { faces: LogoFace[]; uid: string }) {
  return (
    <defs>
      {faces.map((f, i) =>
        f.g ? (
          <linearGradient key={i} id={`${uid}-${i}`} gradientUnits="userSpaceOnUse" x1={f.g[0]} y1={f.g[1]} x2={f.g[2]} y2={f.g[3]}>
            <stop offset="0" style={{ stopColor: f.ink ? inkStop(f.ink[0]) : f.stops![0] }} />
            <stop offset="1" style={{ stopColor: f.ink ? inkStop(f.ink[1]) : f.stops![1] }} />
          </linearGradient>
        ) : null,
      )}
    </defs>
  );
}

export function faceFill(f: LogoFace, uid: string, i: number): string {
  if (f.fill === "word") return "var(--logo-word)";
  if (f.fill === "sky") return "var(--logo-sky)";
  return `url(#${uid}-${i})`;
}

function LogoSvg({ faces, viewBox, title, className, children }: { faces: LogoFace[]; viewBox: string; title?: string; className?: string; children?: ReactNode }) {
  const uid = `lg${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  return (
    <svg viewBox={viewBox} className={className} role={title ? "img" : undefined} aria-label={title} aria-hidden={title ? undefined : true}>
      <FaceGradients faces={faces} uid={uid} />
      {faces.map((f, i) => (
        <path key={i} d={f.d} fill={faceFill(f, uid, i)} fillRule="evenodd" />
      ))}
      {children}
    </svg>
  );
}

/** Solo la marca isométrica (T + D). */
export function LogoMark({ className, title }: { className?: string; title?: string }) {
  return <LogoSvg faces={MARK_FACES} viewBox={MARK_VIEWBOX} title={title} className={cn("block shrink-0", className)} />;
}

/** Solo el wordmark «TrazIA 3D». */
export function LogoWordmark({ className, title }: { className?: string; title?: string }) {
  return <LogoSvg faces={WORD_FACES} viewBox={WORD_VIEWBOX} title={title} className={cn("block", className)} />;
}

/** Logo completo apilado, como el original. */
export function Logo({ className, title = "TrazIA 3D" }: { className?: string; title?: string }) {
  return <LogoSvg faces={LOGO_FACES} viewBox={FULL_VIEWBOX} title={title} className={cn("block", className)} />;
}
