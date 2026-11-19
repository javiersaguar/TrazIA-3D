import type { WebGLRenderer } from "three";
import type { Quality } from "./palettes";

/*
  Calidad del entorno cuando el visor no la impone.

  - Por la tarjeta: gráficas integradas, móviles o por software empiezan en "low".
  - Por lo medido: si mientras anima el fotograma medio pasa de ~30 ms (menos de 33 fps) durante
    unos segundos, se baja a "low" una sola vez (nunca se vuelve a subir: sin oscilaciones).
*/

const MODEST_GPU = /intel|iris|uhd|hd graphics|mali|adreno|powervr|apple gpu|swiftshader|llvmpipe|software|basic render|microsoft basic|vivante|videocore/i;

export function rendererName(gl: WebGLRenderer): string {
  try {
    const context = gl.getContext();
    const debug = context.getExtension("WEBGL_debug_renderer_info");
    return String(context.getParameter(debug?.UNMASKED_RENDERER_WEBGL ?? context.RENDERER) ?? "");
  } catch {
    return "";
  }
}

export function qualityForRenderer(name: string, cores = 8): Quality {
  if (!name) return "low";
  if (MODEST_GPU.test(name) && !/arc\s*a?\d|arc\(tm\)/i.test(name)) return "low";
  return cores <= 4 ? "low" : "high";
}

export function detectQuality(gl: WebGLRenderer): Quality {
  const cores = typeof navigator !== "undefined" ? navigator.hardwareConcurrency ?? 8 : 8;
  return qualityForRenderer(rendererName(gl), cores);
}

/** Vigila el coste por fotograma mientras anima; `sample` devuelve true cuando conviene bajar. */
export class FrameBudget {
  private frames: number[] = [];
  constructor(private limitMs = 30, private window = 120) {}
  reset() {
    this.frames = [];
  }
  sample(deltaSeconds: number): boolean {
    const ms = deltaSeconds * 1000;
    // Pausas largas (pestaña oculta, depurador) no cuentan.
    if (ms > 250) return false;
    this.frames.push(ms);
    if (this.frames.length < this.window) return false;
    if (this.frames.length > this.window) this.frames.shift();
    const sorted = [...this.frames].sort((a, b) => a - b);
    const median = sorted[Math.floor(sorted.length / 2)]!;
    return median > this.limitMs;
  }
}
