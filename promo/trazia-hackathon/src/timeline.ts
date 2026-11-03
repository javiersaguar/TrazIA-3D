// Única fuente de verdad del tiempo (fotogramas absolutos @30 fps). SFX, rótulos y workbench derivan de aquí.
export const FPS = 30;
export const TOTAL = 1350;

export const SHOTS = {
  plans: { from: 0, duration: 168, label: 'S1 · Planos en 2.5D' },
  brand: { from: 168, duration: 114, label: 'S2a · Logo TrazIA 3D' },
  docs: { from: 282, duration: 118, label: 'S2b · Documentos → datos' },
  origin: { from: 390, duration: 210, label: 'S3 · Cada dato tiene un origen' },
  model: { from: 600, duration: 750, label: 'S4–S6 · Plano → IFC → cambios → marca' },
} as const;

// Fases del tramo 3D (absolutas)
export const LIFT = { evidence: 618, start: 660, steel: 735, end: 770 }; // levantamiento plano → modelo
export const HERO = { from: 770, to: 930 };
export const MORPH = { start: 990, end: 1080 }; // rev A → rev B
export const OUTRO = { collapse: 1170, logo: 1190, slogan: 1238, sub: 1262 };

export type Caption = { id: string; from: number; to: number; text: string; align?: 'left' | 'center' };
export const CAPTIONS: Caption[] = [
  { id: 'c1', from: 42, to: 160, text: 'La ingeniería empieza en un plano.' },
  { id: 'c2', from: 294, to: 392, text: 'Transformamos documentos en conocimiento.' },
  { id: 'c3', from: 430, to: 594, text: 'Cada dato tiene un origen.' },
  { id: 'c4', from: 790, to: 924, text: 'Del plano al modelo.' },
  { id: 'c5', from: 960, to: 1162, text: 'Cada cambio, bajo control.' },
];

export const SLOGAN = 'Del plano al modelo, con cada cambio trazado.';
export const SUBLINE = 'TrazIA-3D · GA2MODEL';
