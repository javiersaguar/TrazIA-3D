"use client";

import { useId, type CSSProperties } from "react";

import styles from "./intro-assembly.module.css";
import { cn } from "@/lib/cn";
import { FaceGradients, MARK_FACES, WORD_FACES, faceFill } from "./logo";
import { MARK_VIEWBOX, WORD_VIEWBOX, type LogoRole } from "./logo-geometry";

/*
  Formación del logo como un plano de montaje en vista explosionada:
  1. cada cara parte separada del centro de la marca y su arista se dibuja mientras encaja;
  2. las caras se rellenan con su degradado y un brillo recorre la marca;
  3. las letras de «TrazIA» suben escalonadas y «3D» se enciende un instante.
  Duración total ≈ 2,4 s. Con movimiento reducido no se monta: se usa el logo estático.
*/

/** Duración de la formación, en segundos, para que el contenedor sepa cuándo terminar. */
export const LOGO_ASSEMBLE_SECONDS = 2.4;

// Centro de la marca en coordenadas del PNG original.
const CENTER = { x: 632.5, y: 562.5 };

// Orden de montaje: fuste y barra de la T, sus remates, la D y por último la flecha interior.
const ORDER: Partial<Record<LogoRole, number>> = { "t-front": 0, "t-top": 1, "t-end": 2, "t-inner": 2, "d-outer": 3, "d-arrow": 4 };

function centroid(d: string) {
  const n = (d.match(/-?\d+(?:\.\d+)?/g) ?? []).map(Number);
  let x = 0;
  let y = 0;
  let k = 0;
  for (let i = 0; i + 1 < n.length; i += 2) {
    x += n[i]!;
    y += n[i + 1]!;
    k++;
  }
  return k ? { x: x / k, y: y / k } : CENTER;
}

const MARK_PARTS = MARK_FACES.map((f, i) => {
  const c = centroid(f.d);
  const order = ORDER[f.role] ?? 0;
  const sameRoleBefore = MARK_FACES.slice(0, i).filter((g) => g.role === f.role).length;
  return {
    f,
    i,
    // Separación radial (vista explosionada) con un leve levantamiento
    dx: (c.x - CENTER.x) * 0.5,
    dy: (c.y - CENTER.y) * 0.5 - 26,
    t0: 0.08 + order * 0.075 + sameRoleBefore * 0.04,
    ink: f.role.startsWith("t-"),
  };
});

// Letras ordenadas de izquierda a derecha para el escalonado.
const WORD_PARTS = WORD_FACES.map((f, i) => ({ f, i, x: centroid(f.d).x })).sort((a, b) => a.x - b.x);

const WORD_START = 1.05;

function AssembledMark() {
  const uid = `la${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  return (
    <svg viewBox={MARK_VIEWBOX} className="block h-auto w-full overflow-visible" aria-hidden>
      <FaceGradients faces={MARK_FACES} uid={uid} />
      <defs>
        <clipPath id={`${uid}-clip`}>
          {MARK_FACES.map((f, i) => (
            <path key={i} d={f.d} />
          ))}
        </clipPath>
        <linearGradient id={`${uid}-sheen`} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="#fff" stopOpacity="0" />
          <stop offset="0.5" stopColor="#fff" stopOpacity="0.38" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
      </defs>

      {MARK_PARTS.map(({ f, i, dx, dy, t0, ink }) => (
        <path
          key={i}
          d={f.d}
          fill={faceFill(f, uid, i)}
          fillRule="evenodd"
          stroke={ink ? "var(--logo-ink-hi)" : "var(--logo-sky)"}
          strokeWidth={1.25}
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
          pathLength={1}
          className={styles.face}
          style={{"--dx":`${dx}px`, "--dy":`${dy}px`, "--draw-delay":`${t0}s`,
            "--move-delay":`${t0+.1}s`, "--fill-delay":`${.72+t0*.6}s`} as CSSProperties}
        />
      ))}

      {/* Brillo que recorre la marca al quedar montada */}
      <g clipPath={`url(#${uid}-clip)`}>
        <rect
          y={230}
          width={180}
          height={665}
          fill={`url(#${uid}-sheen)`}
          className={styles.sheen}
        />
      </g>
    </svg>
  );
}

function AssembledWordmark() {
  const uid = `lw${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  return (
    <div className={cn("relative h-full", styles.word)}>
      {/* Brillo breve detrás de «3D» */}
      <span aria-hidden className={cn("pointer-events-none absolute inset-y-[-60%] right-[-6%] left-[66%] rounded-full blur-2xl",styles.glow)}
        style={{background:"radial-gradient(closest-side, var(--logo-sky), transparent)"}}
      />
      <svg viewBox={WORD_VIEWBOX} className="relative block h-full w-auto overflow-visible" aria-hidden>
        {WORD_PARTS.map(({ f, i }, k) => (
          <path
            key={i}
            d={f.d}
            fill={faceFill(f, uid, i)}
            fillRule="evenodd"
            className={styles.letter}
            style={{"--letter-delay":`${WORD_START+k*.05}s`} as CSSProperties}
          />
        ))}
      </svg>
    </div>
  );
}

/**
 * Animación de formación del logo. Las dos capas del viaje se identifican sin
 * montar copias ni ejecutar la proyección de layout de toda la portada.
 */
export function LogoAssemble({ className }: { className?: string }) {
  return <div className={cn("flex flex-col items-center",className)}>
    <div data-intro-logo-part="mark" className={cn("w-[clamp(128px,22vw,200px)]",styles.layer)}><AssembledMark /></div>
    <div data-intro-logo-part="word" className={cn("mt-9 h-[clamp(26px,4.4vw,40px)]",styles.layer)}><AssembledWordmark /></div>
  </div>;
}
