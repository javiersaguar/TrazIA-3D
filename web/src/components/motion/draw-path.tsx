"use client";

import { motion, useReducedMotion, type SVGMotionProps } from "motion/react";
import { useId } from "react";

type DrawPathProps = SVGMotionProps<SVGPathElement> & {
  /** Retraso en segundos. */
  delay?: number;
  /** Duración del trazo en segundos. */
  duration?: number;
  /** Dibuja al entrar en pantalla (una vez) en lugar de al montarse. */
  inView?: boolean;
};

/**
 * Trazo SVG que se dibuja de principio a fin.
 * - Las líneas discontinuas (eje, ocultas, proyección) conservan su patrón: el avance se anima en
 *   una máscara, porque `pathLength` usa el mismo stroke-dasharray.
 * - Con movimiento reducido el trazo aparece de golpe. La estructura no cambia para que el HTML del
 *   servidor y el del cliente coincidan al hidratar.
 */
export function DrawPath({ delay = 0, duration = 0.9, inView = false, strokeDasharray, ...props }: DrawPathProps) {
  const reduced = useReducedMotion();
  const maskId = `dp${useId().replace(/[^a-zA-Z0-9]/g, "")}`;

  const shown = { pathLength: 1, opacity: 1 };
  const transition = reduced
    ? { duration: 0 }
    : { pathLength: { duration, delay, ease: [0.65, 0, 0.35, 1] as const }, opacity: { duration: 0.01, delay } };
  const trigger = inView ? { whileInView: shown, viewport: { once: true, margin: "-60px" } } : { animate: shown };

  if (strokeDasharray == null) {
    return <motion.path initial={{ pathLength: 0, opacity: 0 }} transition={transition} {...trigger} {...props} />;
  }

  return (
    <>
      {/* Región explícita: Chrome descarta la máscara de un trazo recto (caja de anchura 0) si se deja la de por defecto */}
      <mask id={maskId} maskUnits="userSpaceOnUse" x={-5000} y={-5000} width={10000} height={10000}>
        <motion.path
          d={props.d}
          fill="none"
          stroke="#fff"
          strokeWidth={8}
          strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0 }}
          transition={transition}
          {...trigger}
        />
      </mask>
      <motion.path strokeDasharray={strokeDasharray} mask={`url(#${maskId})`} {...props} />
    </>
  );
}
