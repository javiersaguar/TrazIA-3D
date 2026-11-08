"use client";

import { useInView, useScroll, useTransform } from "motion/react";
import dynamic from "next/dynamic";
import { useRef } from "react";

import { SIGNATURE_PHASES } from "@/features/viewer3d/signature-phases";
import { ScrollPhases, useReducedPreference } from "./scroll-phases";

/*
  Sección fijada: al bajar, el plano GA de V-101 se levanta hasta el IFC generado.
  El scroll es el avance de la secuencia; con movimiento reducido se muestra el final.
*/

const Signature = dynamic(() => import("@/features/viewer3d/signature").then((m) => m.Signature), { ssr: false, loading: () => null });

export function PlanSection({ enabled = true }: { enabled?: boolean }) {
  const ref = useRef<HTMLElement>(null);
  const reduced = useReducedPreference();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  // Termina un poco antes de soltar la sección para que el modelo final se vea quieto
  const progress = useTransform(scrollYProgress, [0.04, 0.88], [0, 1], { clamp: true });
  // Se monta poco antes de llegar: el PDF y el IFC tardan en leerse
  const near = useInView(ref, { margin: "0px 0px 15% 0px", once: true });

  return (
    <section id="del-plano" ref={ref} aria-labelledby="plano-titulo" className="relative h-[240vh] scroll-mt-16">
      <div className="sticky top-0 flex min-h-dvh items-center py-16">
        <div className="mx-auto grid w-full max-w-[1240px] items-center gap-10 px-5 md:px-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] lg:gap-14">
          <div>
            <h2 id="plano-titulo" className="landing-display text-[clamp(32px,4.2vw,56px)] leading-[1] text-strong">
              Del plano al modelo
            </h2>
            <p className="mt-4 max-w-[46ch] text-[15px] leading-relaxed text-muted">
              Baja la página y el plano GA de V-101 se levanta hasta el IFC que genera TrazIA-3D.
            </p>
            <ScrollPhases phases={SIGNATURE_PHASES} progress={progress} reduced={reduced} />
          </div>

          <div className="relative h-[min(62vh,560px)] lg:order-first" data-testid="landing-signature">
            {enabled && near ? <Signature pixelBudget={650_000} progress={progress} /> : null}
          </div>
        </div>
      </div>
    </section>
  );
}
