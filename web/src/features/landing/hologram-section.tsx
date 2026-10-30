"use client";

import {
  motion,
  useInView,
  useMotionValueEvent,
  useScroll,
  useTransform,
} from "motion/react";
import dynamic from "next/dynamic";
import { useRef, useState, useSyncExternalStore } from "react";

import { cn } from "@/lib/cn";

/*
  Sección fijada mientras se hace scroll: el avance del scroll es el avance de la transformación
  holograma → modelo real (componente del Agente 2, ilustrativo).
*/

const HologramToReal = dynamic(
  () => import("@/features/hologram").then((m) => m.HologramToReal),
  {
    ssr: false,
    loading: () => null,
  },
);

const PHASES = [
  {
    at: 0,
    title: "Lo que se ha leído",
    text: "Este holograma ilustra la fase de lectura. El equipo de esta sección es paramétrico y no procede de un plano real.",
  },
  {
    at: 0.38,
    title: "Lo que tiene evidencia",
    text: "El barrido explica el paso de borrador a modelo. La evidencia real de cada campo se consulta en Revisión.",
  },
  {
    at: 0.72,
    title: "Lo que se revisa",
    text: "El IFC y sus fuentes se revisan antes de aprobar una exportación. Puedes explorarlos en Modelo 3D.",
  },
];

function phaseOf(p: number) {
  let k = 0;
  PHASES.forEach((ph, i) => {
    if (p >= ph.at) k = i;
  });
  return k;
}

const reducedSnapshot = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const subscribeReduced = (fn: () => void) => {
  const q = window.matchMedia("(prefers-reduced-motion: reduce)");
  q.addEventListener("change", fn);
  return () => q.removeEventListener("change", fn);
};

export function HologramSection() {
  const ref = useRef<HTMLElement>(null);
  const reduced = useSyncExternalStore(
    subscribeReduced,
    reducedSnapshot,
    () => false,
  );
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end end"],
  });
  const near = useInView(ref, { margin: "0px", amount: 0.05, once: true });
  const [active, setActive] = useState(0);
  const percentage = useRef<HTMLSpanElement>(null),
    currentPhase = useRef(0);
  useMotionValueEvent(scrollYProgress, "change", (value) => {
    const next = phaseOf(value);
    if (next !== currentPhase.current) {
      currentPhase.current = next;
      setActive(next);
    }
    if (percentage.current)
      percentage.current.textContent = reduced
        ? "100 %"
        : `${Math.round(value * 100)} %`;
  });
  const firstFill = useTransform(scrollYProgress, [0, 0.38], [0, 1]);
  const secondFill = useTransform(scrollYProgress, [0.38, 0.72], [0, 1]);
  const thirdFill = useTransform(scrollYProgress, [0.72, 1], [0, 1]);
  const fills = [firstFill, secondFill, thirdFill];

  return (
    <section
      ref={ref}
      aria-labelledby="holograma-titulo"
      className="relative h-[240vh]"
    >
      <div className="sticky top-0 flex min-h-dvh items-center py-16">
        <div className="mx-auto grid w-full max-w-[1240px] items-center gap-10 px-5 md:px-8 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-14">
          <div>
            <h2
              id="holograma-titulo"
              className="landing-display text-[clamp(32px,4.2vw,56px)] leading-[1] text-strong"
            >
              Del holograma al modelo
            </h2>
            <ol className="mt-8 space-y-6">
              {PHASES.map((ph, i) => {
                return (
                  <li
                    key={ph.title}
                    className="grid grid-cols-[3px_minmax(0,1fr)] gap-4"
                  >
                    <span
                      className="relative overflow-hidden rounded-full bg-border"
                      aria-hidden
                    >
                      <motion.span
                        className="absolute inset-0 origin-top bg-accent"
                        style={{ scaleY: reduced ? 1 : fills[i] }}
                      />
                    </span>
                    <div
                      className={cn(
                        "transition-opacity duration-300",
                        i === (reduced ? PHASES.length - 1 : active)
                          ? "opacity-100"
                          : "opacity-45",
                      )}
                    >
                      <h3 className="text-[16px] font-semibold text-strong">
                        {ph.title}
                      </h3>
                      <p className="mt-1 max-w-[44ch] text-[14.5px] leading-relaxed text-muted">
                        {ph.text}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>

          <div className="relative h-[min(62vh,560px)] overflow-hidden rounded-[16px] border border-border bg-surface-sunken">
            {/* El aviso «Ilustrativo» y el avance ya los pinta HologramToReal (arriba y abajo) */}
            {near ? (
              <HologramToReal
                source="procedural"
                layout="side"
                progressValue={scrollYProgress}
                controls={false}
                callouts
                className="h-full w-full"
              />
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
