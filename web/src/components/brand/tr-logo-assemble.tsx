"use client";

import { useId, type CSSProperties } from "react";

import styles from "./intro-assembly.module.css";
import { cn } from "@/lib/cn";
import { TR_MARK_BOX, TR_MARK_PIECES, TR_VIEWBOX, TR_WORD_LETTERS } from "./tr-logo-geometry";

/*
  Formación del logo de Técnicas Reunidas, al compás de la de TrazIA (≈ 2,4 s):
  1. se dibuja el contorno de la «tr», como un trazo a mano alzada;
  2. se rellena, se apaga el contorno y un brillo recorre la marca;
  3. «TECNICAS REUNIDAS» sube letra a letra a la vez que «TrazIA».
  Va en un solo color (--logo-ink-hi): claro sobre la portada oscura, grafito en tema claro.
*/

const WORD_START = 1.05;
const [MX, MY, MW, MH] = TR_MARK_BOX;

export function TrLogoAssemble({ className }: { className?: string }) {
  const uid = `tr${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  return (
    <svg viewBox={TR_VIEWBOX} className={cn("block h-auto w-full overflow-visible", className)} aria-hidden>
      <defs>
        <clipPath id={`${uid}-clip`}>
          {TR_MARK_PIECES.map((d, i) => (
            <path key={i} d={d} />
          ))}
        </clipPath>
        <linearGradient id={`${uid}-sheen`} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="var(--logo-sky)" stopOpacity="0" />
          <stop offset="0.5" stopColor="var(--logo-sky)" stopOpacity="0.55" />
          <stop offset="1" stopColor="var(--logo-sky)" stopOpacity="0" />
        </linearGradient>
      </defs>

      <g className={styles.trMark}>
        {TR_MARK_PIECES.map((d, i) => (
          <path
            key={i}
            d={d}
            fill="var(--logo-ink-hi)"
            fillRule="evenodd"
            stroke="var(--logo-ink-hi)"
            strokeWidth={1.25}
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
            pathLength={1} className={styles.trFace}
            style={{"--edge-duration":`${i ? .55 : .8}s`,"--draw-delay":`${i ? .42 : .12}s`,"--fill-delay":`${.82+i*.08}s`} as CSSProperties}
          />
        ))}
      </g>

      {/* Brillo celeste que recorre la marca al quedar formada */}
      <g clipPath={`url(#${uid}-clip)`}>
        <rect
          y={MY}
          width={MW * 0.45}
          height={MH}
          fill={`url(#${uid}-sheen)`}
          className={styles.trSheen}
          style={{"--sheen-from":`${MX-MW*.5}px`,"--sheen-to":`${MX+MW}px`} as CSSProperties}
        />
      </g>

      {TR_WORD_LETTERS.map((d, k) => (
        <path
          key={k}
          d={d}
          fill="var(--logo-ink-hi)"
          fillRule="evenodd"
          className={styles.letter}
          style={{"--letter-y":"14px","--letter-delay":`${WORD_START+k*.03}s`} as CSSProperties}
        />
      ))}
    </svg>
  );
}

/**
 * «×» de colaboración: dos trazos celestes que se dibujan mientras el aspa gira hasta su sitio,
 * y un destello breve cuando ambos logos ya están formados.
 */
export function CollabCross({ className }: { className?: string }) {
  return (
    <span className={cn("relative block",styles.cross,className)} aria-hidden>
      <span className={cn("pointer-events-none absolute inset-[-70%] rounded-full blur-xl",styles.crossGlow)}
        style={{background:"radial-gradient(closest-side, var(--logo-sky), transparent)"}} />
      <svg viewBox="0 0 24 24" className="relative block size-full overflow-visible">
        {[
          { d: "M4 4 20 20", delay: 0.6 },
          { d: "M20 4 4 20", delay: 0.82 },
        ].map((l) => (
          <path
            key={l.d}
            d={l.d}
            fill="none"
            stroke="var(--logo-sky)"
            strokeWidth={2.2}
            strokeLinecap="round"
            pathLength={1} className={styles.crossLine}
            style={{"--draw-delay":`${l.delay}s`} as CSSProperties}
          />
        ))}
      </svg>
    </span>
  );
}
