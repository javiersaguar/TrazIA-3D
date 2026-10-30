"use client";

import { motion } from "motion/react";

import { CountUp } from "@/components/motion/count-up";
import { EASE_OUT } from "@/components/motion/reveal";
import { cn } from "@/lib/cn";

/*
  Las cuatro estrategias, como una tabla de revisiones de plano. Solo B tiene cifras publicadas
  (docs/ESTUDIO.md, estudio 1 del 26/10/2026, datos sintéticos); A, C y D se miden en la fase 2 y
  aquí no se inventa ningún número.
*/

type Metric = { label: string; value: number; decimals?: number; suffix?: string };

const B_METRICS: Metric[] = [
  { label: "Puntuación", value: 0.37, decimals: 3 },
  { label: "Atributos", value: 70.2, decimals: 1, suffix: " %" },
  { label: "Geometría", value: 3.3, decimals: 1, suffix: " %" },
  { label: "Alucinación", value: 0, suffix: " %" },
  { label: "Cita correcta", value: 100, suffix: " %" },
];

const ROWS: { id: string; name: string; text: string; metrics?: Metric[] }[] = [
  { id: "A", name: "Visión + 3D", text: "Saca la geometría de los trazos del dibujo. Las cotas solo fijan la escala y nombran las boquillas." },
  {
    id: "B",
    name: "Datos + reglas",
    text: "Lee texto, tablas, cotas, cajetín y hoja de datos, sin aprendizaje. Nunca inventa: si falla, el campo queda vacío.",
    metrics: B_METRICS,
  },
  { id: "C", name: "RAG", text: "Busca un equipo aprobado parecido y hereda dónde mirar. Un valor de la biblioteca nunca entra sin evidencia del plano actual." },
  {
    id: "D",
    name: "Híbrido",
    text: "Cascada de lo barato a lo caro: B, la plantilla de C, la memoria de la revisión anterior y la geometría de A como control.",
  },
];

export function Strategies() {
  return (
    <section id="estrategias" aria-labelledby="estrategias-titulo" className="mx-auto w-full max-w-[1240px] scroll-mt-20 px-5 py-24 md:px-8 md:py-32">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:items-end">
        <h2 id="estrategias-titulo" className="landing-display text-[clamp(32px,4.2vw,56px)] leading-[1] text-strong">
          Cuatro maneras de leer un plano
        </h2>
        <p className="max-w-[56ch] text-[16px] leading-relaxed text-muted">
          Las cuatro estrategias del reto se comparan con el mismo banco de pruebas. Se queda la que diga el dato, no la
          más llamativa.
        </p>
      </div>

      <div className="mt-12 overflow-hidden rounded-[16px] border border-border bg-surface">
        <div className="hidden grid-cols-[72px_minmax(0,1fr)_minmax(0,1.15fr)] border-b border-border px-5 py-2.5 text-[12px] text-faint md:grid">
          <span>Estrategia</span>
          <span>Cómo lee</span>
          <span>Medido en el banco de pruebas</span>
        </div>
        <ul>
          {ROWS.map((r, i) => (
            <motion.li
              key={r.id}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.07, ease: EASE_OUT }}
              className={cn(
                "grid gap-4 border-b border-border px-5 py-6 last:border-b-0 md:grid-cols-[72px_minmax(0,1fr)_minmax(0,1.15fr)] md:items-start",
                r.metrics && "bg-surface-raised/60",
              )}
            >
              <span
                className={cn(
                  "flex size-10 items-center justify-center rounded-full border font-mono text-[15px]",
                  r.metrics ? "border-accent text-accent-text" : "border-border-strong text-muted",
                )}
              >
                {r.id}
              </span>
              <div>
                <h3 className="text-[16px] font-semibold text-strong">{r.name}</h3>
                <p className="mt-1.5 max-w-[52ch] text-[14.5px] leading-relaxed text-muted">{r.text}</p>
              </div>
              {r.metrics ? (
                <div>
                  <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-5">
                    {r.metrics.map((m) => (
                      <div key={m.label}>
                        <dt className="text-[12px] text-faint">{m.label}</dt>
                        <dd className="mt-0.5 text-[20px] font-semibold text-strong tabular-nums">
                          <CountUp value={m.value} decimals={m.decimals} suffix={m.suffix} />
                        </dd>
                      </div>
                    ))}
                  </dl>
                  <p className="mt-3 text-[12px] text-warning">Estudio 1, 26/10/2026. Datos sintéticos, no planos del organizador.</p>
                </div>
              ) : (
                <p className="text-[14px] text-faint md:pt-1">Se mide en el estudio de la fase 2.</p>
              )}
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  );
}
