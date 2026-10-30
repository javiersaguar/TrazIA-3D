import { CanvasTexture, NoColorSpace, RepeatWrapping } from "three";

/** Datos de superficie, no pigmentos: los colores de los materiales vienen de brand.ts. */
export function brushedPixels(size = 256) {
  const normal = new Uint8ClampedArray(size * size * 4);
  const roughness = new Uint8ClampedArray(size * size * 4);
  for (let y = 0; y < size; y++) {
    const groove = Math.sin(y / size * Math.PI * 62) * 10 + Math.sin(y / size * Math.PI * 106) * 4;
    for (let x = 0; x < size; x++) {
      const index = (y * size + x) * 4;
      const grain = ((Math.imul(x + 31, y + 173) >>> 0) % 13) - 6;
      normal.set([128 + grain * .3, 128 + groove, 254, 255], index);
      const value = 224 + groove * .35 + grain;
      roughness.set([value, value, value, 255], index);
    }
  }
  return { normal, roughness };
}

type Maps = { normalMap: CanvasTexture; roughnessMap: CanvasTexture };
let cached: Maps | undefined;
let users = 0;
let timer: ReturnType<typeof setTimeout> | undefined;

export function brushedTextures(): Maps | undefined {
  if (typeof document === "undefined") return undefined;
  if (!cached) {
    const data = brushedPixels();
    const texture = (pixels: Uint8ClampedArray) => {
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = 256;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("No se pudo preparar la superficie de acero");
      const image = context.createImageData(256, 256);
      image.data.set(pixels);
      context.putImageData(image, 0, 0);
      const result = new CanvasTexture(canvas);
      result.wrapS = result.wrapT = RepeatWrapping;
      result.repeat.set(4, 8);
      result.anisotropy = 4;
      result.colorSpace = NoColorSpace;
      return result;
    };
    cached = { normalMap: texture(data.normal), roughnessMap: texture(data.roughness) };
  }
  return cached;
}

export function retainBrushedTextures() {
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
