"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";

import { EASE_OUT } from "@/components/motion/reveal";

export const ROTATING_LINES = ["con cada cota trazada.", "con la evidencia de cada campo.", "listo para revisión humana."];

/** Segunda línea del titular: rota cada 3,2 s con un desenfoque breve. Lectores de pantalla: texto fijo. */
export function RotatingLine({ play, className }: { play: boolean; className?: string }) {
  const [i, setI] = useState(0);

  useEffect(() => {
    if (!play) return;
    const id = window.setInterval(() => setI((v) => (v + 1) % ROTATING_LINES.length), 3200);
    return () => window.clearInterval(id);
  }, [play]);

  return (
    <span className={className}>
      <span className="sr-only">{ROTATING_LINES[0]}</span>
      <span aria-hidden className="relative block h-[1.2em] overflow-hidden">
        <AnimatePresence initial={false} mode="popLayout">
          <motion.span
            key={i}
            className="absolute inset-x-0 top-0 block whitespace-nowrap"
            initial={{ y: "70%", opacity: 0, filter: "blur(8px)" }}
            animate={{ y: "0%", opacity: 1, filter: "blur(0px)" }}
            exit={{ y: "-70%", opacity: 0, filter: "blur(8px)" }}
            transition={{ duration: 0.55, ease: EASE_OUT }}
          >
            {ROTATING_LINES[i]}
          </motion.span>
        </AnimatePresence>
      </span>
    </span>
  );
}
