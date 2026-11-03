import { useF } from '../lib/frame';
import React from 'react';
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion';
import { EASE_IN, EASE_IO, EASE_OUT, lerp, ramp } from '../lib/anim';
import { C } from '../theme';
import { SHOTS } from '../timeline';

/*
  Escena 1 · «La ingeniería empieza en un plano.»
  Hojas sintéticas del repositorio como objetos 2.5D en una pila axonométrica (depth-layer-moves · multiplane +
  la cámara 3/4 de space-camera-moves · exploded-view, sin el «炸开/合体»): cada hoja se posa desde arriba,
  las capas derivan a velocidades distintas (parallax) y la cámara se acerca hasta el GA V-101.
*/

type Sheet = { src: string; x: number; y: number; z: number; rot: number; w: number; land: number; drift: number; dim: number };
const W = 1180;
const SHEETS: Sheet[] = [
  { src: 'bench/escaneado.webp', x: -760, y: -300, z: 0, rot: -6, w: W, land: 6, drift: 0.4, dim: 0.55 },
  { src: 'bench/plano.webp', x: 640, y: -360, z: 70, rot: 5, w: W, land: 18, drift: 0.7, dim: 0.62 },
  { src: 'bench/rotulado.webp', x: -520, y: 420, z: 140, rot: 3, w: W, land: 30, drift: 1.0, dim: 0.7 },
  { src: 'textures/ga-reva-p1.png', x: 120, y: 40, z: 230, rot: -2, w: 1400, land: 46, drift: 1.4, dim: 1 },
];

export const PlansScene: React.FC = () => {
  const f = useF();
  const end = SHOTS.plans.from + SHOTS.plans.duration;
  // Cámara: inclinación axonométrica que se endereza y se acerca (sin sacudidas)
  const cam = ramp(f, 0, end, EASE_IO);
  const rx = lerp(cam, 56, 38);
  const rz = lerp(cam, -24, -10);
  const zoom = lerp(cam, 0.5, 0.8);
  const pan = lerp(cam, 0, -90);
  const out = 1 - ramp(f, end - 14, end, EASE_IN);
  return (
    <AbsoluteFill style={{ background: C.bg, opacity: out }}>
      {/* Luz cenital fría muy suave */}
      <AbsoluteFill style={{ background: 'radial-gradient(70% 60% at 52% 42%, rgba(92,196,255,0.10), rgba(9,9,11,0) 70%)' }} />
      <AbsoluteFill style={{ perspective: 2600, perspectiveOrigin: '50% 40%' }}>
        <div
          style={{
            position: 'absolute',
            left: 960,
            top: 540,
            width: 0,
            height: 0,
            transformStyle: 'preserve-3d',
            transform: `translateY(${pan}px) scale(${zoom}) rotateX(${rx}deg) rotateZ(${rz}deg)`,
          }}
        >
          {/* Retícula del estudio, como el fondo del visor */}
          <div
            style={{
              position: 'absolute',
              left: -2400,
              top: -2400,
              width: 4800,
              height: 4800,
              backgroundImage: `linear-gradient(${C.border} 2px, transparent 2px), linear-gradient(90deg, ${C.border} 2px, transparent 2px)`,
              backgroundSize: '160px 160px',
              opacity: 0.55 * ramp(f, 0, 30),
              maskImage: 'radial-gradient(closest-side, black, transparent)',
              WebkitMaskImage: 'radial-gradient(closest-side, black, transparent)',
            }}
          />
          {SHEETS.map((s, i) => {
            const land = ramp(f, s.land, s.land + 34, EASE_OUT);
            const h = (s.w * 2971) / 4200;
            const lift = lerp(land, 520, s.z);
            const dx = Math.sin(f / 70 + i) * 10 * s.drift + f * 0.12 * s.drift;
            const dy = f * -0.08 * s.drift;
            return (
              <div
                key={s.src}
                style={{
                  position: 'absolute',
                  left: s.x - s.w / 2 + dx,
                  top: s.y - h / 2 + dy,
                  width: s.w,
                  height: h,
                  transform: `translateZ(${lift}px) rotateZ(${s.rot}deg)`,
                  opacity: land,
                  borderRadius: 6,
                  overflow: 'hidden',
                  background: '#fff',
                  boxShadow: `0 ${30 + s.z / 6}px ${60 + s.z / 3}px rgba(0,0,0,${0.55 * land})`,
                  filter: `brightness(${s.dim})`,
                }}
              >
                <Img src={staticFile(s.src)} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                {/* Degradado de luz sobre el papel */}
                <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(160deg, rgba(255,255,255,0.0) 30%, rgba(9,9,11,0.28) 100%)' }} />
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
      {/* Viñeta para el rótulo */}
      <AbsoluteFill style={{ background: 'linear-gradient(0deg, rgba(9,9,11,0.92) 0%, rgba(9,9,11,0.0) 38%), radial-gradient(120% 90% at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.6) 100%)' }} />
    </AbsoluteFill>
  );
};
