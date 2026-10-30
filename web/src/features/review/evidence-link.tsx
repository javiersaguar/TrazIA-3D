"use client";

import { useEffect, useRef } from "react";
import styles from "./review.module.css";

/** La conexión sigue los anclajes DOM proyectados por el visor y las cajas PDF visibles. */
export function EvidenceLink({
  path,
  elementId,
}: {
  path: string | null;
  elementId: string | null;
}) {
  const svg = useRef<SVGSVGElement>(null),
    line = useRef<SVGPathElement>(null);
  useEffect(() => {
    const root = svg.current?.parentElement,
      node = line.current;
    if (!root || !node || !path || !elementId) return;
    let frame = 0;
    const draw = () => {
      frame = 0;
      const bounds = root.getBoundingClientRect();
      const get = (selector: string) => {
        const el = root.querySelector<HTMLElement>(selector);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        const scroll = el
          .closest("[data-evidence-scroll]")
          ?.getBoundingClientRect();
        if (
          r.width === 0 ||
          r.height === 0 ||
          r.bottom < bounds.top ||
          r.top > bounds.bottom ||
          (scroll && (r.bottom < scroll.top || r.top > scroll.bottom))
        )
          return null;
        return {
          x: (r.left + r.right) / 2 - bounds.left,
          y: (r.top + r.bottom) / 2 - bounds.top,
        };
      };
      const row = get(`[data-row="${CSS.escape(path)}"]`),
        model = get(`[data-ifc-anchor="${CSS.escape(elementId)}"]`),
        pdf = get(`[data-path="${CSS.escape(path)}"]`);
      const points = [pdf, model, row].filter(
        (p): p is { x: number; y: number } => !!p,
      );
      if (points.length < 2) {
        node.setAttribute("d", "");
        return;
      }
      node.setAttribute(
        "d",
        points
          .map((p, i) => (i ? `L ${p.x} ${p.y}` : `M ${p.x} ${p.y}`))
          .join(" "),
      );
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(draw);
    };
    const observer = new MutationObserver(schedule);
    observer.observe(root, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["style"],
    });
    const resize = new ResizeObserver(schedule);
    resize.observe(root);
    root.addEventListener("scroll", schedule, true);
    schedule();
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches)
      node.animate([{ opacity: 0 }, { opacity: 0.65 }], {
        duration: 240,
        easing: "ease-out",
      });
    return () => {
      observer.disconnect();
      resize.disconnect();
      root.removeEventListener("scroll", schedule, true);
      cancelAnimationFrame(frame);
    };
  }, [path, elementId]);
  return (
    <svg ref={svg} className={styles.connector} aria-hidden="true">
      <path ref={line} />
    </svg>
  );
}
