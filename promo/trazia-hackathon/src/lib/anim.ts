import { Easing, interpolate } from 'remotion';

export const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);
export const lerp = (t: number, a: number, b: number) => a + (b - a) * t;
// Curvas del preset «confianza técnica»: entrada (0,0,.2,1); movimiento en pantalla = ease de la Signature del producto
export const EASE_OUT = Easing.bezier(0, 0, 0.2, 1);
export const EASE_IO = Easing.bezier(0.65, 0, 0.35, 1);
export const EASE_IN = Easing.bezier(0.4, 0, 1, 1);
/** 0→1 entre dos fotogramas, con curva y recorte. */
export const ramp = (f: number, a: number, b: number, ease: (t: number) => number = EASE_OUT) =>
  interpolate(f, [a, b], [0, 1], { easing: ease, extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
/** Pseudoaleatorio determinista. */
export const mulberry32 = (seed: number) => () => {
  let t = (seed += 0x6d2b79f5);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};
