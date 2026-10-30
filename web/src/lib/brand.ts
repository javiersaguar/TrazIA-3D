/*
  Colores de marca en hex para three.js, canvas y SVG, donde no llegan las variables CSS.
  Deben coincidir con src/styles/tokens.css (paleta acordada en docs/PLAN_FRONTEND.md).
  Dueño: Agente 1. El 3D los lee; si falta un color, se pide aquí en lugar de inventarlo.
*/

export const BRAND = {
  /** Fondo negro de la app y de las escenas 3D. */
  black: "#09090b",
  surface: "#111113",
  surfaceRaised: "#18181b",
  border: "#222226",
  /** Caras negras de la T del logo y su versión grafito para fondos oscuros. */
  logoInk: "#0b0b0d",
  logoInkSoft: "#3d3d40",
  logoGraphite: "#e9e9ec",
  logoGraphiteSoft: "#9c9ca4",
  /** Celeste del logo: acento, selección y holograma. */
  sky: "#2aa8f2",
  skyLight: "#5cc4ff",
  skyPale: "#95ddfc",
  skyDeep: "#035793",
  hologram: "#3db4ff",
  /** Acero de los modelos y pintura de equipos. */
  steel: "#a7adb5",
  steelDark: "#6b737d",
  paint: "#8d99a6",
  /** Semánticos: cada uno significa una sola cosa. */
  revision: "#f5a35c",
  approved: "#5cc08f",
  danger: "#f07468",
  warning: "#e8b44c",
  text: "#f4f4f5",
  textMuted: "#a1a1aa",
} as const;

export type BrandColor = keyof typeof BRAND;
