"use client";

import { motion } from "motion/react";
import { useId } from "react";

import { EASE_IN_OUT, EASE_OUT } from "@/components/motion/reveal";
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

      <motion.g
        style={{ transformBox: "fill-box", transformOrigin: "center" }}
        initial={{ scale: 0.94 }}
        animate={{ scale: 1 }}
        transition={{ duration: 1.3, delay: 0.1, ease: EASE_OUT }}
      >
        {TR_MARK_PIECES.map((d, i) => (
          <motion.path
            key={i}
            d={d}
            fill="var(--logo-ink-hi)"
            fillRule="evenodd"
            stroke="var(--logo-ink-hi)"
            strokeWidth={1.25}
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
            initial={{ pathLength: 0, fillOpacity: 0, strokeOpacity: 1 }}
            animate={{ pathLength: 1, fillOpacity: 1, strokeOpacity: 0 }}
            transition={{
              pathLength: { duration: i ? 0.55 : 0.8, delay: i ? 0.42 : 0.12, ease: EASE_IN_OUT },
              fillOpacity: { duration: 0.45, delay: 0.82 + i * 0.08, ease: "easeOut" },
              strokeOpacity: { duration: 0.4, delay: 1.1, ease: "easeOut" },
            }}
          />
        ))}
      </motion.g>

      {/* Brillo celeste que recorre la marca al quedar formada */}
      <g clipPath={`url(#${uid}-clip)`}>
        <motion.rect
          y={MY}
          width={MW * 0.45}
          height={MH}
          fill={`url(#${uid}-sheen)`}
          initial={{ x: MX - MW * 0.5 }}
          animate={{ x: MX + MW }}
          transition={{ duration: 0.8, delay: 1.2, ease: EASE_IN_OUT }}
        />
      </g>

      {TR_WORD_LETTERS.map((d, k) => (
        <motion.path
          key={k}
          d={d}
          fill="var(--logo-ink-hi)"
          fillRule="evenodd"
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: WORD_START + k * 0.03, ease: EASE_OUT }}
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
    <motion.span
      className={cn("relative block", className)}
      initial={{ opacity: 0, rotate: -90, scale: 0.7 }}
      animate={{ opacity: 1, rotate: 0, scale: 1 }}
      transition={{ duration: 0.9, delay: 0.5, ease: EASE_OUT }}
      aria-hidden
    >
      <motion.span
        className="pointer-events-none absolute inset-[-70%] rounded-full blur-xl"
        style={{ background: "radial-gradient(closest-side, var(--logo-sky), transparent)" }}
        initial={{ opacity: 0, scale: 0.6 }}
        animate={{ opacity: [0, 0.7, 0], scale: [0.6, 1.15, 1.3] }}
        transition={{ duration: 1, delay: 1.45, times: [0, 0.3, 1], ease: "easeOut" }}
      />
      <svg viewBox="0 0 24 24" className="relative block size-full overflow-visible">
        {[
          { d: "M4 4 20 20", delay: 0.6 },
          { d: "M20 4 4 20", delay: 0.82 },
        ].map((l) => (
          <motion.path
            key={l.d}
            d={l.d}
            fill="none"
            stroke="var(--logo-sky)"
            strokeWidth={2.2}
            strokeLinecap="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.38, delay: l.delay, ease: EASE_IN_OUT }}
          />
        ))}
      </svg>
    </motion.span>
  );
}
