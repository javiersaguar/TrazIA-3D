import { useF } from '../lib/frame';
import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { LogoAssemble } from '../brand/LogoAssemble';
import { EASE_IN, ramp } from '../lib/anim';
import { C } from '../theme';
import { SHOTS } from '../timeline';

// Escena 2a · el logo real se monta por caras (misma coreografía que la intro de la web) y se queda quieto > 1 s.
export const BRAND_START = SHOTS.brand.from + 4;
export const BrandScene: React.FC = () => {
  const f = useF();
  const end = SHOTS.brand.from + SHOTS.brand.duration;
  const out = 1 - ramp(f, end - 12, end, EASE_IN);
  return (
    <AbsoluteFill style={{ background: C.bg, opacity: out }}>
      <AbsoluteFill style={{ background: 'radial-gradient(45% 45% at 50% 46%, rgba(76,186,249,0.08), rgba(9,9,11,0) 70%)' }} />
      <div style={{ position: 'absolute', left: 960 - 380, top: 250 }}>
        <LogoAssemble start={BRAND_START} width={760} uid="brand" sheen={false} />
      </div>
    </AbsoluteFill>
  );
};
