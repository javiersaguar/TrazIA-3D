import React from 'react';
import { Audio, interpolate, Sequence, staticFile } from 'remotion';
import { LIFT, MORPH, OUTRO, SHOTS, TOTAL } from './timeline';

/*
  Banda sonora. Todo es Freesound CC0 (public/audio/sfx/audio-manifest.json y FREESOUND-CREDITS.md).
  BGM: no hay una pista única «ambient-industrial» CC0 adecuada; se compone a partir de capas
  (dron ambiental → textura mecánica → pulso → riser → impacto → resolución). Las capas BGM se apagan
  con bgm=false (render sin BGM) y los SFX se mantienen.
  Alineado según sound-design §4.6: from = fotograma objetivo − retardo del pico del archivo − desfase de salida AAC.
*/

// Desfase de la pista de salida. Medido el 03/11/2026 sobre el render sin BGM (Remotion 4.0.484, H.264 + AAC 48 kHz, mp4)
// por correlación cruzada de 5 cues (impacto, 3 clics, arpa): +1,27…+1,29 f (≈43 ms). Coincide con la referencia de la skill.
export const OUTPUT_AUDIO_OFFSET_F = 1.28;
const FPS = 30;
const at = (target: number, peakSec: number) => Math.round(target - peakSec * FPS - OUTPUT_AUDIO_OFFSET_F);

type Cue = { id: string; src: string; from: number; dur: number; vol: number | ((f: number) => number); loop?: boolean; bgm?: boolean };
const fs = (id: number) => `audio/sfx/fs-${id}.mp3`;
const env = (pts: [number, number][]) => (f: number) => interpolate(f, pts.map((p) => p[0]), pts.map((p) => p[1]), { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

const IMPACT = LIFT.end - 8; // 762: el acero termina de aparecer
const LOGO_LOCK = OUTRO.logo + 34; // las caras del logo terminan de rellenarse
const DOC_ARRIVALS = [0, 1, 2].map((i) => SHOTS.docs.from + 58 + i * 12 + 22);
const ROW_HITS = [4, 22, 40, 58].map((d) => MORPH.start + d);

// Envolventes en fotogramas relativos al inicio de cada cue
export const CUES: Cue[] = [
  // ── BGM (capas) ──
  { id: 'bgm-drone', src: fs(860432), from: 0, dur: 1120, bgm: true, vol: env([[0, 0], [75, 0.55], [1040, 0.5], [1120, 0]]) },
  { id: 'bgm-mech', src: fs(865628), from: 380, dur: 400, loop: true, bgm: true, vol: env([[0, 0], [90, 0.12], [360, 0.26], [400, 0]]) },
  { id: 'bgm-pulse', src: fs(563043), from: 430, dur: 340, loop: true, bgm: true, vol: env([[0, 0], [80, 0.1], [300, 0.2], [340, 0]]) },
  { id: 'bgm-strings', src: fs(452999), from: 600, dur: 620, bgm: true, vol: env([[0, 0], [150, 0.38], [520, 0.34], [620, 0]]) },
  { id: 'bgm-swell', src: fs(261210), from: 940, dur: 230, bgm: true, vol: env([[0, 0], [40, 0.3], [200, 0.28], [230, 0]]) },
  { id: 'bgm-resolve', src: fs(860432), from: 1185, dur: TOTAL - 1185, bgm: true, vol: env([[0, 0], [30, 0.42], [120, 0.4], [TOTAL - 1185, 0]]) },
  { id: 'bgm-riser', src: fs(334525), from: at(IMPACT, 7.895), dur: 240, bgm: true, vol: env([[0, 0.1], [200, 0.5], [240, 0.5]]) },
  // ── SFX ──
  { id: 'sfx-impact', src: fs(430978), from: at(IMPACT, 0.535), dur: 150, vol: 0.7 },
  { id: 'sfx-paper-1', src: fs(353125), from: at(30, 0.865), dur: 34, vol: 0.3 },
  { id: 'sfx-paper-2', src: fs(353125), from: at(72, 0.865), dur: 34, vol: 0.42 },
  { id: 'sfx-whoosh-brand', src: fs(701104), from: at(SHOTS.brand.from, 0.505), dur: 40, vol: 0.3 },
  { id: 'sfx-lock-brand', src: fs(278205), from: at(SHOTS.brand.from + 4 + 34, 0.035), dur: 12, vol: 0.4 },
  { id: 'sfx-whoosh-docs', src: fs(701104), from: at(SHOTS.docs.from + 12, 0.505), dur: 40, vol: 0.22 },
  ...DOC_ARRIVALS.map((t, i) => ({ id: `sfx-doc-${i}`, src: i % 2 ? fs(556632) : fs(278205), from: at(t, i % 2 ? 0.385 : 0.035), dur: i % 2 ? 30 : 12, vol: [0.38, 0.3, 0.24][i] })),
  { id: 'sfx-origin', src: fs(278205), from: at(SHOTS.origin.from + 58 + 24, 0.035), dur: 12, vol: 0.42 },
  { id: 'sfx-whoosh-3d', src: fs(701104), from: at(604, 0.505), dur: 40, vol: 0.26 },
  { id: 'sfx-whoosh-orbit', src: fs(701104), from: at(958, 0.505), dur: 40, vol: 0.26 },
  ...ROW_HITS.map((t, i) => ({ id: `sfx-row-${i}`, src: i % 2 ? fs(556632) : fs(278205), from: at(t, i % 2 ? 0.385 : 0.035), dur: i % 2 ? 30 : 12, vol: [0.36, 0.3, 0.26, 0.22][i] })),
  { id: 'sfx-harp', src: fs(404124), from: at(LOGO_LOCK, 2.355), dur: 84, vol: 0.5 },
  { id: 'sfx-lock-outro', src: fs(278205), from: at(LOGO_LOCK + 2, 0.035), dur: 12, vol: 0.32 },
];

export const Soundtrack: React.FC<{ bgm: boolean }> = ({ bgm }) => (
  <>
    {CUES.filter((c) => bgm || !c.bgm).map((c) => (
      <Sequence key={c.id} from={c.from} durationInFrames={c.dur} name={c.id} layout="none">
        <Audio src={staticFile(c.src)} volume={c.vol} loop={c.loop} />
      </Sequence>
    ))}
  </>
);
