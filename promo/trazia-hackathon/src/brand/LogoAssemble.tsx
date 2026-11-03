import { useF } from '../lib/frame';
import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { EASE_IO, EASE_OUT, clamp01, lerp, ramp } from '../lib/anim';
import { C } from '../theme';
import { FULL_VIEWBOX, LOGO_FACES, type LogoFace, type LogoRole } from './logo-geometry';

/*
  Montaje del logo TrazIA 3D por caras, traducido fotograma a fotograma desde
  web/src/components/brand/logo-assemble.tsx (mismos tiempos, curvas y separación radial).
  Variante «slots» (escena 6): antes de encajar, cada hueco se dibuja como contorno discontinuo
  (idea de input-morph-assemble: el destino es un hueco real) y el contorno desaparece al encajar.
*/
const MARK = LOGO_FACES.filter((f) => !f.role.startsWith('w-'));
const WORD = LOGO_FACES.filter((f) => f.role.startsWith('w-'));
const CENTER = { x: 632.5, y: 562.5 };
const ORDER: Partial<Record<LogoRole, number>> = { 't-front': 0, 't-top': 1, 't-end': 2, 't-inner': 2, 'd-outer': 3, 'd-arrow': 4 };

const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const mixHex = (a: string, b: string, t: number) => {
  const A = hex(a);
  const B = hex(b);
  return `rgb(${A.map((v, i) => Math.round(v + (B[i] - v) * t)).join(',')})`;
};
const inkStop = (tone: number) => mixHex(C.logoInkLo, C.logoInkHi, tone);

function centroid(d: string) {
  const n = (d.match(/-?\d+(?:\.\d+)?/g) ?? []).map(Number);
  let x = 0;
  let y = 0;
  let k = 0;
  for (let i = 0; i + 1 < n.length; i += 2) {
    x += n[i];
    y += n[i + 1];
    k++;
  }
  return k ? { x: x / k, y: y / k } : CENTER;
}
const MARK_PARTS = MARK.map((f, i) => {
  const c = centroid(f.d);
  const order = ORDER[f.role] ?? 0;
  const same = MARK.slice(0, i).filter((g) => g.role === f.role).length;
  return { f, dx: (c.x - CENTER.x) * 0.5, dy: (c.y - CENTER.y) * 0.5 - 26, t0: 0.08 + order * 0.075 + same * 0.04, ink: f.role.startsWith('t-') };
});
const WORD_PARTS = WORD.map((f) => ({ f, x: centroid(f.d).x })).sort((a, b) => a.x - b.x);
const WORD_START = 1.05;

const fill = (f: LogoFace, uid: string, i: number) => (f.fill === 'word' ? C.text : f.fill === 'sky' ? C.logoSky : `url(#${uid}-${i})`);

export const LogoAssemble: React.FC<{ start: number; width: number; uid: string; slots?: boolean; sheen?: boolean; style?: React.CSSProperties }> = ({
  start,
  width,
  uid,
  slots = false,
  sheen = true,
  style,
}) => {
  const frame = useF();
  const { fps } = useVideoConfig();
  const s = (frame - start) / fps; // segundos desde el inicio
  const r = (a: number, d: number, e: (t: number) => number = EASE_OUT) => ramp(s, a, a + d, e);
  const [vx, vy, vw, vh] = FULL_VIEWBOX.split(' ').map(Number);
  // Separación inicial algo mayor en la variante con huecos: las caras llegan desde más lejos
  const spread = slots ? 1.6 : 1;
  return (
    <svg viewBox={FULL_VIEWBOX} width={width} height={(width * vh) / vw} style={{ overflow: 'visible', display: 'block', ...style }}>
      <defs>
        {LOGO_FACES.map((f, i) =>
          f.g ? (
            <linearGradient key={i} id={`${uid}-${i}`} gradientUnits="userSpaceOnUse" x1={f.g[0]} y1={f.g[1]} x2={f.g[2]} y2={f.g[3]}>
              <stop offset="0" stopColor={f.ink ? inkStop(f.ink[0]) : f.stops![0]} />
              <stop offset="1" stopColor={f.ink ? inkStop(f.ink[1]) : f.stops![1]} />
            </linearGradient>
          ) : null,
        )}
        <clipPath id={`${uid}-clip`}>
          {MARK.map((f, i) => (
            <path key={i} d={f.d} />
          ))}
        </clipPath>
        <linearGradient id={`${uid}-sheen`} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="#fff" stopOpacity="0" />
          <stop offset="0.5" stopColor="#fff" stopOpacity="0.38" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <radialGradient id={`${uid}-glow`}>
          <stop offset="0" stopColor={C.logoSky} stopOpacity="1" />
          <stop offset="1" stopColor={C.logoSky} stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Huecos discontinuos (solo escena 6) */}
      {slots &&
        MARK_PARTS.map(({ f, t0 }, i) => {
          const a = r(t0 - 0.35, 0.25) * (1 - r(t0 + 0.75, 0.35));
          return a > 0.001 ? (
            <path key={`s${i}`} d={f.d} fill="none" stroke={C.skyLight} strokeOpacity={0.7 * a} strokeWidth={1.4} strokeDasharray="6 6" vectorEffect="non-scaling-stroke" />
          ) : null;
        })}

      {MARK_PARTS.map(({ f, dx, dy, t0, ink }, i) => {
        const draw = r(t0, 0.7, EASE_IO);
        const move = r(t0 + 0.1, 0.95);
        const fo = r(0.72 + t0 * 0.6, 0.45);
        const so = 1 - r(1.1, 0.4);
        const k = (1 - move) * spread;
        if (s < t0) return null;
        return (
          <path
            key={i}
            d={f.d}
            fill={fill(f, uid, LOGO_FACES.indexOf(f))}
            fillOpacity={fo}
            fillRule="evenodd"
            stroke={ink ? C.logoInkHi : C.logoSky}
            strokeOpacity={so}
            strokeWidth={1.25}
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
            pathLength={1}
            strokeDasharray="1 1"
            strokeDashoffset={1 - draw}
            transform={`translate(${(dx * k).toFixed(2)} ${(dy * k).toFixed(2)})`}
          />
        );
      })}

      {sheen && (
        <g clipPath={`url(#${uid}-clip)`}>
          <rect y={230} width={180} height={665} fill={`url(#${uid}-sheen)`} x={lerp(r(1.15, 0.8, EASE_IO), 120, 980)} opacity={s > 1.15 && s < 1.98 ? 1 : 0} />
        </g>
      )}

      {/* Wordmark: letras que suben escalonadas y brillo breve tras «3D» */}
      <g opacity={r(WORD_START, 0.7)} style={{ filter: `blur(${(10 * (1 - r(WORD_START, 0.7))).toFixed(2)}px)` }}>
        <ellipse
          cx={1030}
          cy={973}
          rx={170}
          ry={110}
          fill={`url(#${uid}-glow)`}
          opacity={(() => {
            const g = clamp01((s - WORD_START - 0.45) / 1.1);
            return g < 0.35 ? (0.75 * g) / 0.35 : lerp((g - 0.35) / 0.65, 0.75, 0.22);
          })()}
        />
        {WORD_PARTS.map(({ f }, k) => {
          const p = r(WORD_START + k * 0.05, 0.5);
          return <path key={k} d={f.d} fill={fill(f, uid, LOGO_FACES.indexOf(f))} fillRule="evenodd" opacity={p} transform={`translate(0 ${(34 * (1 - p)).toFixed(2)})`} />;
        })}
      </g>
      <rect x={vx} y={vy} width={0} height={0} />
    </svg>
  );
};
