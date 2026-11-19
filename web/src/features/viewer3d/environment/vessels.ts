import { linear, MeshBuilder, type Vec3Like } from "./builder";
import { mulberry32, picker } from "./random";

/*
  Barcos y plataformas lejanas del atrezo, construidos con primitivas en una sola malla con color
  y acabado por vértice. Ejes locales: x hacia proa, y arriba (0 = flotación), z a estribor.

  El casco es una superficie de secciones transversales: manga que se afina en la proa con
  abanico y algo de abocinamiento, popa de espejo, quilla que sube en el pie de roda y franjas de
  color (obra muerta, flotación y obra viva) con vértices a ambos lados de cada cambio para que
  los bordes salgan nítidos.
*/

export type HullSpec = {
  length: number;
  beam: number;
  draft: number;
  /** Francobordo en el centro (m sobre la flotación). */
  freeboard: number;
  /** Arrufo: cuánto sube la cubierta en proa y en popa. */
  bowSheer: number;
  sternSheer: number;
  /** Fracción de eslora en que se afina la proa y la popa. */
  entrance: number;
  run: number;
  /** Ancho relativo del espejo de popa. */
  transom: number;
  hull: string;
  boot: string;
  bottom: string;
  deck: string;
  /** Franja clara bajo la regala (opcional). */
  stripe?: string;
};

const smooth = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/** Cota de cubierta (sobre flotación) en la fracción de eslora u (0 popa, 1 proa). */
export function deckHeight(spec: HullSpec, u: number) {
  return spec.freeboard + spec.bowSheer * smooth(0.55, 1, u) ** 1.6 + spec.sternSheer * smooth(0.25, 0, u);
}

/** Semimanga en cubierta en la fracción de eslora u. */
export function halfBreadth(spec: HullSpec, u: number) {
  const bow = Math.min(1, Math.max(0, (u - (1 - spec.entrance)) / spec.entrance));
  const stern = Math.min(1, Math.max(0, (spec.run - u) / spec.run));
  return (spec.beam / 2) * (1 - bow ** 2.1) * (1 - (1 - spec.transom) * stern ** 2);
}

export function buildHull(b: MeshBuilder, spec: HullSpec) {
  const { length, draft } = spec;
  const hull = linear(spec.hull), boot = linear(spec.boot), bottom = linear(spec.bottom);
  const stripe = spec.stripe ? linear(spec.stripe) : hull;
  const stations = 30;
  const rows: Vec3Like[][] = [];
  const decks: Vec3Like[][] = [];
  for (let i = 0; i <= stations; i++) {
    const s = i / stations;
    // Más secciones en la proa, donde cambia la forma.
    const u = 1 - (1 - s) ** 1.35;
    const x = (u - 0.5) * length;
    const top = deckHeight(spec, u);
    const half = halfBreadth(spec, u);
    const bowT = Math.min(1, Math.max(0, (u - (1 - spec.entrance)) / spec.entrance));
    const keel = -draft * (1 - 0.88 * smooth(0.86, 1, u)) * (1 - 0.45 * smooth(0.12, 0, u));
    const flare = 1 - 0.22 * bowT;
    const bilge = Math.min(half * 0.55, (top - keel) * 0.3, spec.beam * 0.09);
    const width = (y: number) => {
      // Abocinamiento: más estrecho abajo en la proa.
      const k = (y - keel) / Math.max(0.01, top - keel);
      return half * (flare + (1 - flare) * k);
    };
    const side: [number, number][] = [];
    const levels = [top, top - 0.32, top - 0.36, 1.05, 1.0, 0.25, -0.55, -0.6];
    // Mismo número de puntos en todas las secciones (la superficie las une fila a fila).
    for (const level of levels) {
      const y = Math.min(top, Math.max(keel + bilge + 0.02, level));
      side.push([width(y), y]);
    }
    for (let k = 0; k <= 3; k++) {
      const a = (k / 3) * Math.PI / 2;
      side.push([width(keel + bilge) - bilge + bilge * Math.cos(a), keel + bilge - bilge * Math.sin(a)]);
    }
    side.push([0, keel]);
    const row: Vec3Like[] = [];
    for (const [z, y] of side) row.push([x, y, -z]);
    for (let k = side.length - 2; k >= 0; k--) row.push([x, side[k]![1], side[k]![0]]);
    rows.push(row);
    decks.push([[x, top, -half], [x, top + 0.12, 0], [x, top, half]]);
  }
  const colorAt = (p: Vec3Like) => {
    const y = p[1];
    const top = deckHeight(spec, (p[0] / length) + 0.5);
    if (y > top - 0.34) return stripe;
    if (y > 1.02) return hull;
    if (y > -0.57) return boot;
    return bottom;
  };
  b.surface(0.55, 0.15);
  b.strip(rows, false, true, colorAt);
  b.color(spec.deck, 0.85, 0.05);
  b.strip(decks, false, false);
  // Espejo de popa.
  b.color(spec.hull, 0.55, 0.15);
  b.fan(rows[0]!, [-1, 0, 0]);
  // Regala: amurada baja en toda la eslora.
  const rail: Vec3Like[][] = [[], []];
  for (const d of decks) {
    rail[0]!.push(d[0]!);
    rail[1]!.push([d[0]![0], d[0]![1] + 1.0, d[0]![2]]);
  }
  b.color(spec.stripe ?? spec.hull, 0.6, 0.1);
  b.strip(rail, false, true);
  b.strip(rail.map(r => r.map(p => [p[0], p[1], -p[2]] as Vec3Like)), false, false);
}

/** Bloque de acomodación con una banda de ventanas oscuras por planta. */
function deckhouse(b: MeshBuilder, x0: number, x1: number, y0: number, levels: number, height: number, width: number, color: string, glass = "#1e2a33") {
  const cx = (x0 + x1) / 2, lx = x1 - x0;
  for (let k = 0; k < levels; k++) {
    const y = y0 + k * height;
    const inset = k * 0.35;
    b.color(color, 0.6, 0.05).box(cx - inset * 0.5, y + height / 2, 0, lx - inset, height, width - inset);
    b.color(glass, 0.15, 0.6).box(cx - inset * 0.5, y + height * 0.62, 0, lx - inset + 0.1, height * 0.3, width - inset + 0.1);
  }
  return y0 + levels * height;
}

function mast(b: MeshBuilder, x: number, y0: number, height: number, color = "#e6e8ea") {
  b.color(color, 0.5, 0.4).cylinder([x, y0, 0], [x, y0 + height, 0], 0.22, 0.12, 8, false);
  b.box(x, y0 + height * 0.72, 0, 0.18, 0.18, 3.2);
  b.color("#2b2f33", 0.5, 0.5).box(x + 0.4, y0 + height * 0.86, 0, 1.6, 0.12, 0.3);
}

/** Buque de apoyo a plataformas (PSV): puente a proa y cubierta de carga corrida a popa. */
export function buildSupplyVessel(): { builder: MeshBuilder; length: number; beam: number } {
  const b = new MeshBuilder();
  const spec: HullSpec = {
    length: 84, beam: 18.5, draft: 6.2, freeboard: 1.9, bowSheer: 5.2, sternSheer: 0.1,
    entrance: 0.3, run: 0.12, transom: 0.92, hull: "#b5262c", boot: "#2c2f33", bottom: "#5c1d1d",
    deck: "#6a6f69", stripe: "#d9dcdc",
  };
  buildHull(b, spec);
  // Castillo y acomodación a proa (3 plantas) con el puente encima.
  const fx = 12, deckY = deckHeight(spec, 0.72);
  b.color("#e9ebec", 0.6, 0.05).box(24, deckY + 1.4, 0, 22, 2.8, 16.5);
  const top = deckhouse(b, 14, 30, deckY + 2.8, 2, 2.9, 15.5, "#eef0f1");
  // Puente con ventanas corridas y alerones.
  b.color("#eef0f1", 0.55, 0.05).box(24.5, top + 1.5, 0, 11, 3.0, 17.8);
  b.color("#18232b", 0.1, 0.7).box(24.6, top + 1.75, 0, 11.15, 1.25, 17.95);
  b.color("#c7cbce", 0.5, 0.2).box(24.5, top + 3.1, 0, 11.6, 0.2, 18.4);
  mast(b, 26, top + 3.2, 8.5);
  b.color("#d8dbdd", 0.55, 0.1).box(fx - 1.5, deckY + 3.5, 6.5, 2.4, 4.5, 2.4);
  b.color("#d8dbdd", 0.55, 0.1).box(fx - 1.5, deckY + 3.5, -6.5, 2.4, 4.5, 2.4);
  // Chimeneas tras el puente.
  b.color("#e9ebec", 0.5, 0.1).box(fx - 1.5, deckY + 6.5, 6.5, 2.0, 1.6, 2.0);
  b.color("#e9ebec", 0.5, 0.1).box(fx - 1.5, deckY + 6.5, -6.5, 2.0, 1.6, 2.0);
  b.color("#202326", 0.6, 0.2).box(fx - 1.5, deckY + 7.5, 6.5, 1.6, 0.6, 1.6);
  b.color("#202326", 0.6, 0.2).box(fx - 1.5, deckY + 7.5, -6.5, 1.6, 0.6, 1.6);
  // Cubierta de carga: contenedores, tubos y barandilla de protección.
  const cargoY = spec.freeboard + 0.15;
  const colors = ["#2f6e9b", "#d7a12a", "#3e7a4b", "#c2462f", "#e3e5e6", "#2f6e9b"];
  const random = mulberry32(77);
  const pick = picker(random);
  for (let i = 0; i < 6; i++) {
    const x = -30 + i * 6.8;
    const z = pick.pick([-4.5, 4.5, 0]);
    b.color(colors[i]!, 0.7, 0.3).box(x, cargoY + 1.3, z, 6.06, 2.6, 2.44);
    if (i % 2 === 0) b.color(colors[(i + 2) % colors.length]!, 0.7, 0.3).box(x, cargoY + 3.9, z, 6.06, 2.6, 2.44);
  }
  b.color("#7d8389", 0.45, 0.7);
  for (let k = 0; k < 9; k++) b.cylinder([-36, cargoY + 0.35 + (k % 3) * 0.55, -1.5 + Math.floor(k / 3) * 0.55], [-8, cargoY + 0.35 + (k % 3) * 0.55, -1.5 + Math.floor(k / 3) * 0.55], 0.26, 0.26, 6, false);
  b.color("#d9a521", 0.5, 0.3);
  for (let x = -40; x <= 8; x += 4) {
    b.cylinder([x, cargoY, 8.6], [x, cargoY + 2.6, 8.6], 0.12, 0.12, 5, false);
    b.cylinder([x, cargoY, -8.6], [x, cargoY + 2.6, -8.6], 0.12, 0.12, 5, false);
  }
  b.box(-16, cargoY + 2.6, 8.6, 48, 0.25, 0.25).box(-16, cargoY + 2.6, -8.6, 48, 0.25, 0.25);
  // Rodillo de popa y grúa de cubierta.
  b.color("#2b2f33", 0.5, 0.6).cylinder([-41.6, cargoY - 0.2, -5], [-41.6, cargoY - 0.2, 5], 0.7, 0.7, 10);
  b.color("#e2a31b", 0.5, 0.4).cylinder([-6, cargoY, -7.2], [-6, cargoY + 5, -7.2], 0.55, 0.45, 10);
  b.cylinder([-6, cargoY + 5, -7.2], [-20, cargoY + 9, -6.4], 0.32, 0.22, 8);
  return { builder: b, length: spec.length, beam: spec.beam };
}

/** Metanero pequeño con tres tanques cilíndricos tipo C sobre cubierta y acomodación a popa. */
export function buildLngCarrier(): { builder: MeshBuilder; length: number; beam: number } {
  const b = new MeshBuilder();
  const spec: HullSpec = {
    length: 152, beam: 25.6, draft: 7.4, freeboard: 7.4, bowSheer: 3.6, sternSheer: 1.0,
    entrance: 0.24, run: 0.16, transom: 0.86, hull: "#22385a", boot: "#8d2424", bottom: "#5a1e1e",
    deck: "#55625a", stripe: "#22385a",
  };
  buildHull(b, spec);
  const deckY = spec.freeboard + 0.1;
  // Tanques tipo C: cilindros horizontales a lo largo, medio enterrados, con su domo.
  const tanks = [[-28, 31], [8, 31], [44, 28]] as const;
  for (const [x, length] of tanks) {
    const radius = 9.4;
    const y = deckY + 2.2;
    b.color("#e7ebee", 0.42, 0.25);
    b.cylinder([x - length / 2, y, 0], [x + length / 2, y, 0], radius, radius, 28, false);
    b.sphere([x - length / 2, y, 0], radius, 20, 10, 0, Math.PI, false, 1).sphere([x + length / 2, y, 0], radius, 20, 10, 0, Math.PI, false, 1);
    b.color("#c9ced2", 0.45, 0.3).cylinder([x + 4, y + radius - 0.6, 0], [x + 4, y + radius + 1.8, 0], 1.5, 1.5, 12);
    // Pasarela sobre los tanques.
    b.color("#c7a12f", 0.55, 0.3).box(x, y + radius + 0.2, 0, length, 0.25, 1.6);
  }
  // Tubería de cubierta (trunk) a estribor y babor, y colector central con su grúa.
  b.color("#9aa2a8", 0.4, 0.75);
  for (const z of [-11, -10.2, 11, 10.2]) b.cylinder([-50, deckY + 1.1, z], [62, deckY + 1.1, z], 0.38, 0.38, 8, false);
  b.color("#d1d5d8", 0.55, 0.2).box(-10, deckY + 2.2, 0, 6, 4.4, 24);
  b.color("#7f8a92", 0.4, 0.7);
  for (let k = -3; k <= 3; k++) b.cylinder([-10 + k * 0.9, deckY + 1.0, -12.4], [-10 + k * 0.9, deckY + 3.2, -12.8], 0.32, 0.32, 8);
  b.color("#d7a12a", 0.5, 0.4).cylinder([-14, deckY, -9], [-14, deckY + 9, -9], 0.6, 0.5, 10).cylinder([-14, deckY + 9, -9], [-2, deckY + 14, -11], 0.35, 0.25, 8);
  // Acomodación a popa: cinco plantas, puente con alerones y chimenea.
  const top = deckhouse(b, -72, -56, deckY, 5, 3.0, 21, "#eef0f1");
  b.color("#eef0f1", 0.55, 0.05).box(-62, top + 1.6, 0, 9, 3.2, 26.2);
  b.color("#17222a", 0.1, 0.7).box(-61.9, top + 1.9, 0, 9.15, 1.3, 26.35);
  b.color("#c9cdd0", 0.5, 0.2).box(-62, top + 3.3, 0, 9.6, 0.22, 26.6);
  mast(b, -63, top + 3.4, 9);
  b.color("#e9ebec", 0.5, 0.1).box(-70.5, top + 3.4, 0, 6, 8.5, 6.5);
  b.color("#2f5d8c", 0.5, 0.1).box(-70.5, top + 5.6, 0, 6.08, 1.6, 6.58);
  b.color("#1d2023", 0.6, 0.3).box(-70.5, top + 7.9, 0, 5.2, 0.6, 5.6);
  // Botes salvavidas.
  b.color("#e2621b", 0.55, 0.05).sphere([-60, deckY + 7.2, 11.6], 1.6, 12, 6, 0, Math.PI, false, 0.85).sphere([-60, deckY + 7.2, -11.6], 1.6, 12, 6, 0, Math.PI, false, 0.85);
  // Castillo de proa con molinetes y palo de proa.
  const bowDeck = deckHeight(spec, 0.93);
  b.color("#55625a", 0.8, 0.1).box(63, bowDeck - 0.1, 0, 14, 0.4, 13);
  b.color("#4c5257", 0.5, 0.5).cylinder([62, bowDeck, -3], [62, bowDeck + 1.4, -3], 1.0, 1.0, 10).cylinder([62, bowDeck, 3], [62, bowDeck + 1.4, 3], 1.0, 1.0, 10);
  mast(b, 66, bowDeck, 10, "#e3a51d");
  return { builder: b, length: spec.length, beam: spec.beam };
}

/** Remolcador de puerto: casco oscuro, defensa de proa, puente alto y chigre de popa. */
export function buildTug(): { builder: MeshBuilder; length: number; beam: number } {
  const b = new MeshBuilder();
  const spec: HullSpec = {
    length: 32, beam: 12, draft: 4.2, freeboard: 1.7, bowSheer: 1.8, sternSheer: 0,
    entrance: 0.36, run: 0.18, transom: 0.85, hull: "#1d1f22", boot: "#a3221f", bottom: "#561b1b",
    deck: "#5d6260", stripe: "#c02b25",
  };
  buildHull(b, spec);
  const deckY = deckHeight(spec, 0.6);
  b.color("#141516", 0.9, 0).torus([6, deckY - 0.1, 0], 4.6, 0.55, 6, 20);
  b.color("#f0f1f2", 0.55, 0.05).box(4, deckY + 1.4, 0, 9, 2.8, 8);
  b.color("#f0f1f2", 0.55, 0.05).box(5, deckY + 3.9, 0, 5.4, 2.2, 6.4);
  b.color("#18232b", 0.1, 0.7).box(5.05, deckY + 4.1, 0, 5.5, 1.0, 6.5);
  mast(b, 4.5, deckY + 5.0, 4.5);
  b.color("#c02b25", 0.5, 0.1).box(-1.2, deckY + 3.2, 2.2, 1.4, 3.4, 1.4).box(-1.2, deckY + 3.2, -2.2, 1.4, 3.4, 1.4);
  b.color("#1b1d1f", 0.5, 0.2).box(-1.2, deckY + 5.0, 2.2, 1.2, 0.3, 1.2).box(-1.2, deckY + 5.0, -2.2, 1.2, 0.3, 1.2);
  b.color("#3b4044", 0.5, 0.6).cylinder([-8, deckY + 0.9, -2.2], [-8, deckY + 0.9, 2.2], 1.0, 1.0, 12);
  return { builder: b, length: spec.length, beam: spec.beam };
}

/** Plataforma lejana (silueta en la bruma): jacket, cubierta, torre de perforación y antorcha. */
export function buildDistantPlatform(b: MeshBuilder, x: number, z: number, heading: number, seed: number): [number, number, number] {
  const random = mulberry32(seed);
  const pick = picker(random);
  const width = pick.range(30, 48), depth = pick.range(24, 34), deck = pick.range(18, 24);
  b.at(x, 0, z, heading);
  b.color("#8b949a", 0.6, 0.5);
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    b.cylinder([sx * width * 0.42, -2, sz * depth * 0.42], [sx * width * 0.36, deck, sz * depth * 0.36], 0.9, 0.8, 6, false);
  }
  for (let k = 0; k < 3; k++) {
    const y0 = k * deck / 3, y1 = (k + 1) * deck / 3;
    b.cylinder([-width * 0.41, y0, -depth * 0.41], [width * 0.4, y1, -depth * 0.4], 0.35, 0.35, 4, false);
    b.cylinder([-width * 0.41, y0, depth * 0.41], [width * 0.4, y1, depth * 0.4], 0.35, 0.35, 4, false);
  }
  b.color("#9ea6ab", 0.7, 0.3).box(0, deck + 1.5, 0, width, 3, depth);
  b.color(pick.pick(["#c9c3b5", "#b9c0c5", "#d0c7a8"]), 0.75, 0.1).box(-width * 0.18, deck + 6.5, depth * 0.1, width * 0.45, 7, depth * 0.6);
  b.color("#e6e8e9", 0.7, 0.05).box(width * 0.25, deck + 9, -depth * 0.15, width * 0.3, 12, depth * 0.45);
  b.color("#c64a2a", 0.6, 0.3).lattice([width * 0.05, deck + 3, -depth * 0.2], [width * 0.05, deck + 3 + pick.range(26, 34), -depth * 0.2], 3.2, 0.9, 5, 0.25);
  // Brazo de antorcha que sale de la plataforma.
  const boomEnd: [number, number, number] = [-width * 0.5 - 26, deck + 22, 0];
  b.color("#a0a7ac", 0.6, 0.4).lattice([-width * 0.5, deck + 2, 0], boomEnd, 1.4, 0.7, 4, 0.18);
  b.pop();
  const cos = Math.cos(heading), sin = Math.sin(heading);
  // Punta de la antorcha en coordenadas del mundo (giro en Y como `at`).
  return [x + boomEnd[0] * cos + boomEnd[2] * sin, boomEnd[1], z - boomEnd[0] * sin + boomEnd[2] * cos];
}
