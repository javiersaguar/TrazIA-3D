"use client";

import { motion } from "motion/react";
import { useId } from "react";

import { EASE_IN_OUT, EASE_OUT } from "@/components/motion/reveal";
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
        <motion.path
          key={i}
          d={f.d}
          fill={faceFill(f, uid, i)}
          fillRule="evenodd"
          stroke={ink ? "var(--logo-ink-hi)" : "var(--logo-sky)"}
          strokeWidth={1.25}
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
          initial={{ pathLength: 0, x: dx, y: dy, fillOpacity: 0, strokeOpacity: 1 }}
          animate={{ pathLength: 1, x: 0, y: 0, fillOpacity: 1, strokeOpacity: 0 }}
          transition={{
            pathLength: { duration: 0.7, delay: t0, ease: EASE_IN_OUT },
            x: { duration: 0.95, delay: t0 + 0.1, ease: EASE_OUT },
            y: { duration: 0.95, delay: t0 + 0.1, ease: EASE_OUT },
            fillOpacity: { duration: 0.45, delay: 0.72 + t0 * 0.6, ease: "easeOut" },
            strokeOpacity: { duration: 0.4, delay: 1.1, ease: "easeOut" },
          }}
        />
      ))}

      {/* Brillo que recorre la marca al quedar montada */}
      <g clipPath={`url(#${uid}-clip)`}>
        <motion.rect
          y={230}
          width={180}
          height={665}
          fill={`url(#${uid}-sheen)`}
          initial={{ x: 120 }}
          animate={{ x: 980 }}
          transition={{ duration: 0.8, delay: 1.15, ease: EASE_IN_OUT }}
        />
      </g>
    </svg>
  );
}

function AssembledWordmark() {
  const uid = `lw${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  return (
    <motion.div
      className="relative h-full"
      initial={{ filter: "blur(10px)", opacity: 0 }}
      animate={{ filter: "blur(0px)", opacity: 1 }}
      transition={{ duration: 0.7, delay: WORD_START, ease: EASE_OUT }}
    >
      {/* Brillo breve detrás de «3D» */}
      <motion.span
        aria-hidden
        className="pointer-events-none absolute inset-y-[-60%] right-[-6%] left-[66%] rounded-full blur-2xl"
        style={{ background: "radial-gradient(closest-side, var(--logo-sky), transparent)" }}
        initial={{ opacity: 0 }}
        animate={{ opacity: [0, 0.75, 0.22] }}
        transition={{ duration: 1.1, delay: WORD_START + 0.45, times: [0, 0.35, 1], ease: "easeOut" }}
      />
      <svg viewBox={WORD_VIEWBOX} className="relative block h-full w-auto overflow-visible" aria-hidden>
        {WORD_PARTS.map(({ f, i }, k) => (
          <motion.path
            key={i}
            d={f.d}
            fill={faceFill(f, uid, i)}
            fillRule="evenodd"
            initial={{ opacity: 0, y: 34 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: WORD_START + k * 0.05, ease: EASE_OUT }}
          />
        ))}
      </svg>
    </motion.div>
  );
}

/**
 * Animación de formación del logo. Los contenedores llevan `layoutId` opcionales para que, al
 * terminar, la marca y el wordmark viajen hasta donde estén las copias estáticas con el mismo id.
 */
export function LogoAssemble({
  className,
  markLayoutId,
  wordLayoutId,
}: {
  className?: string;
  markLayoutId?: string;
  wordLayoutId?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center", className)}>
      <motion.div layoutId={markLayoutId} className="w-[clamp(128px,22vw,200px)]">
        <AssembledMark />
      </motion.div>
      <motion.div layoutId={wordLayoutId} className="mt-9 h-[clamp(26px,4.4vw,40px)]">
        <AssembledWordmark />
      </motion.div>
    </div>
  );
}
