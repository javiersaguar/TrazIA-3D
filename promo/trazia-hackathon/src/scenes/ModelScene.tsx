import { useF } from '../lib/frame';
import React, { useContext } from 'react';
import { FrameOffset } from '../lib/frame';
import { ThreeCanvas } from '@remotion/three';
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion';
import { LogoAssemble } from '../brand/LogoAssemble';
import { EASE_IN, EASE_IO, EASE_OUT, lerp, ramp } from '../lib/anim';
import { C, FONT, display } from '../theme';
import { HERO, MORPH, OUTRO, SLOGAN, SUBLINE } from '../timeline';
import { azAt, project } from './model/camera';
import { useModelData } from './model/data';
import { VesselScene } from './model/VesselScene';

// Escenas 4–6: el estudio 3D con el IFC real y las capas HTML (notas, panel de Cambios, marca final).
// Todos los fotogramas son absolutos: este componente se monta en una <Sequence> sin desplazamiento de tiempo.

type Note = { label: string; sub: string; at: (az: number) => [number, number, number]; side: 1 | -1; dy: number; start: number };
const face = (az: number, r: number, y: number): [number, number, number] => [Math.sin((az * Math.PI) / 180) * r, y, Math.cos((az * Math.PI) / 180) * r];
const NOTES: Note[] = [
  { label: 'Cabezal superior', sub: 'V-101/top_head', at: (az) => face(az, 0.7, 7.45), side: 1, dy: -40, start: 806 },
  { label: 'Virola', sub: 'IfcTank · V-101', at: (az) => face(az, 1.0, 5.0), side: 1, dy: 0, start: 816 },
  { label: 'Tobera N1', sub: 'IfcPipeSegment', at: () => [1.39, 2.5, 0], side: 1, dy: 10, start: 826 },
  { label: 'Faldón', sub: 'V-101/skirt', at: (az) => face(az, 1.0, 0.6), side: 1, dy: 30, start: 836 },
];

const Notes: React.FC = () => {
  const f = useF();
  if (f < 800 || f > HERO.to) return null;
  const out = 1 - ramp(f, HERO.to - 22, HERO.to - 6, EASE_IN);
  const az = azAt(f);
  return (
    <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0, opacity: out }}>
      {NOTES.map((n) => {
        const a = project(f, n.at(az));
        const p = ramp(f, n.start, n.start + 16);
        const t = ramp(f, n.start + 8, n.start + 26);
        const bx = 1330;
        const by = a.y + n.dy;
        const mid = a.x + 70;
        return (
          <g key={n.label} opacity={p}>
            <circle cx={a.x} cy={a.y} r={6} fill="#ffffff" />
            <circle cx={a.x} cy={a.y} r={14} fill="none" stroke={C.skyLight} strokeOpacity={0.6} strokeWidth={2} />
            <polyline
              points={`${a.x},${a.y} ${mid},${by} ${bx - 16},${by}`}
              fill="none"
              stroke={C.skyLight}
              strokeWidth={2}
              strokeOpacity={0.85}
              pathLength={1}
              strokeDasharray="1 1"
              strokeDashoffset={1 - p}
            />
            <g opacity={t} transform={`translate(${bx} ${by + (1 - t) * 10})`}>
              <text x={0} y={2} fontFamily={FONT.sans} fontWeight={600} fontSize={34} fill={C.text}>
                {n.label}
              </text>
              <text x={0} y={42} fontFamily={FONT.mono} fontWeight={500} fontSize={28} fill={C.muted}>
                {n.sub}
              </text>
            </g>
          </g>
        );
      })}
    </svg>
  );
};

// Columna «Cambios rev A → rev B» de la captura real (CSS px de la captura 1920×1080 @2x)
// Medido sobre la captura 2x: panel 342,5–741,5 × 342,5–981; tarjetas en x 355,5, ancho 373.
const CROP = { x: 342.5, y: 342.5, w: 399, h: 638.5 };
const CARD = { x: 355.5, w: 373 };
const ROWS = [
  { y: 434.5, h: 99, at: MORPH.start + 4 }, // Longitud entre tangentes +500 mm
  { y: 540.5, h: 99, at: MORPH.start + 22 }, // N3 · elevación +200 mm
  { y: 646.5, h: 119, at: MORPH.start + 40 }, // N4 · boquilla nueva
  { y: 878.5, h: 99, at: MORPH.start + 58 }, // Altura del faldón +150 mm
];
const PANEL = { x: 1260, y: 150, s: 1.24 };

// Cotas sobre el propio modelo, sincronizadas con las filas de Cambios (valores de changes.json y del IFC rev A/B)
const silhouette = (az: number, r: number, y: number): [number, number, number] => {
  const a = (az * Math.PI) / 180;
  return [Math.cos(a) * r, y, -Math.sin(a) * r];
};
const Deltas: React.FC = () => {
  const f = useF();
  if (f < MORPH.start || f > OUTRO.collapse + 4) return null;
  const out = 1 - ramp(f, OUTRO.collapse - 14, OUTRO.collapse, EASE_IN);
  const m = ramp(f, MORPH.start, MORPH.end, EASE_IO);
  const az = azAt(f);
  const vis = (at: number) => ramp(f, at, at + 12) * out;
  const label = (x: number, y: number, title: string, delta: string, o: number, anchor: 'start' | 'end') => (
    <g opacity={o} transform={`translate(${x} ${y + (1 - o) * 8})`}>
      <text x={0} y={-6} textAnchor={anchor} fontFamily={FONT.sans} fontWeight={500} fontSize={28} fill={C.text}>
        {title}
      </text>
      <text x={0} y={34} textAnchor={anchor} fontFamily={FONT.sans} fontWeight={600} fontSize={34} fill={C.revision}>
        {delta}
      </text>
    </g>
  );
  const bracket = (y0: number, y1: number, o: number, key: string) => {
    const a = project(f, silhouette(az, 1.32, y0));
    const b = project(f, silhouette(az, 1.32, y1));
    return (
      <g key={key} opacity={o} stroke={C.revision} strokeWidth={2.5} fill="none">
        <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} />
        <line x1={a.x - 10} y1={a.y} x2={a.x + 10} y2={a.y} />
        <line x1={b.x - 10} y1={b.y} x2={b.x + 10} y2={b.y} />
      </g>
    );
  };
  // Virola 1,2–7,2 → 1,35–7,85 m; faldón 0–1,2 → 0–1,35 m; N3 3,5 → 3,7 m; N4 nueva a 6,2 m (+z)
  const sh0 = lerp(m, 1.2, 1.35);
  const sh1 = lerp(m, 7.2, 7.85);
  const shMid = project(f, silhouette(az, 1.32, (sh0 + sh1) / 2));
  const skMid = project(f, silhouette(az, 1.32, sh0 / 2));
  const n3 = project(f, [-1.36, lerp(m, 3.5, 3.7), 0]);
  const n4 = project(f, [0, 6.2, 1.3]);
  const r = [MORPH.start + 4, MORPH.start + 22, MORPH.start + 40, MORPH.start + 58];
  const lead = (p: { x: number; y: number }, x: number, o: number) => (
    <g opacity={o}>
      <circle cx={p.x} cy={p.y} r={6} fill={C.revision} />
      <line x1={p.x} y1={p.y} x2={x} y2={p.y} stroke={C.revision} strokeWidth={2} />
    </g>
  );
  return (
    <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
      {bracket(sh0, sh1, vis(r[0]), 'shell')}
      {label(shMid.x + 28, shMid.y, 'Longitud entre tangentes', '+500 mm', vis(r[0]), 'start')}
      {lead(n3, n3.x - 90, vis(r[1]))}
      {label(n3.x - 104, n3.y, 'N3 · elevación', '+200 mm', vis(r[1]), 'end')}
      {lead(n4, n4.x - 150 - (n4.x - n3.x), vis(r[2]))}
      {label(n4.x - 164 - (n4.x - n3.x), n4.y, 'N4 · boquilla nueva', 'nueva en rev B', vis(r[2]), 'end')}
      {bracket(0, sh0, vis(r[3]), 'skirt')}
      {label(skMid.x + 28, skMid.y, 'Altura del faldón', '+150 mm', vis(r[3]), 'start')}
    </svg>
  );
};

const ChangesPanel: React.FC = () => {
  const f = useF();
  const inn = ramp(f, 945, 975);
  const out = 1 - ramp(f, OUTRO.collapse - 12, OUTRO.collapse + 4, EASE_IN);
  if (inn <= 0 || out <= 0) return null;
  const s = PANEL.s;
  return (
    <div
      style={{
        position: 'absolute',
        left: PANEL.x,
        top: PANEL.y,
        width: CROP.w * s,
        height: CROP.h * s,
        borderRadius: 12 * s,
        overflow: 'hidden',
        boxShadow: `0 0 0 1px ${C.border}, 0 30px 80px rgba(0,0,0,0.55)`,
        opacity: inn * out,
        transform: `translateX(${(1 - inn) * 40}px)`,
      }}
    >
      <Img
        src={staticFile('captures/cambios.png')}
        style={{ position: 'absolute', width: 1920 * s, height: 1080 * s, left: -CROP.x * s, top: -CROP.y * s, maxWidth: 'none' }}
      />
      {ROWS.map((r, i) => {
        const a = ramp(f, r.at, r.at + 8);
        const settle = 1 - 0.55 * ramp(f, r.at + 8, r.at + 26);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: (CARD.x - CROP.x) * s,
              top: (r.y - CROP.y) * s,
              width: CARD.w * s,
              height: r.h * s,
              borderRadius: 8 * s,
              boxShadow: `0 0 0 ${2.5}px rgba(245,163,92,${(0.95 * a * settle + 0.0).toFixed(3)}), 0 0 28px rgba(245,163,92,${(0.45 * a * settle).toFixed(3)})`,
              background: `rgba(245,163,92,${(0.07 * a * settle).toFixed(3)})`,
            }}
          />
        );
      })}
    </div>
  );
};

const Outro: React.FC = () => {
  const f = useF();
  if (f < OUTRO.logo - 20) return null;
  const glow = ramp(f, OUTRO.collapse + 14, OUTRO.collapse + 30) * (1 - ramp(f, OUTRO.logo + 14, OUTRO.logo + 40));
  const sl = ramp(f, OUTRO.slogan, OUTRO.slogan + 26, EASE_OUT);
  const sub = ramp(f, OUTRO.sub, OUTRO.sub + 24, EASE_OUT);
  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: 960 - 260,
          top: 400 - 260,
          width: 520,
          height: 520,
          borderRadius: 520,
          background: `radial-gradient(closest-side, rgba(92,196,255,${(0.55 * glow).toFixed(3)}), rgba(42,168,242,0))`,
        }}
      />
      <div style={{ position: 'absolute', left: 960 - 330, top: 150 }}>
        <LogoAssemble start={OUTRO.logo} width={660} uid="outro" slots />
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 710, textAlign: 'center', ...display(64), opacity: sl, transform: `translateY(${(1 - sl) * 18}px)` }}>
        {SLOGAN}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 808,
          textAlign: 'center',
          fontFamily: FONT.mono,
          fontWeight: 500,
          fontSize: 32,
          letterSpacing: '0.04em',
          color: C.muted,
          opacity: sub,
        }}
      >
        {SUBLINE}
      </div>
    </AbsoluteFill>
  );
};

export const ModelScene: React.FC = () => {
  const f = useF();
  const data = useModelData();
  const offset = useContext(FrameOffset);
  const fadeIn = ramp(f, 600, 618);
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <AbsoluteFill style={{ opacity: fadeIn }}>
        <ThreeCanvas width={1920} height={1080} camera={{ fov: 32, near: 0.1, far: 400, position: [0, 10, 10] }} gl={{ antialias: true, preserveDrawingBuffer: true }}>
          {data ? <VesselScene data={data} offset={offset} /> : null}
        </ThreeCanvas>
      </AbsoluteFill>
      <Notes />
      <Deltas />
      <ChangesPanel />
      <Outro />
    </AbsoluteFill>
  );
};
