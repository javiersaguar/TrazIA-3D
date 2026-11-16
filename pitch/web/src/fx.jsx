import React, { useEffect, useLayoutEffect, useState } from "react";
import { animate, m, useMotionValue, useReducedMotion, useTransform } from "motion/react";
import { pitch } from "./pitch-data.js";

export const ease = [0.23, 1, 0.32, 1];
export const easeInOut = [0.77, 0, 0.175, 1];
export const asset = (path) => import.meta.env.BASE_URL + path;

export function useFx() {
  const reduced = useReducedMotion();
  return !reduced && new URLSearchParams(window.location.search).get("fx") !== "0";
}

const angleRest = "scale(1)";
const opacityBlink = [0, 1, 0.5, 1];

export function Esquinas({ delay = 0, spring = false, breathing = false }) {
  const duration = 0.45;
  return (
    <m.span aria-hidden="true" className="fx-corners"
      initial={{ transform: "scale(1.25)", opacity: 0 }}
      animate={{
        transform: spring ? angleRest : ["scale(1.25)", angleRest],
        opacity: opacityBlink,
      }}
      transition={{
        transform: spring ? { type: "spring", duration, bounce: 0.23, delay } : { duration, ease, delay },
        opacity: { duration, times: [0, 0.34, 0.62, 1], ease: "linear", delay },
      }}
    >
      <m.span className="fx-corners-inner"
        initial={breathing ? { transform: angleRest } : false}
        animate={breathing ? { transform: [angleRest, "scale(1.03)", angleRest] } : undefined}
        transition={breathing ? { delay, duration: 0.56, repeat: 1, ease: easeInOut } : undefined}
      >
        <span /><span /><span /><span />
      </m.span>
    </m.span>
  );
}

export function Barrido({ delay = 0, strength = 1, repeat = 0, repeatDelay = 0 }) {
  return (
    <span aria-hidden="true" className="fx-scan-window">
      <m.span className="fx-scan-band"
        initial={{ transform: "translateY(-100%)", opacity: strength }}
        animate={{ transform: ["translateY(-100%)", "translateY(0%)"], opacity: [strength, strength, 0] }}
        transition={{ delay, duration: 0.8, repeat, repeatDelay, ease: "linear" }}
      />
    </span>
  );
}

export function CajaTrazo({ delay = 0, style }) {
  return (
    <span aria-hidden="true" className="fx-trace-area" style={style}>
      <m.span className="fx-trace-box"
        initial={{ clipPath: "inset(0% 100% 100% 0%)" }}
        animate={{ clipPath: "inset(0% 0% 0% 0%)" }}
        transition={{ duration: 0.6, ease: easeInOut, delay }}
      />
      <Esquinas delay={delay + 0.6} />
    </span>
  );
}

export function Contador({ value, format, delay = 0, duration = 0.7, flash = true }) {
  const amount = useMotionValue(0);
  const text = useTransform(amount, format);
  useEffect(() => {
    const animation = animate(amount, value, { delay, duration, ease });
    return () => animation.stop();
  }, [amount, value, delay, duration]);
  return (
    <span className="fx-counter" data-value={format(value)}>
      <m.span className="fx-counter-value">{text}</m.span>
      {flash && <m.span aria-hidden="true" className="fx-counter-flash"
        initial={{ opacity: 0 }}
        animate={{ opacity: [0, 0.54, 0] }}
        transition={{ duration: 0.27, delay: delay + duration, ease }}
      />}
    </span>
  );
}

function equalStops(previous, next) {
  return previous.length === next.length && previous.every(
    (stop, i) => stop.x === next[i].x && stop.y === next[i].y
      && stop.top === next[i].top && stop.left === next[i].left
      && stop.width === next[i].width && stop.height === next[i].height,
  );
}

// offsetTop y offsetLeft se miden en el layout final, al margen de las entradas por transform.
function useStops(container, selector, edge) {
  const [stops, setStops] = useState([]);
  useLayoutEffect(() => {
    const root = container.current;
    if (!root) return;
    const elements = Array.from(root.querySelectorAll(selector));
    const measure = () => {
      const next = elements.map((element) => {
        const { offsetTop: top, offsetLeft: left, offsetWidth: width, offsetHeight: height } = element;
        return { top, left, width, height, x: left + width / 2, y: top + (edge === "bottom" ? height : height / 2) };
      });
      setStops((previous) => equalStops(previous, next) ? previous : next);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(root);
    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, [container, selector, edge]);
  return stops;
}

function TrailDot({ points, delay, duration, small = false }) {
  const positions = points.map(({ x, y }) => `translate(${x}px, ${y}px)`);
  return (
    <m.span className={`fx-route-dot ${small ? "fx-route-dot-small" : ""}`}
      initial={{ transform: positions[0], opacity: 0 }}
      animate={{ transform: positions, opacity: [0, 1, 1, 0] }}
      transition={{
        transform: { delay, duration, ease: "linear" },
        opacity: { delay, duration, times: [0, 0.10, 0.87, 1], ease: "linear" },
      }}
    />
  );
}

export function PuntoRecorrido({ container, delay, interval, stories = false, echoes = false, edge = "bottom" }) {
  const points = useStops(container, "[data-fx-step]", edge);
  if (points.length < 2) return null;
  return (
    <span aria-hidden="true" className={`fx-route ${stories ? "fx-stories" : ""}`}>
      {!stories && points.slice(1).map((next, i) => {
        const from = points[i];
        const dx = next.x - from.x, dy = next.y - from.y;
        return (
          <span key={i} className="fx-route-segment" style={{
            left: from.x, top: from.y, width: Math.hypot(dx, dy), transform: `rotate(${Math.atan2(dy, dx)}rad)`,
          }}>
            <m.span initial={{ transform: "scaleX(0.03)", opacity: 0 }}
              animate={{ transform: "scaleX(1)", opacity: 1 }}
              transition={{ delay: delay + i * interval, duration: interval, ease: "linear" }}
            />
          </span>
        );
      })}
      {points.map(({ x, y, top, left, width, height }, index) => {
        const hit = delay + interval * index;
        return (
          <React.Fragment key={index}>
            <span className="fx-route-pin" style={{ left: x, top: y }}>
              <m.span initial={{ opacity: 0, transform: "scale(.93)" }}
                animate={{ opacity: [0, 1, 0.34], transform: ["scale(.93)", "scale(1.17)", "scale(1)"] }}
                transition={{ delay: hit, duration: 0.36, ease }}
              />
            </span>
            <m.span className="fx-route-highlight" style={{ left, top, width, height }}
              initial={{ opacity: 0 }} animate={{ opacity: [0, 0.7, 0.19] }}
              transition={{ delay: hit, duration: 0.49, ease }}
            />
            {stories && (
              <span className="fx-story-track" style={{ left, top: top + height + 5, width }}>
                <m.span initial={{ transform: "scaleX(0.03)", opacity: 0 }}
                  animate={{ transform: "scaleX(1)", opacity: 1 }}
                  transition={{ delay: hit, duration: interval, ease: "linear" }}
                />
              </span>
            )}
          </React.Fragment>
        );
      })}
      <TrailDot points={points} delay={delay} duration={interval * (points.length - 1)} />
      {echoes && [0.11, 0.22].map((offset) => (
        <TrailDot key={offset} points={points} delay={delay + offset} duration={interval * (points.length - 1)} small />
      ))}
    </span>
  );
}

export function DeltaMarker({ container, delay, interval }) {
  const stops = useStops(container, ".delta-row", "center");
  if (!stops.length) return null;
  const positions = stops.map(({ y }) => `translateY(${y}px)`);
  return (
    <m.span aria-hidden="true" className="fx-delta-marker"
      initial={{ transform: positions[0], opacity: 0 }}
      animate={{ transform: positions, opacity: 1 }}
      transition={{
        transform: { delay, duration: interval * (positions.length - 1), ease: easeInOut },
        opacity: { delay, duration: 0.16, ease },
      }}
    />
  );
}

const inFlight = new Map();

export function usePreloadScene(id) {
  useEffect(() => {
    const files = {
      open: [pitch.media.plan, pitch.media.ifcB],
      input: [pitch.media.plan],
      trace: [pitch.media.evidence],
      model: [pitch.media.plan, pitch.media.outline, pitch.media.ifcB],
      delta: [pitch.media.ifcA, pitch.media.ifcB],
    }[id];
    if (!files?.length) return;
    const timer = setTimeout(() => {
      for (const path of files) {
        const url = asset(path);
        if (inFlight.has(url)) continue;
        const image = new Image();
        image.src = url;
        // Conservar la imagen decodificada evita volver a pagar ese coste al abrir la escena.
        inFlight.set(url, image);
        void image.decode().catch(() => inFlight.delete(url));
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [id]);
}
