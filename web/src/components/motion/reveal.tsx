"use client";

import { motion, type HTMLMotionProps } from "motion/react";
import { Children, isValidElement, type ReactNode } from "react";

/** Curvas compartidas: ease-out fuerte para entradas, ease-in-out para movimiento en pantalla. */
export const EASE_OUT = [0.23, 1, 0.32, 1] as const;
export const EASE_IN_OUT = [0.77, 0, 0.175, 1] as const;

type RevealProps = HTMLMotionProps<"div"> & {
  /** Retraso en segundos. */
  delay?: number;
  /** Desplazamiento vertical de partida en px. */
  y?: number;
  /** Desenfoque de partida en px (0 = sin desenfoque). */
  blur?: number;
  /** Anima al entrar en pantalla (una vez) en lugar de al montarse. */
  inView?: boolean;
};

/**
 * Aparece subiendo con fundido. Con movimiento reducido, MotionConfig («user») anula el
 * desplazamiento y queda el fundido. Nada depende de la preferencia al pintar, así el HTML del
 * servidor coincide con el del cliente.
 */
export function Reveal({ delay = 0, y = 12, blur = 0, inView = false, children, ...props }: RevealProps) {
  const hidden = { opacity: 0, y, filter: blur ? `blur(${blur}px)` : "blur(0px)" };
  const shown = { opacity: 1, y: 0, filter: "blur(0px)" };
  const transition = { duration: 0.6, delay, ease: EASE_OUT };
  return inView ? (
    <motion.div initial={hidden} whileInView={shown} viewport={{ once: true, margin: "-80px" }} transition={transition} {...props}>
      {children}
    </motion.div>
  ) : (
    <motion.div initial={hidden} animate={shown} transition={transition} {...props}>
      {children}
    </motion.div>
  );
}

/** Escalona la entrada de cada hijo directo (40–80 ms entre ellos). */
export function Stagger({
  children,
  step = 0.06,
  delay = 0,
  y = 10,
  inView = false,
  className,
  itemClassName,
}: {
  children: ReactNode;
  step?: number;
  delay?: number;
  y?: number;
  inView?: boolean;
  className?: string;
  itemClassName?: string;
}) {
  return (
    <div className={className}>
      {Children.toArray(children).map((child, i) => (
        <Reveal key={isValidElement(child) && child.key != null ? child.key : i} delay={delay + i * step} y={y} inView={inView} className={itemClassName}>
          {child}
        </Reveal>
      ))}
    </div>
  );
}
