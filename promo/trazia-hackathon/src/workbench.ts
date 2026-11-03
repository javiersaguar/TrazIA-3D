// Manifiesto del Motion Workbench (video-shotcraft references/workbench.md §2). Mismas tablas que Main.tsx.
import { CUES } from './audio';
import { SyntheticBadge } from './components/SyntheticBadge';
import { CaptionUnit, TraziaPromo, UNITS } from './Main';
import { C } from './theme';
import { CAPTIONS, FPS, SHOTS, TOTAL } from './timeline';

const ids = Object.keys(SHOTS) as (keyof typeof SHOTS)[];

export const WORKBENCH = {
  name: 'TrazIA-3D · GA2MODEL · borrador 45 s',
  fps: FPS,
  width: 1920,
  height: 1080,
  total: TOTAL,
  background: C.bg,
  shots: ids.map((id) => ({ id, label: SHOTS[id].label, from: SHOTS[id].from, duration: SHOTS[id].duration, component: UNITS[id] })),
  captions: CAPTIONS.map((c) => ({
    id: c.id,
    label: `Rótulo · ${c.text}`,
    from: c.from - 1,
    duration: c.to - c.from + 3,
    component: CaptionUnit,
    props: { text: c.text, duration: c.to - c.from + 3, size: 84 },
    schema: [
      { type: 'textarea', key: 'text', label: 'Texto', default: '' },
      { type: 'number', key: 'size', label: 'Tamaño', min: 56, max: 120, step: 2, unit: 'px', default: 84 },
    ],
    durationProp: 'duration',
    cardId: 'caption',
    cardName: 'Rótulo',
  })),
  overlays: [{ id: 'synthetic', label: 'Aviso · datos sintéticos', from: 0, duration: TOTAL, component: SyntheticBadge }],
  sfx: CUES.filter((c) => !c.bgm).map((c) => ({ from: c.from, duration: c.dur, src: c.src, volume: typeof c.vol === 'number' ? c.vol : 0.5 })),
  bgm: CUES.filter((c) => c.bgm).map((c) => ({ from: c.from, duration: c.dur, src: c.src, volume: typeof c.vol === 'number' ? c.vol : 0.35 })),
  order: ['transitions', 'captions', 'overlays'],
  original: TraziaPromo,
};
