"use client";

import { animate, useInView, useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";

/**
 * Número que cuenta hasta su valor la primera vez que se ve, con formato es-ES.
 * Escribe en el DOM directamente (sin re-render por fotograma). Si el valor cambia después,
 * cuenta desde el valor anterior.
 */
export function CountUp({
  value,
  decimals = 0,
  duration = 0.9,
  prefix = "",
  suffix = "",
  className,
}: {
  value: number;
  decimals?: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const seen = useInView(ref, { once: true, margin: "-40px" });
  const reduced = useReducedMotion();
  const last = useRef(0);
  const format = (n: number) =>
    // Agrupación siempre, como lib/format: en es-ES 4800 se escribe 4.800
    prefix + n.toLocaleString("es-ES", { minimumFractionDigits: decimals, maximumFractionDigits: decimals, useGrouping: "always" }) + suffix;

  useEffect(() => {
    const node = ref.current;
    if (!node || !seen) return;
    if (reduced) {
      node.textContent = format(value);
      last.current = value;
      return;
    }
    const controls = animate(last.current, value, {
      duration,
      ease: [0.23, 1, 0.32, 1],
      onUpdate: (n) => {
        node.textContent = format(n);
      },
    });
    last.current = value;
    return () => controls.stop();
    // format depende solo de props ya listadas
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seen, value, reduced, duration, decimals, prefix, suffix]);

  // El lector de pantalla solo oye el valor final, también dentro de una región aria-live
  return (
    <span className={className}>
      <span ref={ref} aria-hidden>
        {format(0)}
      </span>
      <span className="sr-only">{format(value)}</span>
    </span>
  );
}
