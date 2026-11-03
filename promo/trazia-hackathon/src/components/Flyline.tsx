import { useF } from '../lib/frame';
import React from 'react';
import { Easing, interpolate, useCurrentFrame } from 'remotion';

// Adaptado de demos/effects/glow-flyline-moves/FlylineArc.tsx (flyline-arc): crecimiento 22 f out-cubic,
// cabeza con halo y cometa solo mientras crece, cola oscura que se iguala 10 f tras llegar, nodo final fijo.
// Color: celeste del producto en lugar del índigo de la demo.
type Pt = { x: number; y: number };
const bez = (p0: Pt, p1: Pt, p2: Pt, p3: Pt, t: number): Pt => {
  const u = 1 - t;
  return {
    x: u * u * u * p0.x + 3 * u * u * t * p1.x + 3 * u * t * t * p2.x + t * t * t * p3.x,
    y: u * u * u * p0.y + 3 * u * u * t * p1.y + 3 * u * t * t * p2.y + t * t * t * p3.y,
  };
};
const N = 100;
const GLOW = '42,168,242';
const cl = { extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const };

export const Flyline: React.FC<{ start: number; p0: Pt; p1: Pt; p2: Pt; p3: Pt; dur?: number; id: string; scale?: number }> = ({
  start,
  p0,
  p1,
  p2,
  p3,
  dur = 22,
  id,
  scale = 1,
}) => {
  const frame = useF();
  if (frame < start) return null;
  const e = interpolate(frame, [start, start + dur], [0, 1], { easing: Easing.out(Easing.cubic), ...cl });
  const growing = frame < start + dur;
  const settle = interpolate(frame, [start + dur, start + dur + 10], [0, 1], { easing: Easing.out(Easing.quad), ...cl });
  const anchor = interpolate(frame, [start, start + 6], [0, 1], { easing: Easing.out(Easing.cubic), ...cl });
  const pts: Pt[] = [];
  const nDrawn = Math.max(2, Math.ceil(e * N) + 1);
  for (let i = 0; i < nDrawn; i++) pts.push(bez(p0, p1, p2, p3, Math.min(i / N, e)));
  const head = bez(p0, p1, p2, p3, e);
  pts[pts.length - 1] = head;
  const poly = pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const segs = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const tSeg = Math.min(i / N, e) / Math.max(e, 0.001);
    const grad = 0.3 + 0.7 * tSeg * tSeg;
    segs.push(
      <line key={i} x1={pts[i].x} y1={pts[i].y} x2={pts[i + 1].x} y2={pts[i + 1].y} stroke="#eaf7ff" strokeWidth={3 * scale} strokeOpacity={grad + (1 - grad) * settle} />,
    );
  }
  const comet = pts.slice(Math.max(0, pts.length - 9)).map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  return (
    <g>
      <defs>
        <radialGradient id={id}>
          <stop offset="0%" stopColor="rgba(255,255,255,0.6)" />
          <stop offset="30%" stopColor="rgba(120,205,255,0.3)" />
          <stop offset="100%" stopColor="rgba(42,168,242,0)" />
        </radialGradient>
      </defs>
      <circle cx={p0.x} cy={p0.y} r={9 * anchor * scale} fill={`rgba(${GLOW},0.28)`} />
      <circle cx={p0.x} cy={p0.y} r={4.5 * anchor * scale} fill="#ffffff" />
      <polyline points={poly} fill="none" stroke={`rgb(${GLOW})`} strokeWidth={16 * scale} strokeLinecap="round" strokeLinejoin="round" strokeOpacity={0.1 + 0.04 * settle} />
      <polyline points={poly} fill="none" stroke="rgb(92,196,255)" strokeWidth={6 * scale} strokeLinecap="round" strokeLinejoin="round" strokeOpacity={0.26} />
      {segs}
      {growing ? (
        <g>
          <polyline points={comet} fill="none" stroke="#ffffff" strokeWidth={6 * scale} strokeLinecap="round" strokeOpacity={0.55} />
          <circle cx={head.x} cy={head.y} r={40 * scale} fill={`url(#${id})`} />
          <circle cx={head.x} cy={head.y} r={7 * scale} fill="#ffffff" />
        </g>
      ) : (
        <g>
          <circle cx={p3.x} cy={p3.y} r={11 * scale} fill={`rgba(${GLOW},0.25)`} />
          <circle cx={p3.x} cy={p3.y} r={5 * scale} fill="#ffffff" />
        </g>
      )}
    </g>
  );
};

/** Pulso al llegar (CardPulse de la demo): borde celeste + halo + anillo de impacto. Coordenadas SVG. */
export const ArrivalPulse: React.FC<{ at: number; rect: { x: number; y: number; w: number; h: number }; r?: number; id: string }> = ({ at, rect, r = 12, id }) => {
  const frame = useF();
  if (frame < at) return null;
  const amp =
    frame <= at + 6
      ? interpolate(frame, [at, at + 6], [0, 1], { easing: Easing.out(Easing.cubic), ...cl })
      : interpolate(frame, [at + 6, at + 18], [1, 0.35], { easing: Easing.out(Easing.quad), ...cl });
  const ring = interpolate(frame, [at, at + 14], [0, 1], { easing: Easing.out(Easing.cubic), ...cl });
  const cx = rect.x + rect.w / 2;
  const cy = rect.y + rect.h / 2;
  return (
    <g>
      <defs>
        <filter id={id} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation={10} />
        </filter>
      </defs>
      <rect x={rect.x} y={rect.y} width={rect.w} height={rect.h} rx={r} fill="none" stroke={`rgb(${GLOW})`} strokeWidth={8} strokeOpacity={0.55 * amp} filter={`url(#${id})`} />
      <rect x={rect.x + 0.75} y={rect.y + 0.75} width={rect.w - 1.5} height={rect.h - 1.5} rx={r} fill="none" stroke="#9bdcff" strokeWidth={2} strokeOpacity={0.95 * amp} />
      {ring < 1 && <circle cx={cx} cy={cy} r={12 + 80 * ring} fill="none" stroke="#9bdcff" strokeWidth={2.5 * (1 - ring) + 0.5} strokeOpacity={0.7 * (1 - ring)} />}
    </g>
  );
};
