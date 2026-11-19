import { CanvasTexture, NoColorSpace, RepeatWrapping } from "three";

/*
  Árido del hormigón y del asfalto: ruido de valor en dos escalas para la rugosidad y un relieve
  muy suave para la normal. Datos de superficie, no color: el color viene del estilo IFC.
*/

function valueNoise(size: number, cells: number, seed: number) {
  const grid = new Float32Array((cells + 1) * (cells + 1));
  let state = seed;
  for (let i = 0; i < grid.length; i++) grid[i] = ((state = (Math.imul(1664525, state) + 1013904223) >>> 0) / 4294967296);
  // Borde periódico: la textura se repite sin costura.
  for (let i = 0; i <= cells; i++) { grid[i * (cells + 1) + cells] = grid[i * (cells + 1)]!; grid[cells * (cells + 1) + i] = grid[i]!; }
  const out = new Float32Array(size * size);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const gx = (x / size) * cells, gy = (y / size) * cells;
    const ix = Math.floor(gx), iy = Math.floor(gy);
    const tx = gx - ix, ty = gy - iy;
    const sx = tx * tx * (3 - 2 * tx), sy = ty * ty * (3 - 2 * ty);
    const at = (i: number, j: number) => grid[(iy + j) * (cells + 1) + ix + i]!;
    out[y * size + x] = (at(0, 0) * (1 - sx) + at(1, 0) * sx) * (1 - sy) + (at(0, 1) * (1 - sx) + at(1, 1) * sx) * sy;
  }
  return out;
}

export function grainPixels(size = 128) {
  const broad = valueNoise(size, 8, 7), fine = valueNoise(size, 32, 19);
  const normal = new Uint8ClampedArray(size * size * 4);
  const roughness = new Uint8ClampedArray(size * size * 4);
  const height = (x: number, y: number) => {
    const i = ((y + size) % size) * size + ((x + size) % size);
    return broad[i]! * 0.4 + fine[i]! * 0.6;
  };
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const index = (y * size + x) * 4;
    const dx = height(x + 1, y) - height(x - 1, y), dy = height(x, y + 1) - height(x, y - 1);
    normal.set([128 - dx * 90, 128 - dy * 90, 255, 255], index);
    const speck = ((Math.imul(x + 11, y + 97) >>> 0) % 29) === 0 ? -26 : 0;
    const value = 205 + (height(x, y) - 0.5) * 70 + speck;
    roughness.set([value, value, value, 255], index);
  }
  return { normal, roughness };
}

type Maps = { normalMap: CanvasTexture; roughnessMap: CanvasTexture };
let cached: Maps | undefined;
let users = 0;
let timer: ReturnType<typeof setTimeout> | undefined;

export function grainTextures(): Maps | undefined {
  if (typeof document === "undefined") return undefined;
  if (!cached) {
    const size = 128;
    const data = grainPixels(size);
    const texture = (pixels: Uint8ClampedArray) => {
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = size;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("No se pudo preparar la superficie de hormigón");
      const image = context.createImageData(size, size);
      image.data.set(pixels);
      context.putImageData(image, 0, 0);
      const result = new CanvasTexture(canvas);
      result.wrapS = result.wrapT = RepeatWrapping;
      result.repeat.set(6, 6);
      result.anisotropy = 4;
      result.colorSpace = NoColorSpace;
      return result;
    };
    cached = { normalMap: texture(data.normal), roughnessMap: texture(data.roughness) };
  }
  return cached;
}

export function retainGrainTextures() {
  clearTimeout(timer);
  users++;
  return () => {
    users--;
    if (users === 0) timer = setTimeout(() => {
      if (users !== 0) return;
      cached?.normalMap.dispose();
      cached?.roughnessMap.dispose();
      cached = undefined;
    }, 150);
  };
}
