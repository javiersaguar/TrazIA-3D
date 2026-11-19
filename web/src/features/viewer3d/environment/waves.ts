import { Vector4 } from "three";

/*
  Olas de Gerstner: la misma suma de ondas en la GPU (desplaza la malla del agua) y en la CPU
  (balanceo del buque, cota de la lámina bajo un objeto). Los parámetros salen de aquí y se pasan
  como uniformes, así no hay dos versiones que se desincronicen.

  Convenio: posición base p = (x, z) en metros; cada onda i tiene dirección unitaria D, número de
  onda k = 2π/λ, amplitud A, frecuencia ω = √(g·k) (aguas profundas) y fase φ.
    θ = k (D·p) − ω t + φ
    desplazamiento = (Q A Dx cos θ, A sin θ, Q A Dz cos θ)
  Q se reparte para que Σ Q k A ≤ 1: las crestas se afilan sin dar bucles.
*/

export const GRAVITY = 9.81;

export type WaveSpec = {
  /** Dirección de avance en grados, medida desde +X hacia +Z. */
  direction: number;
  wavelength: number;
  amplitude: number;
  /** Afilado de la cresta entre 0 y 1. */
  chop: number;
  phase: number;
};

export type Wave = {
  dx: number;
  dz: number;
  k: number;
  amplitude: number;
  omega: number;
  phase: number;
  q: number;
  wavelength: number;
};

export const WAVE_COUNT = 8;

/** Mar abierto: mar de fondo largo y mar de viento que cruza (estado de mar 3-4). */
export const OCEAN_WAVES: WaveSpec[] = [
  { direction: 214, wavelength: 74, amplitude: 0.5, chop: 0.62, phase: 0.0 },
  { direction: 238, wavelength: 47, amplitude: 0.33, chop: 0.66, phase: 1.7 },
  { direction: 186, wavelength: 31, amplitude: 0.21, chop: 0.7, phase: 4.1 },
  { direction: 262, wavelength: 19.5, amplitude: 0.13, chop: 0.62, phase: 2.6 },
  { direction: 201, wavelength: 11.8, amplitude: 0.075, chop: 0.55, phase: 5.3 },
  { direction: 247, wavelength: 7.1, amplitude: 0.043, chop: 0.5, phase: 0.9 },
  { direction: 158, wavelength: 4.4, amplitude: 0.025, chop: 0.45, phase: 3.4 },
  { direction: 292, wavelength: 2.7, amplitude: 0.015, chop: 0.4, phase: 1.2 },
];

/** Dársena abrigada: oleaje corto y bajo. */
export const COAST_WAVES: WaveSpec[] = [
  { direction: 152, wavelength: 41, amplitude: 0.15, chop: 0.55, phase: 0.4 },
  { direction: 131, wavelength: 23, amplitude: 0.085, chop: 0.6, phase: 2.2 },
  { direction: 177, wavelength: 13.5, amplitude: 0.05, chop: 0.55, phase: 4.8 },
  { direction: 118, wavelength: 7.8, amplitude: 0.03, chop: 0.5, phase: 1.1 },
  { direction: 196, wavelength: 4.6, amplitude: 0.018, chop: 0.45, phase: 3.7 },
  { direction: 141, wavelength: 2.9, amplitude: 0.011, chop: 0.4, phase: 5.9 },
  { direction: 104, wavelength: 1.9, amplitude: 0.0065, chop: 0.35, phase: 0.6 },
  { direction: 165, wavelength: 1.25, amplitude: 0.004, chop: 0.3, phase: 2.9 },
];

export function buildWaves(specs: readonly WaveSpec[]): Wave[] {
  const count = specs.length;
  return specs.map(spec => {
    const angle = (spec.direction * Math.PI) / 180;
    const k = (Math.PI * 2) / spec.wavelength;
    return {
      dx: Math.cos(angle),
      dz: Math.sin(angle),
      k,
      amplitude: spec.amplitude,
      omega: Math.sqrt(GRAVITY * k),
      phase: spec.phase,
      q: spec.chop / (k * spec.amplitude * count),
      wavelength: spec.wavelength,
    };
  });
}

/** Desplazamiento (dx, dy, dz) del punto base (x, z) en el instante t. */
export function waveDisplacement(waves: readonly Wave[], x: number, z: number, t: number, out: [number, number, number] = [0, 0, 0]) {
  let dx = 0, dy = 0, dz = 0;
  for (const w of waves) {
    const theta = w.k * (w.dx * x + w.dz * z) - w.omega * t + w.phase;
    const c = Math.cos(theta);
    dx += w.q * w.amplitude * w.dx * c;
    dz += w.q * w.amplitude * w.dz * c;
    dy += w.amplitude * Math.sin(theta);
  }
  out[0] = dx; out[1] = dy; out[2] = dz;
  return out;
}

/** Normal unitaria de la superficie desplazada sobre el punto base (x, z). */
export function waveNormal(waves: readonly Wave[], x: number, z: number, t: number): [number, number, number] {
  let nx = 0, ny = 1, nz = 0;
  for (const w of waves) {
    const theta = w.k * (w.dx * x + w.dz * z) - w.omega * t + w.phase;
    const wa = w.k * w.amplitude;
    const c = Math.cos(theta);
    nx -= w.dx * wa * c;
    nz -= w.dz * wa * c;
    ny -= w.q * wa * Math.sin(theta);
  }
  const length = Math.hypot(nx, ny, nz);
  return [nx / length, ny / length, nz / length];
}

/**
  Cota de la lámina en el punto del mundo (x, z). Gerstner mueve los puntos en horizontal: se
  busca el punto base que acaba en (x, z) con unas pocas iteraciones de punto fijo.
*/
export function waveHeightAt(waves: readonly Wave[], x: number, z: number, t: number, iterations = 4): number {
  let px = x, pz = z;
  const d: [number, number, number] = [0, 0, 0];
  for (let i = 0; i < iterations; i++) {
    waveDisplacement(waves, px, pz, t, d);
    px = x - d[0];
    pz = z - d[2];
  }
  return waveDisplacement(waves, px, pz, t, d)[1];
}

export type FloatPose = { heave: number; pitch: number; roll: number };

/**
  Movimiento de un casco que flota: media de la lámina bajo su huella (filtra las olas cortas)
  y pendientes proa-popa y babor-estribor. `response` < 1 amortigua un buque grande o amarrado.
*/
export function floatingPose(
  waves: readonly Wave[],
  x: number,
  z: number,
  heading: number,
  length: number,
  beam: number,
  t: number,
  response = 1,
): FloatPose {
  const fx = Math.cos(heading), fz = Math.sin(heading);
  const sx = -fz, sz = fx;
  const sample = (along: number, across: number) =>
    waveHeightAt(waves, x + fx * along + sx * across, z + fz * along + sz * across, t, 2);
  const stations = [-0.45, -0.15, 0.15, 0.45];
  let bow = 0, stern = 0, port = 0, starboard = 0, sum = 0;
  for (const s of stations) {
    const center = sample(s * length, 0);
    sum += center;
    if (s > 0) bow += center; else stern += center;
  }
  for (const s of [-0.25, 0.25]) {
    port += sample(s * length, beam * 0.5);
    starboard += sample(s * length, -beam * 0.5);
  }
  const heave = (sum / stations.length) * response;
  const pitch = Math.atan2((bow - stern) / 2, length * 0.6) * response;
  const roll = Math.atan2((port - starboard) / 2, beam) * response;
  return { heave, pitch, roll };
}

/** Uniformes para el shader: (Dx, Dz, k, A) y (ω, φ, Q, λ), rellenando hasta WAVE_COUNT. */
export function waveUniforms(waves: readonly Wave[]): { a: Vector4[]; b: Vector4[] } {
  const a: Vector4[] = [];
  const b: Vector4[] = [];
  for (let i = 0; i < WAVE_COUNT; i++) {
    const w = waves[i];
    a.push(w ? new Vector4(w.dx, w.dz, w.k, w.amplitude) : new Vector4(1, 0, 1, 0));
    b.push(w ? new Vector4(w.omega, w.phase, w.q, w.wavelength) : new Vector4(0, 0, 0, 1));
  }
  return { a, b };
}

/** Altura máxima posible (todas las crestas a la vez): cota para el francobordo y las pruebas. */
export function maxAmplitude(waves: readonly Wave[]): number {
  return waves.reduce((sum, w) => sum + w.amplitude, 0);
}

export const WAVES_GLSL = /* glsl */ `
uniform vec4 uWaveA[${WAVE_COUNT}];
uniform vec4 uWaveB[${WAVE_COUNT}];
/* Desplazamiento Gerstner; las ondas más cortas que minLambda se desvanecen (LOD). */
vec3 waveDisplace(vec2 p, float t, float minLambda) {
  vec3 d = vec3(0.0);
  for (int i = 0; i < ${WAVE_COUNT}; i++) {
    vec4 A = uWaveA[i];
    vec4 B = uWaveB[i];
    float fade = smoothstep(minLambda, minLambda * 1.8, B.w);
    float theta = A.z * dot(A.xy, p) - B.x * t + B.y;
    float c = cos(theta);
    d.x += B.z * A.w * A.x * c * fade;
    d.z += B.z * A.w * A.y * c * fade;
    d.y += A.w * sin(theta) * fade;
  }
  return d;
}
/* Normal (sin normalizar) y plegado de la cresta (Σ Q k A sin θ) sobre el punto base. */
vec4 waveNormal(vec2 p, float t, float minLambda) {
  vec3 n = vec3(0.0, 1.0, 0.0);
  float fold = 0.0;
  for (int i = 0; i < ${WAVE_COUNT}; i++) {
    vec4 A = uWaveA[i];
    vec4 B = uWaveB[i];
    float fade = smoothstep(minLambda, minLambda * 1.8, B.w);
    float theta = A.z * dot(A.xy, p) - B.x * t + B.y;
    float wa = A.z * A.w * fade;
    float c = cos(theta);
    float s = sin(theta);
    n.x -= A.x * wa * c;
    n.z -= A.y * wa * c;
    n.y -= B.z * wa * s;
    fold += B.z * wa * s;
  }
  return vec4(n, fold);
}
`;
