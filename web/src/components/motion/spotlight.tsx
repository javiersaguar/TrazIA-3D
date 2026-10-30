"use client";

import { motion, useReducedMotion, useSpring, useTransform } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";

/**
 * Foco suave que sigue al ratón dentro de su contenedor padre. Decorativo: solo con puntero fino
 * y sin movimiento reducido. El padre debe tener position relative y overflow hidden.
 */
export function Spotlight({ size = 520, className }: { size?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  const [visible, setVisible] = useState(false);
  const x = useSpring(0, { stiffness: 120, damping: 22, mass: 0.6 });
  const y = useSpring(0, { stiffness: 120, damping: 22, mass: 0.6 });
  const left = useTransform(x, (v) => v - size / 2);
  const top = useTransform(y, (v) => v - size / 2);

  useEffect(() => {
    const parent = ref.current?.parentElement;
    if (!parent || reduced || !window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    const move = (e: PointerEvent) => {
      const r = parent.getBoundingClientRect();
      x.set(e.clientX - r.left);
      y.set(e.clientY - r.top);
    };
    const enter = () => setVisible(true);
    const leave = () => setVisible(false);
    parent.addEventListener("pointermove", move);
    parent.addEventListener("pointerenter", enter);
    parent.addEventListener("pointerleave", leave);
    return () => {
      parent.removeEventListener("pointermove", move);
      parent.removeEventListener("pointerenter", enter);
      parent.removeEventListener("pointerleave", leave);
    };
  }, [reduced, x, y]);

  return (
    <motion.div
      ref={ref}
      aria-hidden
      className={cn("pointer-events-none absolute rounded-full transition-opacity duration-500", visible ? "opacity-100" : "opacity-0", className)}
      style={{
        width: size,
        height: size,
        left,
        top,
        background: "radial-gradient(circle at center, rgb(92 196 255 / 0.10), rgb(92 196 255 / 0.04) 35%, transparent 70%)",
      }}
    />
  );
}
