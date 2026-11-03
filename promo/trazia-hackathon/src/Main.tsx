import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { Caption } from './components/Caption';
import { SyntheticBadge } from './components/SyntheticBadge';
import { Soundtrack } from './audio';
import { FrameOffset } from './lib/frame';
import { loadFonts } from './lib/fonts';
import { BrandScene } from './scenes/BrandScene';
import { DocsScene } from './scenes/DocsScene';
import { ModelScene } from './scenes/ModelScene';
import { OriginScene } from './scenes/OriginScene';
import { PlansScene } from './scenes/PlansScene';
import { C } from './theme';
import { CAPTIONS, SHOTS } from './timeline';

loadFonts();

type ShotId = keyof typeof SHOTS;
/** Cada escena se escribe en fotogramas absolutos; la unidad le publica su desplazamiento (también en el workbench). */
const unit = (id: ShotId, Scene: React.FC): React.FC => {
  const U: React.FC = () => (
    <FrameOffset.Provider value={SHOTS[id].from}>
      <Scene />
    </FrameOffset.Provider>
  );
  U.displayName = `Unit(${id})`;
  return U;
};
export const UNITS: Record<ShotId, React.FC> = {
  plans: unit('plans', PlansScene),
  brand: unit('brand', BrandScene),
  docs: unit('docs', DocsScene),
  origin: unit('origin', OriginScene),
  model: unit('model', ModelScene),
};

/** Rótulo como unidad editable: texto y duración son props (el workbench los expone). */
// El workbench puede montar el componente sin `duration` (miniaturas): se usa 90 f por defecto.
export const CaptionUnit: React.FC<{ text: string; duration?: number; size?: number }> = ({ text = '', duration, size = 84 }) => {
  const d = Number.isFinite(Number(duration)) && Number(duration) > 6 ? Number(duration) : 90;
  return (
    <FrameOffset.Provider value={0}>
      <Caption text={text} from={1} to={d - 2} size={Number(size) || 84} />
    </FrameOffset.Provider>
  );
};

export const TraziaPromo: React.FC<{ bgm: boolean }> = ({ bgm }) => (
  <AbsoluteFill style={{ background: C.bg }}>
    {(Object.keys(UNITS) as ShotId[]).map((id) => {
      const U = UNITS[id];
      return (
        <Sequence key={id} from={SHOTS[id].from} durationInFrames={SHOTS[id].duration} name={SHOTS[id].label}>
          <U />
        </Sequence>
      );
    })}
    {CAPTIONS.map((c) => (
      <Sequence key={c.id} from={c.from - 1} durationInFrames={c.to - c.from + 3} name={`Rótulo ${c.id}`}>
        <CaptionUnit text={c.text} duration={c.to - c.from + 3} />
      </Sequence>
    ))}
    <SyntheticBadge />
    <Soundtrack bgm={bgm} />
  </AbsoluteFill>
);
