"use client";

import { AnimatePresence, motion, useInView, useReducedMotion } from "motion/react";
import { useEffect, useState, useRef, useSyncExternalStore } from "react";

import { EASE_OUT } from "@/components/motion/reveal";

const subscribeVisibility = (fn:()=>void) => { document.addEventListener("visibilitychange",fn);return ()=>document.removeEventListener("visibilitychange",fn); };
export const ROTATING_LINES = ["con cada cota trazada.", "con la evidencia de cada campo.", "listo para revisión humana."];

/** Segunda línea del titular: rota cada 3,2 s con un desenfoque breve. Lectores de pantalla: texto fijo. */
export function RotatingLine({ play, className }: { play: boolean; className?: string }) {
  const root = useRef<HTMLSpanElement>(null);
  const visible = useInView(root);
  const pageVisible = useSyncExternalStore(subscribeVisibility,()=>!document.hidden,()=>false);
  const reduced = useReducedMotion();
  const [i, setI] = useState(0);

  useEffect(() => {
    if (!play || !visible || !pageVisible || reduced) return;
    const id = window.setInterval(() => setI((v) => (v + 1) % ROTATING_LINES.length), 3200);
    return () => window.clearInterval(id);
  }, [play, visible, pageVisible, reduced]);

  return (
    <span ref={root} className={className}>
      <span className="sr-only">{ROTATING_LINES[0]}</span>
      <span aria-hidden className="relative block h-[1.2em] overflow-hidden">
        <AnimatePresence initial={false} mode="popLayout">
          <motion.span
            key={i}
            className="absolute inset-x-0 top-0 block whitespace-nowrap"
            initial={{ transform: "translateY(70%)", opacity: 0, filter: "blur(8px)" }}
            animate={{ transform: "translateY(0%)", opacity: 1, filter: "blur(0px)" }}
            exit={{ transform: "translateY(-70%)", opacity: 0, filter: "blur(8px)" }}
            transition={{ duration: 0.55, ease: EASE_OUT }}
          >
            {ROTATING_LINES[i]}
          </motion.span>
        </AnimatePresence>
      </span>
    </span>
  );
}
