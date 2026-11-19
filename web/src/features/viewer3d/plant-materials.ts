/*
  Acabados PBR de las plantas de proceso, por nombre del IfcSurfaceStyle de cada geometría.

  El color sale siempre del IFC (IfcSurfaceStyleShading); el nombre del estilo decide cómo
  responde la superficie a la luz y al mapa de entorno: pintura con barniz, acero galvanizado,
  chapa de aluminio del aislamiento, hormigón, caucho… Un estilo desconocido se resuelve por su
  color: saturado → pintura; gris → acero.
*/

export type SurfaceKind = "painted" | "steel" | "galvanized" | "cladding" | "concrete" | "asphalt" | "rubber" | "stainless" | "grating";

export type SurfaceFinish = {
  kind: SurfaceKind;
  metalness: number;
  roughness: number;
  clearcoat: number;
  clearcoatRoughness: number;
  /** Peso de la textura de cepillado (0 = superficie lisa). */
  brushed: number;
  /** Ruido de árido o asfalto en la rugosidad (0 = sin ruido). */
  grain: number;
  envMapIntensity: number;
};

const finish = (kind: SurfaceKind, metalness: number, roughness: number, extra: Partial<SurfaceFinish> = {}): SurfaceFinish => ({
  kind, metalness, roughness, clearcoat: 0, clearcoatRoughness: 0.3, brushed: 0, grain: 0, envMapIntensity: 1, ...extra,
});

const FINISHES: Record<string, SurfaceFinish> = {
  // Envolventes de equipos y estructura: acero con pintura de poliuretano, algo de brillo.
  acero: finish("painted", 0.32, 0.4, { clearcoat: 0.35, clearcoatRoughness: 0.32, brushed: 0.35 }),
  refuerzo: finish("steel", 0.55, 0.48, { brushed: 0.5 }),
  // Motores y carcasas: esmalte de fábrica, más brillante.
  motor: finish("painted", 0.18, 0.3, { clearcoat: 0.65, clearcoatRoughness: 0.18 }),
  seguridad: finish("painted", 0.06, 0.46, { clearcoat: 0.2, clearcoatRoughness: 0.4 }),
  rojo: finish("painted", 0.08, 0.36, { clearcoat: 0.45, clearcoatRoughness: 0.25 }),
  // Chapa de aluminio sobre el aislamiento térmico.
  aislante: finish("cladding", 0.82, 0.3, { brushed: 1, envMapIntensity: 1.1 }),
  hormigon: finish("concrete", 0, 0.9, { grain: 1, envMapIntensity: 0.6 }),
  asfalto: finish("asphalt", 0, 0.95, { grain: 1, envMapIntensity: 0.5 }),
  junta: finish("rubber", 0, 0.78, { envMapIntensity: 0.6 }),
  caucho: finish("rubber", 0, 0.82, { envMapIntensity: 0.5 }),
  // Cubiertas y chapas de piso galvanizadas.
  cubierta: finish("galvanized", 0.62, 0.52, { brushed: 0.4 }),
  galvanizado: finish("galvanized", 0.72, 0.46, { brushed: 0.5 }),
  rejilla: finish("grating", 0.6, 0.55, { brushed: 0.3 }),
  inoxidable: finish("stainless", 0.92, 0.24, { brushed: 1, envMapIntensity: 1.15 }),
  // Tuberías pintadas con el color del fluido.
  mezcla: finish("painted", 0.22, 0.34, { clearcoat: 0.4, clearcoatRoughness: 0.25 }),
  gas: finish("painted", 0.22, 0.34, { clearcoat: 0.4, clearcoatRoughness: 0.25 }),
  crudo: finish("painted", 0.22, 0.36, { clearcoat: 0.4, clearcoatRoughness: 0.25 }),
  agua: finish("painted", 0.22, 0.34, { clearcoat: 0.4, clearcoatRoughness: 0.25 }),
  condensado: finish("painted", 0.22, 0.34, { clearcoat: 0.4, clearcoatRoughness: 0.25 }),
  gnl: finish("painted", 0.22, 0.32, { clearcoat: 0.45, clearcoatRoughness: 0.22 }),
};

/** "Hormigón" → "hormigon"; "Acero inoxidable" → "acero inoxidable". */
export const styleKey = (style: string) => style.normalize("NFD").replace(/[̀-ͯ]/g, "").trim().toLowerCase();

const ALIASES: [RegExp, string][] = [
  [/inox/, "inoxidable"],
  [/galvan/, "galvanizado"],
  [/rejill|tramex|grating/, "rejilla"],
  [/aisla|chapa de aluminio|cladding/, "aislante"],
  [/hormig|concret/, "hormigon"],
  [/asfalt|pavimento/, "asfalto"],
  [/junta|caucho|goma|neopren/, "junta"],
  [/seguridad|barandill|escalera/, "seguridad"],
  [/motor/, "motor"],
  [/cubierta|techo|chapa/, "cubierta"],
  [/refuerzo|perfil|viga/, "refuerzo"],
];

/** Acabado de una geometría a partir del nombre de su estilo y, si no se conoce, de su color. */
export function surfaceFinish(style: string | undefined, color: readonly number[] = [0.6, 0.6, 0.6]): SurfaceFinish {
  if (style) {
    const key = styleKey(style);
    if (FINISHES[key]) return FINISHES[key]!;
    for (const [pattern, alias] of ALIASES) if (pattern.test(key)) return FINISHES[alias]!;
  }
  const [r = 0.6, g = 0.6, b = 0.6] = color;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const saturation = max > 0 ? (max - min) / max : 0;
  return saturation > 0.28
    ? finish("painted", 0.15, 0.42, { clearcoat: 0.3, clearcoatRoughness: 0.3 })
    : finish("steel", 0.5, 0.44, { brushed: 0.4 });
}
