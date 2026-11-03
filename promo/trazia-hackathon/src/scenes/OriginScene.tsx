import { useF } from '../lib/frame';
import React from 'react';
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion';
import { ArrivalPulse, Flyline } from '../components/Flyline';
import { EASE_IN, EASE_IO, EASE_OUT, lerp, ramp } from '../lib/anim';
import { C, FONT } from '../theme';
import { SHOTS } from '../timeline';

/*
  Escena 3 · «Cada dato tiene un origen.»
  Captura real de Revisión con «Diámetro de la virola 2.000 mm» seleccionado (la app ya enlaza campo, plano y 3D).
  La cámara se acerca a la cola de revisión; un recorte ampliado del GA sintético muestra la línea de origen y una
  flyline (flyline-arc) une el valor con su bbox real (GA-V101 · pág. 1).
*/
const S = SHOTS.origin.from;
const END = S + SHOTS.origin.duration;
// Coordenadas CSS de la captura (1920×1080)
const VALUE = { x: 1757, y: 482 };
const ROW = { x: 1389, y: 461, w: 416, h: 129 };
const PIVOT = { x: 1500, y: 520 };
// Recorte del GA (px de la textura 4200×2971) alrededor de la tabla de parámetros
const GA = { w: 4200, h: 2971 };
const CROP = { x: 1700, y: 470, w: 1050, h: 640 };
const BOX = [0.4284, 0.2166, 0.534, 0.2309]; // equipment.diameter
const CARD = { x: 150, y: 160, w: 860 };
const CH = (CARD.w * CROP.h) / CROP.w;
const k = CARD.w / CROP.w;

export const OriginScene: React.FC = () => {
  const f = useF();
  const inn = ramp(f, S, S + 12);
  const out = 1 - ramp(f, END - 16, END, EASE_IN);
  const zoom = lerp(ramp(f, S, END, EASE_IO), 1.0, 1.16);
  const tx = (p: { x: number; y: number }) => ({ x: PIVOT.x + (p.x - PIVOT.x) * zoom, y: PIVOT.y + (p.y - PIVOT.y) * zoom });
  const v = tx(VALUE);
  const r0 = tx({ x: ROW.x, y: ROW.y });
  const card = ramp(f, S + 26, S + 50, EASE_OUT);
  const bx = CARD.x + (BOX[0] * GA.w - CROP.x) * k;
  const by = CARD.y + (BOX[1] * GA.h - CROP.y) * k;
  const bw = (BOX[2] - BOX[0]) * GA.w * k;
  const bh = (BOX[3] - BOX[1]) * GA.h * k;
  const FL = S + 58;
  return (
    <AbsoluteFill style={{ background: C.bg, opacity: inn * out }}>
      <Img
        src={staticFile('captures/revision.png')}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          transformOrigin: `${PIVOT.x}px ${PIVOT.y}px`,
          transform: `scale(${zoom})`,
          filter: `brightness(${lerp(ramp(f, S + 20, S + 44), 1, 0.5)})`,
        }}
      />
      {/* La fila seleccionada se mantiene a brillo completo */}
      <div style={{ position: 'absolute', left: r0.x, top: r0.y, width: ROW.w * zoom, height: ROW.h * zoom, overflow: 'hidden', borderRadius: 10 * zoom }}>
        <Img
          src={staticFile('captures/revision.png')}
          style={{ position: 'absolute', width: 1920 * zoom, height: 1080 * zoom, left: -ROW.x * zoom, top: -ROW.y * zoom, maxWidth: 'none' }}
        />
      </div>
      {/* Recorte ampliado del GA sintético con la evidencia */}
      <div
        style={{
          position: 'absolute',
          left: CARD.x,
          top: CARD.y,
          width: CARD.w,
          height: CH,
          borderRadius: 14,
          overflow: 'hidden',
          background: '#fff',
          boxShadow: `0 0 0 1px ${C.border}, 0 40px 100px rgba(0,0,0,0.65)`,
          opacity: card,
          transform: `scale(${lerp(card, 0.94, 1)})`,
          transformOrigin: '30% 50%',
        }}
      >
        <Img src={staticFile('textures/ga-reva-p1.png')} style={{ position: 'absolute', width: GA.w * k, height: GA.h * k, left: -CROP.x * k, top: -CROP.y * k, maxWidth: 'none' }} />
        <div
          style={{
            position: 'absolute',
            left: bx - CARD.x - 8,
            top: by - CARD.y - 6,
            width: bw + 16,
            height: bh + 12,
            borderRadius: 6,
            background: `rgba(42,168,242,${(0.18 * ramp(f, FL + 20, FL + 28)).toFixed(3)})`,
          }}
        />
      </div>
      <div style={{ position: 'absolute', left: CARD.x, top: CARD.y + CH + 22, fontFamily: FONT.mono, fontSize: 32, color: C.text, opacity: ramp(f, FL + 24, FL + 40) }}>
        <span style={{ color: C.skyLight }}>GA-V101</span> · pág. 1 · evidencia del campo
      </div>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        <ArrivalPulse at={S + 14} id="rowp" r={12} rect={{ x: r0.x, y: r0.y, w: ROW.w * zoom, h: ROW.h * zoom }} />
        <Flyline id="ofl" start={FL} dur={24} p0={{ x: v.x - 70, y: v.y }} p1={{ x: v.x - 360, y: v.y - 260 }} p2={{ x: bx + bw + 380, y: by - 120 }} p3={{ x: bx + bw + 8, y: by + bh / 2 }} />
        <ArrivalPulse at={FL + 24} id="boxp" r={6} rect={{ x: bx - 8, y: by - 6, w: bw + 16, h: bh + 12 }} />
      </svg>
      <AbsoluteFill style={{ background: 'linear-gradient(0deg, rgba(9,9,11,0.95) 0%, rgba(9,9,11,0) 32%)' }} />
    </AbsoluteFill>
  );
};
