"use client";

import { motion, useMotionValueEvent, useScroll } from "motion/react";
import dynamic from "next/dynamic";
import { useRef, useState } from "react";

import { cn } from "@/lib/cn";

/*
  Sección fijada mientras se hace scroll: el avance del scroll es el avance de la transformación
  holograma → modelo real (componente del Agente 2, ilustrativo).
*/

const HologramToReal = dynamic(() => import("@/features/hologram").then((m) => m.HologramToReal), {
  ssr: false,
  loading: () => null,
});

const PHASES = [
  { at: 0, title: "Lo que se ha leído", text: "El holograma es la geometría que el sistema ha entendido del plano. Todavía es un borrador." },
  { at: 0.38, title: "Lo que tiene evidencia", text: "Cada pieza se materializa cuando sus cotas tienen una cita en el plano." },
  { at: 0.72, title: "Lo que se revisa", text: "El resultado es el modelo que una persona revisa y aprueba antes de exportarlo." },
];

function phaseOf(p: number) {
  let k = 0;
  PHASES.forEach((ph, i) => {
    if (p >= ph.at) k = i;
  });
  return k;
}

export function HologramSection() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const [p, setP] = useState(0);
  useMotionValueEvent(scrollYProgress, "change", (v) => setP(Math.round(v * 200) / 200));
  const active = phaseOf(p);

  return (
    <section ref={ref} aria-labelledby="holograma-titulo" className="relative h-[240vh]">
      <div className="sticky top-0 flex min-h-dvh items-center py-16">
        <div className="mx-auto grid w-full max-w-[1240px] items-center gap-10 px-5 md:px-8 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-14">
          <div>
            <h2 id="holograma-titulo" className="landing-display text-[clamp(32px,4.2vw,56px)] leading-[1] text-strong">
              Del holograma al modelo
            </h2>
            <ol className="mt-8 space-y-6">
              {PHASES.map((ph, i) => {
                const start = ph.at;
                const end = PHASES[i + 1]?.at ?? 1;
                const fill = Math.min(1, Math.max(0, (p - start) / (end - start)));
                return (
                  <li key={ph.title} className="grid grid-cols-[3px_minmax(0,1fr)] gap-4">
                    <span className="relative overflow-hidden rounded-full bg-border" aria-hidden>
                      <motion.span className="absolute inset-0 origin-top bg-accent" style={{ scaleY: fill }} />
                    </span>
                    <div className={cn("transition-opacity duration-300", i === active ? "opacity-100" : "opacity-45")}>
                      <h3 className="text-[16px] font-semibold text-strong">{ph.title}</h3>
                      <p className="mt-1 max-w-[44ch] text-[14.5px] leading-relaxed text-muted">{ph.text}</p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>

          <div className="relative h-[min(62vh,560px)] overflow-hidden rounded-[16px] border border-border bg-surface-sunken">
            <HologramToReal source="procedural" layout="side" progress={p} callouts className="h-full w-full" />
            <div className="pointer-events-none absolute inset-x-4 bottom-4 flex items-center gap-3 font-mono text-[11px] text-faint">
              <span>Ilustrativo, no procede del IFC</span>
              <span className="ml-auto tabular-nums text-muted">{Math.round(p * 100)} %</span>
              <span className="h-1 w-24 overflow-hidden rounded-full bg-border">
                <span className="block h-full origin-left bg-accent" style={{ transform: `scaleX(${p})` }} />
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
