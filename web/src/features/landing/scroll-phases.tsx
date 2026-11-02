"use client";

import { motion, useMotionValueEvent, useTransform, type MotionValue } from "motion/react";
import { useRef, useState, useSyncExternalStore } from "react";

import { cn } from "@/lib/cn";

/* Lista de fases de una sección fijada: el avance del scroll rellena la barra de cada fase. */

export type ScrollPhase = { at: number; title: string; text: string };

const reducedSnapshot = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const subscribeReduced = (fn: () => void) => {
  const q = window.matchMedia("(prefers-reduced-motion: reduce)");
  q.addEventListener("change", fn);
  return () => q.removeEventListener("change", fn);
};

export function useReducedPreference() {
  return useSyncExternalStore(subscribeReduced, reducedSnapshot, () => false);
}

function phaseOf(phases: readonly ScrollPhase[], p: number) {
  let k = 0;
  phases.forEach((ph, i) => {
    if (p >= ph.at) k = i;
  });
  return k;
}

function PhaseBar({ progress, from, to, reduced }: { progress: MotionValue<number>; from: number; to: number; reduced: boolean }) {
  const fill = useTransform(progress, [from, to], [0, 1]);
  return (
    <span className="relative overflow-hidden rounded-full bg-border" aria-hidden>
      <motion.span className="absolute inset-0 origin-top bg-accent" style={{ scaleY: reduced ? 1 : fill }} />
    </span>
  );
}

export function ScrollPhases({ phases, progress, reduced }: { phases: readonly ScrollPhase[]; progress: MotionValue<number>; reduced: boolean }) {
  const [active, setActive] = useState(0);
  const current = useRef(0);
  useMotionValueEvent(progress, "change", (value) => {
    const next = phaseOf(phases, value);
    if (next !== current.current) {
      current.current = next;
      setActive(next);
    }
  });
  const shown = reduced ? phases.length - 1 : active;
  return (
    <ol className="mt-8 space-y-6">
      {phases.map((ph, i) => (
        <li key={ph.title} className="grid grid-cols-[3px_minmax(0,1fr)] gap-4" aria-current={i === shown ? "step" : undefined}>
          <PhaseBar progress={progress} from={ph.at} to={phases[i + 1]?.at ?? 1} reduced={reduced} />
          <div className={cn("transition-opacity duration-300", i === shown ? "opacity-100" : "opacity-45")}>
            <h3 className="text-[16px] font-semibold text-strong">{ph.title}</h3>
            <p className="mt-1 max-w-[44ch] text-[14.5px] leading-relaxed text-muted">{ph.text}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
