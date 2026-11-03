import { PerspectiveCamera, Vector3 } from 'three';
import { EASE_IO, lerp, ramp } from '../../lib/anim';
import { HERO, LIFT, MORPH, OUTRO } from '../../timeline';

// Cámara como función pura del fotograma: la usan el lienzo 3D y las anotaciones HTML (proyección).
export type Pose = { pos: [number, number, number]; target: [number, number, number]; fov: number };

const sph = (az: number, el: number, r: number, t: [number, number, number]): Pose['pos'] => {
  const a = (az * Math.PI) / 180;
  const e = (el * Math.PI) / 180;
  return [t[0] + r * Math.cos(e) * Math.sin(a), t[1] + r * Math.sin(e), t[2] + r * Math.cos(e) * Math.cos(a)];
};
const mix = (p: Pose, q: Pose, t: number): Pose => ({
  pos: [lerp(t, p.pos[0], q.pos[0]), lerp(t, p.pos[1], q.pos[1]), lerp(t, p.pos[2], q.pos[2])],
  target: [lerp(t, p.target[0], q.target[0]), lerp(t, p.target[1], q.target[1]), lerp(t, p.target[2], q.target[2])],
  fov: lerp(t, p.fov, q.fov),
});
// Órbita en coordenadas esféricas (azimut, elevación, radio, objetivo)
type Orb = { az: number; el: number; r: number; t: [number, number, number]; fov: number };
const orb = (o: Orb): Pose => ({ pos: sph(o.az, o.el, o.r, o.t), target: o.t, fov: o.fov });
const mixOrb = (p: Orb, q: Orb, t: number): Orb => ({
  az: lerp(t, p.az, q.az),
  el: lerp(t, p.el, q.el),
  r: lerp(t, p.r, q.r),
  t: [lerp(t, p.t[0], q.t[0]), lerp(t, p.t[1], q.t[1]), lerp(t, p.t[2], q.t[2])],
  fov: lerp(t, p.fov, q.fov),
});

// Plano cenital del papel (12 × 8,5 u), ligeramente oblicuo
const PAPER_A: Pose = { pos: [-0.2, 15.8, 7.6], target: [-0.4, 0, 0.2], fov: 34 };
const PAPER_B: Pose = { pos: [-0.8, 14.2, 7.2], target: [-0.9, 0.3, 0.2], fov: 34 };
// Órbitas sobre el recipiente de pie (altura 0–7,7 m)
const RISE: Orb = { az: 30, el: 20, r: 22, t: [0, 3.6, 0], fov: 32 };
const HERO_A: Orb = { az: 38, el: 13, r: 21, t: [0, 3.85, 0], fov: 32 };
const HERO_B: Orb = { az: 62, el: 7, r: 19.5, t: [0.3, 3.9, 0], fov: 32 };
// Revisión: lado de N3 (−x) y N4 (+z), modelo a la izquierda del encuadre para el panel de Cambios
// (objetivo algo más bajo para que el faldón no toque el rótulo inferior izquierdo)
const DELTA_A: Orb = { az: -24, el: 7, r: 23, t: [3.0, 3.45, 1.1], fov: 32 };
const DELTA_B: Orb = { az: -30, el: 9, r: 22.5, t: [3.0, 3.5, 1.1], fov: 32 };
const END: Orb = { az: -34, el: 10, r: 24, t: [0, 3.9, 0], fov: 32 };

export const poseAt = (f: number): Pose => {
  if (f < LIFT.start) return mix(PAPER_A, PAPER_B, ramp(f, 600, LIFT.start, EASE_IO));
  if (f < HERO.from) {
    // Del papel a la órbita de subida, acompañando el levantamiento
    const t = ramp(f, LIFT.start, HERO.from, EASE_IO);
    return mix(PAPER_B, orb(mixOrb(RISE, HERO_A, t)), t);
  }
  if (f < HERO.to) return orb(mixOrb(HERO_A, HERO_B, ramp(f, HERO.from, HERO.to, (x) => x)));
  if (f < MORPH.start) return orb(mixOrb(HERO_B, DELTA_A, ramp(f, HERO.to, MORPH.start, EASE_IO)));
  if (f < OUTRO.collapse) return orb(mixOrb(DELTA_A, DELTA_B, ramp(f, MORPH.start, OUTRO.collapse, (x) => x)));
  return orb(mixOrb(DELTA_B, END, ramp(f, OUTRO.collapse, OUTRO.collapse + 30, EASE_IO)));
};

const cam = new PerspectiveCamera(32, 1920 / 1080, 0.1, 400);
/** Proyección a píxeles de pantalla (1920×1080) del punto del mundo en el fotograma f. */
export const project = (f: number, p: [number, number, number]) => {
  const pose = poseAt(f);
  cam.fov = pose.fov;
  cam.position.set(...pose.pos);
  cam.lookAt(new Vector3(...pose.target));
  cam.updateProjectionMatrix();
  cam.updateMatrixWorld();
  const v = new Vector3(...p).project(cam);
  return { x: ((v.x + 1) / 2) * 1920, y: ((1 - v.y) / 2) * 1080 };
};
/** Azimut actual en grados (para anclar notas en la cara visible). */
export const azAt = (f: number) => {
  const pose = poseAt(f);
  return (Math.atan2(pose.pos[0] - pose.target[0], pose.pos[2] - pose.target[2]) * 180) / Math.PI;
};
