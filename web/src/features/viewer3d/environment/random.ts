/*
  Azar determinista para los entornos. Nada de Math.random: cada atrezo nace de una semilla fija,
  así dos cargas de la misma planta dan la misma escena y las capturas se pueden comparar.

  `hashUint` es la versión en CPU del hash entero que usan los shaders (`envHash` en glsl.ts):
  con enteros de 32 bits la GPU y la CPU dan exactamente el mismo valor.
*/

/** Generador mulberry32: rápido, 32 bits de estado y bien repartido para atrezo. */
export function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Hash entero (lowbias32). Igual que `envHash` en GLSL. */
export function hashUint(value: number): number {
  let x = value >>> 0;
  x ^= x >>> 16;
  x = Math.imul(x, 0x7feb352d) >>> 0;
  x ^= x >>> 15;
  x = Math.imul(x, 0x846ca68b) >>> 0;
  x ^= x >>> 16;
  return x >>> 0;
}

/** Valor en [0, 1] para una celda entera (x, y). Igual que `envHash2` en GLSL. */
export function hash2(x: number, y: number): number {
  const h = hashUint((Math.imul(x | 0, 0x9e3779b1) ^ hashUint((y | 0) + 0x632be5ab)) >>> 0);
  return h / 4294967295;
}

/** Ayudas para elegir valores con un generador. */
export function picker(random: () => number) {
  return {
    range: (min: number, max: number) => min + (max - min) * random(),
    int: (min: number, max: number) => Math.floor(min + (max - min + 1) * random()),
    sign: () => (random() < 0.5 ? -1 : 1),
    pick: <T,>(items: readonly T[]): T => items[Math.min(items.length - 1, Math.floor(random() * items.length))]!,
  };
}

/** Ruido de valor 2D suave (quíntico) sobre `hash2`, en [0, 1]. Igual que `envValueNoise`. */
export function valueNoise(x: number, y: number): number {
  const ix = Math.floor(x);
  const iy = Math.floor(y);
  const fx = x - ix;
  const fy = y - iy;
  const ux = fx * fx * fx * (fx * (fx * 6 - 15) + 10);
  const uy = fy * fy * fy * (fy * (fy * 6 - 15) + 10);
  const a = hash2(ix, iy);
  const b = hash2(ix + 1, iy);
  const c = hash2(ix, iy + 1);
  const d = hash2(ix + 1, iy + 1);
  return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy;
}
