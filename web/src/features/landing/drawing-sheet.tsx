"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import dynamic from "next/dynamic";
import { useEffect, useState, type ReactNode } from "react";

import { DrawPath } from "@/components/motion/draw-path";
import { EASE_OUT } from "@/components/motion/reveal";
import { cn } from "@/lib/cn";

/*
  Hoja de plano del hero: el alzado GA de V-101 (rev. B, datos sintéticos de la demo) se dibuja
  solo, aparecen las cotas y la revisión B se marca con su nube. A la derecha, el 3D ilustrativo
  del Agente 2 sale de las líneas de proyección.
  Escala del dibujo: 1 mm = 0,05 unidades. Cotas reales de la demo: Ø 2000, altura 6500 (era
  6000), faldón 1350 (era 1200), N1–N4 con su elevación y azimut.
*/

const ShowcaseVessel = dynamic(
  () => import("@/features/showcase3d").then((m) => m.ShowcaseVessel),
  {
    ssr: false,
    loading: () => null,
  },
);

const S = 0.05;
const BASE_Y = 387.5; // línea de tangencia inferior
const y = (elev: number) => BASE_Y - elev * S;

const INK = "var(--sheet-ink)";
const THIN = "var(--sheet-thin)";
const REV = "var(--revision)";

/** Nube de revisión: festón de arcos alrededor de un rectángulo. */
function cloud(x: number, y0: number, w: number, h: number, r = 5) {
  const nx = Math.max(2, Math.round(w / (2 * r)));
  const ny = Math.max(2, Math.round(h / (2 * r)));
  const sx = w / nx;
  const sy = h / ny;
  let d = `M${x} ${y0}`;
  for (let i = 1; i <= nx; i++)
    d += ` A${sx / 2} ${sx / 2} 0 0 1 ${x + i * sx} ${y0}`;
  for (let i = 1; i <= ny; i++)
    d += ` A${sy / 2} ${sy / 2} 0 0 1 ${x + w} ${y0 + i * sy}`;
  for (let i = 1; i <= nx; i++)
    d += ` A${sx / 2} ${sx / 2} 0 0 1 ${x + w - i * sx} ${y0 + h}`;
  for (let i = 1; i <= ny; i++)
    d += ` A${sy / 2} ${sy / 2} 0 0 1 ${x} ${y0 + h - i * sy}`;
  return d;
}

function Arrow({
  x,
  y: ay,
  dir,
}: {
  x: number;
  y: number;
  dir: "up" | "down" | "left" | "right";
}) {
  const p =
    dir === "up"
      ? `M${x} ${ay} l-2.6 7 h5.2 Z`
      : dir === "down"
        ? `M${x} ${ay} l-2.6 -7 h5.2 Z`
        : dir === "left"
          ? `M${x} ${ay} l7 -2.6 v5.2 Z`
          : `M${x} ${ay} l-7 -2.6 v5.2 Z`;
  return <path d={p} fill={THIN} />;
}

function Fade({ delay, children }: { delay: number; children: ReactNode }) {
  return (
    <motion.g
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.35, delay, ease: "easeOut" }}
    >
      {children}
    </motion.g>
  );
}

function Balloon({
  x,
  y: by,
  label,
  delay,
  tone = THIN,
}: {
  x: number;
  y: number;
  label: string;
  delay: number;
  tone?: string;
}) {
  return (
    <Fade delay={delay}>
      <circle
        cx={x}
        cy={by}
        r={10}
        fill="var(--surface-sunken)"
        stroke={tone}
        vectorEffect="non-scaling-stroke"
        strokeWidth={0.9}
      />
      <text
        x={x}
        y={by + 3.6}
        textAnchor="middle"
        className="font-mono"
        fontSize={9.5}
        fill={tone === THIN ? "var(--text-muted)" : tone}
      >
        {label}
      </text>
    </Fade>
  );
}

const main = {
  stroke: INK,
  strokeWidth: 1.35,
  fill: "none",
  vectorEffect: "non-scaling-stroke" as const,
  strokeLinejoin: "round" as const,
};
const thin = {
  stroke: THIN,
  strokeWidth: 0.8,
  fill: "none",
  vectorEffect: "non-scaling-stroke" as const,
};
const rev = {
  stroke: REV,
  strokeWidth: 1.35,
  fill: "none",
  vectorEffect: "non-scaling-stroke" as const,
  strokeLinejoin: "round" as const,
};

/** Alzado GA de V-101 visto desde el azimut 0: N2 (90°) a la derecha, N4 (270°) a la izquierda. */
function Elevation({ revB }: { revB: boolean }) {
  const hatch = Array.from(
    { length: 13 },
    (_, i) => `M${90 + i * 10} 455 l-7 8`,
  ).join(" ");
  return (
    <svg
      viewBox="0 0 420 480"
      className="block h-full w-auto max-w-full overflow-visible"
      role="img"
      aria-label="Alzado del recipiente V-101, revisión B"
    >
      {/* Eje */}
      <DrawPath
        d="M150 14 V472"
        {...thin}
        strokeDasharray="14 3 2 3"
        delay={0.5}
        duration={0.8}
      />

      {/* Fondos, virola y faldón */}
      <DrawPath
        d={`M100 ${y(6500)} A50 25 0 0 1 200 ${y(6500)}`}
        {...main}
        delay={0.05}
        duration={0.6}
      />
      <DrawPath
        d={`M100 ${y(6500)} V${BASE_Y} M200 ${y(6500)} V${BASE_Y}`}
        {...main}
        delay={0.2}
        duration={1}
      />
      <DrawPath
        d={`M100 ${BASE_Y} A50 25 0 0 0 200 ${BASE_Y}`}
        {...thin}
        strokeDasharray="4 3"
        delay={0.7}
        duration={0.5}
      />
      <DrawPath
        d={`M100 ${y(6500)} H200 M100 ${BASE_Y} H200`}
        {...thin}
        delay={0.65}
        duration={0.5}
      />
      <DrawPath
        d={`M100 ${BASE_Y} V451 M200 ${BASE_Y} V451 M92 451 H208 V455 H92 Z`}
        {...main}
        delay={0.55}
        duration={0.7}
      />
      <DrawPath
        d="M134 449 V432 A16 16 0 0 1 166 432 V449 Z"
        {...thin}
        delay={0.95}
        duration={0.5}
      />
      <DrawPath
        d={`M82 455 H218 ${hatch}`}
        {...thin}
        delay={0.9}
        duration={0.6}
      />

      {/* N1 (az 0, de frente) y N3 (az 180, detrás: oculta) */}
      <DrawPath
        d={`M141 ${y(2500)} a9 9 0 1 0 18 0 a9 9 0 1 0 -18 0 M145 ${y(2500)} a5 5 0 1 0 10 0 a5 5 0 1 0 -10 0`}
        {...main}
        delay={1.05}
        duration={0.5}
      />
      <DrawPath
        d={`M139 ${y(3700)} a11 11 0 1 0 22 0 a11 11 0 1 0 -22 0`}
        {...(revB ? rev : thin)}
        strokeDasharray="4 3"
        delay={1.15}
        duration={0.5}
      />
      {/* N2 (az 90, derecha) */}
      <DrawPath
        d={`M200 ${y(5500) - 2.5} H215 M200 ${y(5500) + 2.5} H215 M215 ${y(5500) - 6.5} h3 v13 h-3 Z`}
        {...main}
        delay={1.2}
        duration={0.45}
      />

      {/* Cota del diámetro */}
      <DrawPath
        d="M100 34 V18 M200 34 V18 M100 22 H200"
        {...thin}
        delay={1.3}
        duration={0.5}
      />
      <Fade delay={1.6}>
        <Arrow x={100} y={22} dir="left" />
        <Arrow x={200} y={22} dir="right" />
        <text
          x={150}
          y={16}
          textAnchor="middle"
          className="font-mono"
          fontSize={11}
          fill="var(--text-muted)"
        >
          Ø2000
        </text>
      </Fade>

      {/* Cota de altura entre tangentes (cambia en la rev. B) */}
      <DrawPath
        d={`M205 ${y(6500)} H262 M205 ${BASE_Y} H262 M256 ${y(6500)} V${BASE_Y}`}
        {...thin}
        delay={1.4}
        duration={0.6}
      />
      <Fade delay={1.75}>
        <Arrow x={256} y={y(6500)} dir="up" />
        <Arrow x={256} y={BASE_Y} dir="down" />
      </Fade>
      <g transform={`translate(249 ${(y(6500) + BASE_Y) / 2}) rotate(-90)`}>
        <AnimatePresence mode="wait" initial={false}>
          <motion.text
            key={revB ? "b" : "a"}
            textAnchor="middle"
            className="font-mono"
            fontSize={11}
            fill={revB ? REV : "var(--text-muted)"}
            initial={{ opacity: 0, y: 6 }}
            animate={{
              opacity: 1,
              y: 0,
              transition: {
                duration: 0.3,
                delay: revB ? 0 : 1.8,
                ease: EASE_OUT,
              },
            }}
            exit={{ opacity: 0, y: -6, transition: { duration: 0.18 } }}
          >
            {revB ? "6500" : "6000"}
          </motion.text>
        </AnimatePresence>
      </g>
      {revB ? (
        <>
          <DrawPath
            d={cloud(236, y(6500) + 128, 22, 70, 5)}
            {...rev}
            duration={0.7}
          />
          <Fade delay={0.55}>
            <path
              d={`M268 ${y(6500) + 150} l7 12 h-14 Z`}
              fill="none"
              stroke={REV}
              strokeWidth={1.1}
              vectorEffect="non-scaling-stroke"
            />
            <text
              x={268}
              y={y(6500) + 160.5}
              textAnchor="middle"
              className="font-mono"
              fontSize={8}
              fill={REV}
            >
              B
            </text>
          </Fade>
        </>
      ) : null}

      {/* Faldón (cambia en la rev. B) */}
      <DrawPath
        d={`M95 ${BASE_Y} H52 M88 455 H52 M58 ${BASE_Y} V455`}
        {...thin}
        delay={1.5}
        duration={0.5}
      />
      <Fade delay={1.8}>
        <Arrow x={58} y={BASE_Y} dir="up" />
        <Arrow x={58} y={455} dir="down" />
        <text
          transform={`translate(52 ${(BASE_Y + 455) / 2}) rotate(-90)`}
          textAnchor="middle"
          className="font-mono"
          fontSize={11}
          fill={revB ? REV : "var(--text-muted)"}
        >
          {revB ? "1350" : "1200"}
        </text>
      </Fade>

      {/* N4 (az 270): nueva en la rev. B */}
      {revB ? (
        <>
          <DrawPath
            d={`M100 ${y(6200) - 2.5} H85 M100 ${y(6200) + 2.5} H85 M85 ${y(6200) - 6.5} h-3 v13 h3 Z`}
            {...rev}
            delay={0.25}
            duration={0.45}
          />
          <DrawPath
            d={`M80 ${y(6200)} L58 ${y(6200) - 22}`}
            {...rev}
            strokeWidth={0.8}
            delay={0.5}
            duration={0.3}
          />
          <Balloon x={50} y={y(6200) - 30} label="N4" delay={0.7} tone={REV} />
        </>
      ) : null}

      {/* Globos de boquillas */}
      <DrawPath
        d={`M159 ${y(2500) + 4} L178 ${y(2500) + 30}`}
        {...thin}
        delay={1.9}
        duration={0.3}
      />
      <Balloon x={186} y={y(2500) + 40} label="N1" delay={2} />
      <DrawPath
        d={`M218 ${y(5500)} L232 ${y(5500) - 22}`}
        {...thin}
        delay={1.95}
        duration={0.3}
      />
      <Balloon x={236} y={y(5500) - 32} label="N2" delay={2.05} />
      <DrawPath
        d={`M139 ${y(3700) - 6} L120 ${y(3700) - 28}`}
        {...(revB ? rev : thin)}
        strokeWidth={0.8}
        delay={2}
        duration={0.3}
      />
      <Balloon
        x={114}
        y={y(3700) - 38}
        label="N3"
        delay={2.1}
        tone={revB ? REV : THIN}
      />

      {/* Líneas de proyección hacia la vista 3D */}
      <DrawPath
        d={`M268 ${y(6500)} H420 M268 ${BASE_Y} H420`}
        {...thin}
        strokeDasharray="2 4"
        delay={2.1}
        duration={0.8}
      />
    </svg>
  );
}

function ZoneMarks() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-3 font-mono text-[9.5px] text-faint"
    >
      <div className="absolute inset-x-0 top-1 flex justify-around">
        {["1", "2", "3", "4"].map((n) => (
          <span key={n}>{n}</span>
        ))}
      </div>
      <div className="absolute inset-y-0 left-1.5 flex flex-col justify-around">
        {["A", "B", "C"].map((n) => (
          <span key={n}>{n}</span>
        ))}
      </div>
    </div>
  );
}

function TitleBlock() {
  const cells: [string, string, string?][] = [
    ["Proyecto", "DEMO-PLANT"],
    ["Equipo", "V-101, vertical", "col-span-2"],
    ["Documento", "Plano GA"],
    ["Escala", "1:50"],
    ["Rev.", "B"],
  ];
  return (
    <dl className="grid grid-cols-3 border-l border-border-strong font-mono text-[10.5px]">
      {cells.map(([k, v, span]) => (
        <div
          key={k}
          className={cn(
            "min-w-0 border-t border-r border-border-strong px-2 py-1.5",
            span,
          )}
        >
          <dt className="truncate text-[9px] text-faint">{k}</dt>
          <dd className="truncate text-text">{v}</dd>
        </div>
      ))}
      <div className="border-t border-r border-border-strong px-2 py-1.5">
        <dt className="text-[9px] text-faint">Datos</dt>
        <dd className="text-warning">sintéticos</dd>
      </div>
    </dl>
  );
}

function RevisionTable({ revB }: { revB: boolean }) {
  return (
    <table className="w-full border-collapse font-mono text-[10.5px]">
      <caption className="sr-only">Tabla de revisiones</caption>
      <thead>
        <tr className="text-[9px] text-faint">
          <th
            scope="col"
            className="w-9 border-t border-r border-border-strong px-2 py-1 text-left font-normal"
          >
            Rev.
          </th>
          <th
            scope="col"
            className="border-t border-border-strong px-2 py-1 text-left font-normal"
          >
            Descripción
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          className={cn(
            "transition-colors duration-500",
            revB ? "text-revision" : "text-faint",
          )}
        >
          <td className="border-t border-r border-border-strong px-2 py-1">
            B
          </td>
          <td className="truncate border-t border-border-strong px-2 py-1">
            Altura 6500, faldón 1350, N3 a 3700, N4 nueva
          </td>
        </tr>
        <tr className="text-muted">
          <td className="border-t border-r border-border-strong px-2 py-1">
            A
          </td>
          <td className="border-t border-border-strong px-2 py-1">
            Emisión inicial
          </td>
        </tr>
      </tbody>
    </table>
  );
}

/** Hoja de plano completa. `play` arranca el dibujo (se retiene mientras dura la intro). */
export function DrawingSheet({
  play,
  className,
}: {
  play: boolean;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const [revB, setRevB] = useState(false);

  useEffect(() => {
    if (!play) return;
    const t = window.setTimeout(() => setRevB(true), reduced ? 0 : 2900);
    return () => window.clearTimeout(t);
  }, [play, reduced]);

  return (
    <figure
      className={cn(
        "relative flex flex-col overflow-hidden rounded-[16px] border border-border bg-surface-sunken shadow-[var(--shadow-pop)]",
        className,
      )}
    >
      <div
        className="landing-paper pointer-events-none absolute inset-0 opacity-70"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-3 rounded-[3px] border border-border-strong"
        aria-hidden
      />
      <ZoneMarks />

      <div className="relative flex min-h-0 flex-1 items-stretch px-7 pt-8 pb-3">
        {/* En móvil el alzado no puede llevarse todo el ancho: el recipiente 3D necesita su hueco */}
        <div className="pointer-events-none relative z-[1] h-full min-h-0 max-w-[58%] shrink-0 sm:max-w-none">
          {play ? <Elevation revB={revB} /> : null}
        </div>
        <div className="relative -ml-[14%] min-w-0 flex-1">
          {play ? (
            <motion.div
              className="absolute inset-0"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                duration: 0.9,
                delay: reduced ? 0 : 2.3,
                ease: EASE_OUT,
              }}
            >
              <ShowcaseVessel
                mode="particles"
                interactive
                hud={false}
                className="h-full w-full !bg-transparent"
              />
            </motion.div>
          ) : null}
          {/* El aviso «Ilustrativo» lo pone el propio ShowcaseVessel abajo; la pista va arriba para no pisarlo */}
          <p className="pointer-events-none absolute top-1 right-1 hidden font-mono text-[10px] text-faint sm:block">
            Arrastra para girar. Clic para cambiar de equipo.
          </p>
        </div>
      </div>

      {/* Tabla y cajetín lado a lado solo cuando la lámina es ancha; en tableta van uno sobre otro */}
      <figcaption className="relative mx-3 mb-3 grid grid-cols-1 border-b border-border-strong bg-surface-sunken/80 xl:grid-cols-[1.1fr_1fr]">
        <div className="border-l border-border-strong">
          <RevisionTable revB={revB} />
        </div>
        <TitleBlock />
      </figcaption>
    </figure>
  );
}
