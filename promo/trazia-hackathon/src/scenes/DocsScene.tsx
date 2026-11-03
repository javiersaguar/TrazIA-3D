import { useF } from '../lib/frame';
import React from 'react';
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion';
import { ArrivalPulse, Flyline } from '../components/Flyline';
import { ScanSweep } from '../components/ScanSweep';
import { EASE_IN, EASE_IO, EASE_OUT, lerp, ramp } from '../lib/anim';
import { C, FONT } from '../theme';
import { SHOTS } from '../timeline';

/*
  Escena 2b · «Transformamos documentos en conocimiento.»
  Captura real de Documentos en 2.5D; el GA V-101 rev A sale de la bandeja, se lee (scan-bracket-sweep)
  y tres flylines (flyline-arc) lo unen a los campos extraídos, con los valores y nombres que muestra la app.
*/
const S = SHOTS.docs.from;
const SHEET = { x: 130, y: 120, w: 820 };
const SH = (SHEET.w * 2971) / 4200;
// Evidencias (bbox normalizado de la página, evidence-rev-a.json)
const EV = [
  { label: 'Diámetro de la virola', value: '2.000 mm', box: [0.4284, 0.2166, 0.534, 0.2309], y: 200 },
  { label: 'Longitud entre tangentes', value: '6.000 mm', box: [0.4284, 0.2487, 0.52, 0.2629], y: 340 },
  { label: 'Altura del faldón', value: '1.200 mm', box: [0.4284, 0.3128, 0.5552, 0.3271], y: 480 },
];
const CHIP = { x: 1150, w: 660, h: 104 };

export const DocsScene: React.FC = () => {
  const f = useF();
  const end = S + SHOTS.docs.duration;
  const inn = ramp(f, S, S + 10);
  const out = 1 - ramp(f, end - 12, end, EASE_IN);
  const cam = ramp(f, S, end, (x) => x);
  const dim = lerp(ramp(f, S + 4, S + 22, EASE_IO), 1, 0.38);
  const pop = ramp(f, S + 8, S + 20, EASE_OUT);
  return (
    <AbsoluteFill style={{ background: C.bg, opacity: inn * out }}>
      <AbsoluteFill style={{ perspective: 2400 }}>
        <Img
          src={staticFile('captures/documentos.png')}
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transformOrigin: '60% 60%',
            transform: `translateZ(${lerp(cam, -120, -40)}px) rotateX(${lerp(cam, 14, 10)}deg) rotateY(${lerp(cam, -12, -8)}deg)`,
            filter: `brightness(${dim})`,
            borderRadius: 14,
          }}
        />
      </AbsoluteFill>
      {/* GA V-101 rev A: la misma hoja de la bandeja, quieta mientras se lee */}
      <div
        style={{
          position: 'absolute',
          left: SHEET.x,
          top: SHEET.y,
          width: SHEET.w,
          height: SH,
          transform: `scale(${lerp(pop, 0.86, 1)})`,
          opacity: Math.min(1, pop * 3),
          transformOrigin: '50% 50%',
        }}
      >
        <div style={{ position: 'absolute', inset: 0, borderRadius: 10, overflow: 'hidden', background: '#fff', boxShadow: '0 40px 90px rgba(0,0,0,0.6)' }}>
          <Img src={staticFile('textures/ga-reva-p1.png')} style={{ width: '100%', height: '100%', display: 'block' }} />
        </div>
        <ScanSweep w={SHEET.w} h={SH} radius={10} bracketsAt={S + 18} scanFrom={S + 22} scanTo={S + 102} passes={4} />
        <div style={{ position: 'absolute', left: 0, top: SH + 24, fontFamily: FONT.mono, fontSize: 30, color: C.muted, opacity: pop }}>
          GAD_V-101_revA.pdf · pág. 1
        </div>
      </div>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        {EV.map((e, i) => {
          const start = S + 58 + i * 12;
          const rect = {
            x: SHEET.x + e.box[0] * SHEET.w - 6,
            y: SHEET.y + e.box[1] * SH - 5,
            w: (e.box[2] - e.box[0]) * SHEET.w + 12,
            h: (e.box[3] - e.box[1]) * SH + 10,
          };
          const bx = rect.x + rect.w;
          const by = rect.y + rect.h / 2;
          const cx = CHIP.x;
          const cy = e.y + CHIP.h / 2;
          return (
            <g key={e.label}>
              <ArrivalPulse at={start - 2} id={`evp${i}`} r={4} rect={rect} />
              <Flyline id={`dfl${i}`} start={start} p0={{ x: bx, y: by }} p1={{ x: bx + 170, y: by - 30 }} p2={{ x: cx - 170, y: cy + 30 }} p3={{ x: cx, y: cy }} />
            </g>
          );
        })}
      </svg>
      {EV.map((e, i) => {
        const at = S + 58 + i * 12 + 18;
        const a = ramp(f, at, at + 14);
        return (
          <div
            key={e.label}
            style={{
              position: 'absolute',
              left: CHIP.x,
              top: e.y,
              width: CHIP.w,
              height: CHIP.h,
              boxSizing: 'border-box',
              padding: '0 30px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderRadius: 12,
              background: C.surface,
              boxShadow: `0 0 0 1px ${C.border}, 0 20px 50px rgba(0,0,0,0.5)`,
              opacity: a,
              transform: `translateY(${(1 - a) * 14}px)`,
            }}
          >
            <span style={{ fontFamily: FONT.sans, fontWeight: 500, fontSize: 32, color: C.text }}>{e.label}</span>
            <span style={{ fontFamily: FONT.mono, fontWeight: 500, fontSize: 34, color: C.skyLight }}>{e.value}</span>
          </div>
        );
      })}
      <AbsoluteFill style={{ background: 'linear-gradient(0deg, rgba(9,9,11,0.95) 0%, rgba(9,9,11,0) 30%)' }} />
    </AbsoluteFill>
  );
};
