import { useF } from '../lib/frame';
import React from 'react';
import { useCurrentFrame } from 'remotion';
import { clamp01, ramp } from '../lib/anim';

// Adaptado de demos/effects/scan-bracket-sweep/ScanBracketSweep.tsx (scan-bracket-sweep).
// Se conserva lo que la tarjeta marca como «已知坑»: documento inmóvil, banda recortada al mismo radio que el
// documento, cola con dirección y gradiente invertidos a la vez, cola proporcional a la velocidad (0 en las pausas).
// Escalado: brazo de corchete 64 px (≤ 1/4 del lado corto), 4 pasadas en 84 f (≈ 21 f por pasada, la demo usa ≈ 23 f).
const inOutSin = (x: number) => 0.5 - Math.cos(Math.PI * clamp01(x)) / 2;
const SCAN = '42,168,242';

export const ScanSweep: React.FC<{
  w: number;
  h: number;
  radius?: number;
  bracketsAt: number; // fotograma de caída de corchetes
  scanFrom: number;
  scanTo: number;
  passes?: number;
  ink?: string;
}> = ({ w, h, radius = 10, bracketsAt, scanFrom, scanTo, passes = 4, ink = '#e8f6ff' }) => {
  const f = useF();
  const at = (fr: number) => {
    const sp = clamp01((fr - scanFrom) / (scanTo - scanFrom));
    const raw = sp * passes;
    const pi = Math.min(passes - 1, Math.floor(raw));
    const local = clamp01((raw - pi) / 0.88);
    const dir = pi % 2 === 0 ? 1 : -1;
    const prog = inOutSin(local);
    return { y: dir > 0 ? prog * h : h - prog * h, dir };
  };
  const { y, dir } = at(f);
  const speed = Math.abs(at(f + 0.5).y - at(f - 0.5).y);
  const peak = (h * Math.PI) / 2 / (((scanTo - scanFrom) / passes) * 0.88);
  const tail = 150 * Math.pow(clamp01(speed / peak), 0.75);
  const clipOp = ramp(f, scanFrom - 3, scanFrom + 3) * (1 - ramp(f, scanTo - 2, scanTo + 5));
  const ARM = 64;
  const OFF = 14;
  const corners = [
    { x: -OFF, y: -OFF, d: `M2 ${ARM}V2h${ARM - 2}`, dx: 1, dy: 1 },
    { x: w + OFF - ARM - 2, y: -OFF, d: `M2 2h${ARM - 2}v${ARM - 2}`, dx: -1, dy: 1 },
    { x: w + OFF - ARM - 2, y: h + OFF - ARM - 2, d: `M${ARM} 2v${ARM - 2}H2`, dx: -1, dy: -1 },
    { x: -OFF, y: h + OFF - ARM - 2, d: `M${ARM} ${ARM}H2V2`, dx: 1, dy: -1 },
  ];
  return (
    <>
      <div style={{ position: 'absolute', inset: 0, borderRadius: radius, overflow: 'hidden', opacity: clipOp, pointerEvents: 'none' }}>
        <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: 0, transform: `translateY(${y.toFixed(2)}px)` }}>
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              height: tail,
              top: dir > 0 ? -tail : 0,
              mixBlendMode: 'multiply',
              background:
                dir > 0
                  ? `linear-gradient(180deg, rgba(${SCAN},0) 0%, rgba(${SCAN},0.07) 55%, rgba(${SCAN},0.24) 100%)`
                  : `linear-gradient(0deg, rgba(${SCAN},0) 0%, rgba(${SCAN},0.07) 55%, rgba(${SCAN},0.24) 100%)`,
            }}
          />
          <div style={{ position: 'absolute', left: 0, right: 0, top: -9, height: 18, background: `linear-gradient(180deg, rgba(${SCAN},0) 0%, rgba(${SCAN},0.3) 50%, rgba(${SCAN},0) 100%)` }} />
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: -1.2,
              height: 2.4,
              background: `linear-gradient(90deg, rgba(${SCAN},0.55) 0%, rgb(${SCAN}) 18%, #a6e2ff 50%, rgb(${SCAN}) 82%, rgba(${SCAN},0.55) 100%)`,
              boxShadow: `0 0 5px rgba(${SCAN},0.8)`,
            }}
          />
        </div>
      </div>
      {corners.map((c, i) => {
        const t0 = bracketsAt + i * 3;
        const a = ramp(f, t0, t0 + 4);
        const p = ramp(f, t0, t0 + 8);
        const over = p < 1 ? 1 - p + Math.sin(p * Math.PI) * -0.08 : 0;
        const off = over * 16;
        return (
          <svg
            key={i}
            width={ARM + 4}
            height={ARM + 4}
            style={{ position: 'absolute', left: c.x, top: c.y, overflow: 'visible', opacity: a, transform: `translate(${-off * c.dx}px,${-off * c.dy}px)` }}
          >
            <path d={c.d} fill="none" stroke={ink} strokeWidth={3.2} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        );
      })}
    </>
  );
};
