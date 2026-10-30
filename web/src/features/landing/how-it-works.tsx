"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";

import { DrawPath } from "@/components/motion/draw-path";
import { EASE_OUT } from "@/components/motion/reveal";

/*
  Cuatro pasos reales, en orden. Los globos numerados y la línea de cota que los une salen del
  lenguaje de los planos: aquí sí hay una secuencia.
*/

const ink = { stroke: "var(--sheet-ink)", strokeWidth: 1.2, fill: "none", vectorEffect: "non-scaling-stroke" as const, strokeLinejoin: "round" as const };
const thin = { stroke: "var(--sheet-thin)", strokeWidth: 0.8, fill: "none", vectorEffect: "non-scaling-stroke" as const };
const sky = { stroke: "var(--accent)", strokeWidth: 1.3, fill: "none", vectorEffect: "non-scaling-stroke" as const, strokeLinejoin: "round" as const };
const rev = { stroke: "var(--revision)", strokeWidth: 1.3, fill: "none", vectorEffect: "non-scaling-stroke" as const, strokeLinejoin: "round" as const };

function Pop({ delay, children }: { delay: number; children: ReactNode }) {
  return (
    <motion.g initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true, margin: "-60px" }} transition={{ duration: 0.4, delay, ease: "easeOut" }}>
      {children}
    </motion.g>
  );
}

function PlanArt() {
  return (
    <svg viewBox="0 0 200 130" className="h-full w-full" aria-hidden>
      <DrawPath inView d="M14 10 H186 V120 H14 Z M20 16 H180 V114 H20 Z" {...thin} duration={0.8} />
      <DrawPath inView d="M70 28 A14 7 0 0 1 98 28 V86 M70 28 V86 M70 86 A14 7 0 0 0 98 86 M70 86 V104 M98 86 V104 M64 104 H104" {...ink} delay={0.2} duration={1} />
      <DrawPath inView d="M84 20 V110" {...thin} strokeDasharray="8 2 2 2" delay={0.4} />
      <DrawPath inView d="M124 84 H180 M124 94 H180 M124 104 H180 M124 84 V114 M150 84 V114" {...thin} delay={0.7} duration={0.6} />
      <DrawPath inView d="M104 34 H116 M104 86 H116 M112 34 V86" {...thin} delay={0.9} duration={0.5} />
    </svg>
  );
}

function EvidenceArt() {
  return (
    <svg viewBox="0 0 200 130" className="h-full w-full" aria-hidden>
      <DrawPath inView d="M30 40 V18 M110 40 V18 M30 24 H110" {...thin} duration={0.6} />
      <DrawPath inView d="M30 40 V110 M110 40 V110" {...ink} delay={0.1} duration={0.8} />
      <Pop delay={0.5}>
        <text x={70} y={20} textAnchor="middle" className="font-mono" fontSize={10} fill="var(--text-muted)">
          Ø2000
        </text>
      </Pop>
      <DrawPath inView d="M52 8 H88 V27 H52 Z" {...sky} strokeDasharray="3 2" delay={0.75} duration={0.5} />
      <DrawPath inView d="M88 18 C120 18 118 66 132 66" {...sky} delay={1.0} duration={0.5} />
      <Pop delay={1.3}>
        <rect x={132} y={54} width={60} height={34} rx={6} fill="var(--surface-raised)" stroke="var(--border-strong)" />
        <text x={140} y={68} className="font-mono" fontSize={9} fill="var(--text)">
          2000 mm
        </text>
        <rect x={140} y={75} width={44} height={3} rx={1.5} fill="var(--border)" />
      </Pop>
      <motion.rect
        x={140}
        y={75}
        height={3}
        rx={1.5}
        fill="var(--accent)"
        initial={{ width: 0 }}
        whileInView={{ width: 40 }}
        viewport={{ once: true, margin: "-60px" }}
        transition={{ duration: 0.6, delay: 1.5, ease: EASE_OUT }}
      />
    </svg>
  );
}

function ModelArt() {
  return (
    <svg viewBox="0 0 200 130" className="h-full w-full" aria-hidden>
      <Pop delay={0.9}>
        <path d="M76 28 A24 9 0 0 1 124 28 V100 A24 9 0 0 1 76 100 Z" fill="var(--accent-soft)" />
      </Pop>
      <DrawPath inView d="M76 28 A24 9 0 0 1 124 28 A24 9 0 0 1 76 28 Z" {...sky} duration={0.6} />
      <DrawPath inView d="M76 28 V100 M124 28 V100" {...sky} delay={0.3} duration={0.6} />
      <DrawPath inView d="M76 100 A24 9 0 0 0 124 100" {...sky} delay={0.55} duration={0.4} />
      <DrawPath inView d="M76 100 A24 9 0 0 1 124 100" {...thin} strokeDasharray="3 2" delay={0.6} duration={0.4} />
      <DrawPath inView d="M76 28 A24 18 0 0 1 124 28" {...sky} delay={0.7} duration={0.4} />
      <DrawPath inView d="M124 62 H140 M140 56 V68" {...sky} delay={0.85} duration={0.3} />
      <Pop delay={1.1}>
        <text x={150} y={118} className="font-mono" fontSize={9} fill="var(--text-faint)">
          IFC4
        </text>
      </Pop>
    </svg>
  );
}

function ChangesArt() {
  return (
    <svg viewBox="0 0 200 130" className="h-full w-full" aria-hidden>
      <DrawPath inView d="M40 40 A16 6 0 0 1 72 40 V108 M40 40 V108 M36 108 H76" {...thin} duration={0.8} />
      <Pop delay={0.3}>
        <text x={56} y={124} textAnchor="middle" className="font-mono" fontSize={9} fill="var(--text-faint)">
          A
        </text>
      </Pop>
      <DrawPath inView d="M118 28 A16 6 0 0 1 150 28 V108 M118 28 V108 M114 108 H154" {...rev} delay={0.5} duration={0.9} />
      <Pop delay={0.9}>
        <text x={134} y={124} textAnchor="middle" className="font-mono" fontSize={9} fill="var(--revision)">
          B
        </text>
      </Pop>
      <DrawPath inView d="M76 40 H114 M76 28 H114" {...thin} strokeDasharray="2 3" delay={1.0} duration={0.5} />
      <DrawPath inView d="M100 40 V28" {...rev} delay={1.3} duration={0.3} />
      <Pop delay={1.45}>
        <text x={160} y={38} className="font-mono" fontSize={9.5} fill="var(--revision)">
          +500
        </text>
      </Pop>
    </svg>
  );
}

const STEPS = [
  {
    title: "Plano",
    text: "Subes el PDF del plano GA. Se leen el texto, las tablas, las cotas y el cajetín; si no hay capa de texto, entra el OCR.",
    art: <PlanArt />,
  },
  {
    title: "Evidencia",
    text: "Cada campo guarda su valor, su unidad, la zona del plano de la que sale y la confianza de la lectura.",
    art: <EvidenceArt />,
  },
  {
    title: "Modelo",
    text: "Con los campos revisados se genera el IFC. El visor enseña esa geometría, no un dibujo aparte.",
    art: <ModelArt />,
  },
  {
    title: "Cambios",
    text: "Con una revisión nueva, compara A y B: qué cambió, cuánto y dónde, en el plano y en 3D.",
    art: <ChangesArt />,
  },
];

export function HowItWorks() {
  return (
    <section id="como-funciona" aria-labelledby="como-titulo" className="mx-auto w-full max-w-[1240px] scroll-mt-20 px-5 py-24 md:px-8 md:py-32">
      <div className="max-w-[60ch]">
        <h2 id="como-titulo" className="landing-display text-[clamp(32px,4.2vw,56px)] leading-[1] text-strong">
          Cómo funciona
        </h2>
        <p className="mt-4 text-[16px] leading-relaxed text-muted">Cuatro pasos, del PDF al modelo que revisa una persona.</p>
      </div>

      <div className="relative mt-14">
        {/* Línea de cota que une los cuatro globos */}
        <svg aria-hidden className="pointer-events-none absolute top-[15px] right-[calc(25%-16px)] left-4 hidden h-3 overflow-visible lg:block" preserveAspectRatio="none" viewBox="0 0 100 12">
          <DrawPath inView d="M0 6 H100" stroke="var(--sheet-thin)" strokeWidth={0.8} vectorEffect="non-scaling-stroke" fill="none" duration={1.2} />
        </svg>
        <ol className="grid gap-12 md:grid-cols-2 lg:grid-cols-4 lg:gap-8">
          {STEPS.map((s, i) => (
            <motion.li
              key={s.title}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.55, delay: i * 0.08, ease: EASE_OUT }}
              className="relative"
            >
              <span className="relative z-[1] flex size-8 items-center justify-center rounded-full border border-accent bg-bg font-mono text-[13px] text-accent-text">
                {i + 1}
              </span>
              <h3 className="mt-5 text-[17px] font-semibold text-strong">{s.title}</h3>
              <p className="mt-2 max-w-[38ch] text-[14.5px] leading-relaxed text-muted">{s.text}</p>
              <div className="drafting-grid mt-6 aspect-[20/13] overflow-hidden rounded-[12px] border border-border">{s.art}</div>
            </motion.li>
          ))}
        </ol>
      </div>
    </section>
  );
}
