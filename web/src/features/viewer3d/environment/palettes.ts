/*
  Paletas y luz de cada entorno. Los colores se escriben en sRGB (como se eligen a ojo) y los
  shaders los reciben en lineal. Las distancias van en metros desde el centro de la planta.

  Convenio del sol: azimut en grados desde +Z hacia +X, elevación sobre el horizonte. La vista
  isométrica del visor mira desde +X +Z, así que un azimut cercano a 0° ilumina desde detrás del
  hombro izquierdo del observador: caras visibles con luz y sombras que se alejan de la cámara.
*/

export type EnvironmentId = "ocean" | "coast" | "desert" | "industrial";
export type Quality = "high" | "low";

export type Palette = {
  sun: { azimuth: number; elevation: number; color: string; intensity: number };
  sky: { zenith: string; horizon: string; haze: string; ground: string; sunGlow: number };
  /** Niebla radial: empieza en `near` y llega casi a saturar en `far`. */
  fog: { near: number; far: number; max: number; height: number };
  clouds: { coverage: number; softness: number; scale: number; height: number; tint: string; streak: number };
  hemisphere: { sky: string; ground: string; intensity: number };
  environmentIntensity: number;
  exposure: number;
  /** Dirección (x, z) hacia la que sopla el viento y su velocidad en m/s. */
  wind: [number, number, number];
  /** Cota de la lámina de agua, si la hay. */
  waterLevel: number;
  /** Instante de partida de la animación: también es el fotograma fijo sin movimiento. */
  start: number;
};

export const PALETTES: Record<EnvironmentId, Palette> = {
  ocean: {
    sun: { azimuth: 22, elevation: 34, color: "#fff0dc", intensity: 3.6 },
    sky: { zenith: "#2f63a6", horizon: "#b4cadb", haze: "#c3d3de", ground: "#22394a", sunGlow: 1 },
    fog: { near: 260, far: 3800, max: 0.96, height: 900 },
    clouds: { coverage: 0.42, softness: 0.22, scale: 1, height: 1500, tint: "#f4f6f8", streak: 0.15 },
    hemisphere: { sky: "#9fbfdc", ground: "#1d3445", intensity: 0.45 },
    environmentIntensity: 0.9,
    exposure: 1.05,
    wind: [-0.81, -0.59, 7],
    waterLevel: 0,
    start: 37,
  },
  coast: {
    sun: { azimuth: 12, elevation: 36, color: "#fff2e0", intensity: 3.5 },
    sky: { zenith: "#3c6dab", horizon: "#bccfdc", haze: "#cad7df", ground: "#5a5f55", sunGlow: 0.9 },
    fog: { near: 300, far: 3400, max: 0.95, height: 700 },
    clouds: { coverage: 0.46, softness: 0.25, scale: 1.15, height: 1300, tint: "#f6f7f8", streak: 0.1 },
    hemisphere: { sky: "#a7c3dc", ground: "#4f5248", intensity: 0.45 },
    environmentIntensity: 0.9,
    exposure: 1.05,
    wind: [-0.6, 0.8, 5],
    waterLevel: -0.55,
    start: 24,
  },
  desert: {
    sun: { azimuth: 24, elevation: 29, color: "#ffe3bd", intensity: 3.9 },
    sky: { zenith: "#4b7cb8", horizon: "#e6d8c0", haze: "#e2d0b4", ground: "#c49d72", sunGlow: 1.15 },
    fog: { near: 380, far: 4200, max: 0.93, height: 600 },
    clouds: { coverage: 0.16, softness: 0.35, scale: 0.8, height: 2600, tint: "#fbf3e8", streak: 0.85 },
    hemisphere: { sky: "#b7c9dc", ground: "#b58c62", intensity: 0.5 },
    environmentIntensity: 0.85,
    exposure: 1.0,
    wind: [-0.94, 0.34, 9],
    waterLevel: 0,
    start: 52,
  },
  industrial: {
    sun: { azimuth: 32, elevation: 41, color: "#fff0dd", intensity: 3.3 },
    sky: { zenith: "#5f7fa3", horizon: "#c4cbd1", haze: "#c0c5c8", ground: "#625f58", sunGlow: 0.8 },
    fog: { near: 220, far: 2600, max: 0.95, height: 500 },
    clouds: { coverage: 0.55, softness: 0.3, scale: 1.3, height: 1200, tint: "#eef0f2", streak: 0.25 },
    hemisphere: { sky: "#aebfd0", ground: "#57544e", intensity: 0.5 },
    environmentIntensity: 0.9,
    exposure: 1.08,
    wind: [-0.88, -0.47, 4],
    waterLevel: 0,
    start: 31,
  },
};

const DEG = Math.PI / 180;

/** Vector unitario hacia el sol, en coordenadas del visor (Y arriba). */
export function sunDirection(palette: Palette): [number, number, number] {
  const { azimuth, elevation } = palette.sun;
  const c = Math.cos(elevation * DEG);
  return [c * Math.sin(azimuth * DEG), Math.sin(elevation * DEG), c * Math.cos(azimuth * DEG)];
}

/** Coeficiente de la niebla exponencial para que en `far` llegue al 95 %. */
export function fogDensity(palette: Palette): number {
  return 3 / Math.max(1, palette.fog.far - palette.fog.near);
}

/** Fracción de niebla a una distancia en planta del centro (misma fórmula que el shader). */
export function fogAmount(palette: Palette, distance: number): number {
  const amount = 1 - Math.exp(-Math.max(distance - palette.fog.near, 0) * fogDensity(palette));
  return Math.min(amount, palette.fog.max);
}
