import {
  Group,
  InstancedMesh,
  Matrix4,
  Quaternion,
  Vector2,
  Vector3,
  Vector4,
} from "three";
import { MeshBuilder, type Vec3Like } from "./builder";
import { propMesh } from "./materials";
import { createParticles } from "./particles";
import { mulberry32, picker, valueNoise } from "./random";
import { sceneGroup, standardScene, type EnvironmentScene, type SceneContext } from "./scene";
import { siteDistance, type SiteFrame } from "./site";
import { createTerrain } from "./terrain";

/*
  Desierto: campo de dunas transversales al viento (barlovento suave, cara de avalancha
  empinada), explanada nivelada bajo la planta con una transición natural (y la arena que el
  viento acumula contra su borde), pista de servicio con una camioneta que levanta polvo,
  oleoducto sobre durmientes hasta el horizonte, mesetas rocosas en la calima y espejismo del
  cielo en el suelo lejano. Animado: arena que vuela por las crestas en ráfagas, un remolino de
  polvo lejano y matorrales rodantes que ruedan sin deslizar.

  La cota de las dunas se calcula igual en TS (malla, sombras, vehículos) y en GLSL (normal por
  píxel): mismo ruido con hash entero (random.ts ↔ glsl.ts).
*/

export const PAD_LEVEL = -0.12;
export const DUNE_WAVELENGTH = 125;
export const DUNE_HEIGHT = 11;
const CREST = 0.84;

export type DesertLayout = {
  site: SiteFrame;
  /** Dirección hacia la que sopla el viento (unitaria). */
  wind: [number, number];
  /** Pista: centro y semiejes de la elipse. */
  track: [number, number, number, number];
  /** Oleoducto: origen y dirección (unitaria). */
  pipeline: [number, number, number, number];
};

export function desertLayout(site: SiteFrame, wind: [number, number]): DesertLayout {
  const length = Math.hypot(wind[0], wind[1]) || 1;
  const w: [number, number] = [wind[0] / length, wind[1] / length];
  const pipeDir = new Vector2(-0.96, -0.28).normalize();
  return {
    site,
    wind: w,
    track: [site.x, site.z, site.halfX + 92, site.halfZ + 84],
    pipeline: [site.x - site.halfX - 4, site.z - site.halfZ * 0.35, pipeDir.x, pipeDir.y],
  };
}

/** Perfil de una duna transversal en su fase f ∈ [0, 1): barlovento convexo y cara de avalancha. */
export function duneProfile(f: number): number {
  if (f < CREST) return Math.sin((Math.PI / 2) * (f / CREST)) ** 1.5;
  const q = (f - CREST) / (1 - CREST);
  return 1 - q ** 1.25;
}

/** Fase, amplitud y máscara (explanada, pista, oleoducto) de las dunas en (x, z). */
export function duneField(layout: DesertLayout, x: number, z: number) {
  const { site, wind, track, pipeline } = layout;
  const px = x - site.x, pz = z - site.z;
  const along = px * wind[0] + pz * wind[1];
  const across = -px * wind[1] + pz * wind[0];
  const warp = 38 * (valueNoise(px / 260, pz / 260) - 0.5) + 14 * (valueNoise(px / 97 + 31, pz / 97) - 0.5);
  const phase = (along + warp) / DUNE_WAVELENGTH;
  const f = phase - Math.floor(phase);
  const amp = 0.4 + 0.6 * valueNoise(across / 210 + 3.1, along / 420 + 7.7);
  const d = siteDistance(site, x, z);
  const pad = smoothstep(16, 120, d);
  const ex = (x - track[0]) / track[2], ez = (z - track[1]) / track[3];
  const trackDist = Math.abs(Math.hypot(ex, ez) - 1) * Math.min(track[2], track[3]);
  const road = smoothstep(5, 24, trackDist);
  const rx = x - pipeline[0], rz = z - pipeline[1];
  const t = rx * pipeline[2] + rz * pipeline[3];
  const pipeDist = t > 0 ? Math.abs(rx * pipeline[3] - rz * pipeline[2]) : Math.hypot(rx, rz);
  const corridor = smoothstep(7, 30, pipeDist);
  return { f, amp, mask: pad * road * corridor, pad, d };
}

export function smoothstep(a: number, b: number, x: number) {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
}

/** Cota del terreno del desierto en (x, z). */
export function desertHeight(layout: DesertLayout, x: number, z: number): number {
  const { f, amp, mask, d } = duneField(layout, x, z);
  const px = x - layout.site.x, pz = z - layout.site.z;
  const broad = 7 * (valueNoise(px / 900 + 11, pz / 900) - 0.5) + 2.5 * (valueNoise(px / 330, pz / 330 + 5) - 0.5);
  const berm = 0.75 * Math.exp(-(((d - 21) / 7) ** 2));
  return PAD_LEVEL + (DUNE_HEIGHT * amp * duneProfile(f) + broad) * mask + berm;
}

/** El mismo campo en GLSL (para la normal por píxel y el color). */
export const DESERT_GLSL = /* glsl */ `
uniform vec4 uSiteRect;
uniform vec4 uTrack;
uniform vec4 uPipe;
uniform vec2 uWindDir;
float dSmooth(float a, float b, float x) { float t = clamp((x - a) / (b - a), 0.0, 1.0); return t * t * (3.0 - 2.0 * t); }
float siteDist(vec2 p) {
  vec2 d = abs(p - uSiteRect.xy) - uSiteRect.zw;
  return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
}
float trackDist(vec2 p) {
  vec2 e = (p - uTrack.xy) / uTrack.zw;
  return abs(length(e) - 1.0) * min(uTrack.z, uTrack.w);
}
float pipeDist(vec2 p) {
  vec2 r = p - uPipe.xy;
  float t = dot(r, uPipe.zw);
  return t > 0.0 ? abs(r.x * uPipe.w - r.y * uPipe.z) : length(r);
}
float duneProfile(float f) {
  if (f < ${CREST.toFixed(2)}) return pow(sin(1.5707963 * f / ${CREST.toFixed(2)}), 1.5);
  float q = (f - ${CREST.toFixed(2)}) / ${(1 - CREST).toFixed(2)};
  return 1.0 - pow(q, 1.25);
}
/* (fase, amplitud, máscara, máscara de explanada) */
vec4 duneField(vec2 p, out float d) {
  vec2 q = p - uSiteRect.xy;
  float along = dot(q, uWindDir);
  float across = -q.x * uWindDir.y + q.y * uWindDir.x;
  float warp = 38.0 * (envValueNoise(q / 260.0) - 0.5) + 14.0 * (envValueNoise(q / 97.0 + vec2(31.0, 0.0)) - 0.5);
  float phase = (along + warp) / ${DUNE_WAVELENGTH.toFixed(1)};
  float f = fract(phase);
  float amp = 0.4 + 0.6 * envValueNoise(vec2(across / 210.0 + 3.1, along / 420.0 + 7.7));
  d = siteDist(p);
  float pad = dSmooth(16.0, 120.0, d);
  float mask = pad * dSmooth(5.0, 24.0, trackDist(p)) * dSmooth(7.0, 30.0, pipeDist(p));
  return vec4(f, amp, mask, pad);
}
float terrainHeight(vec2 p) {
  float d;
  vec4 field = duneField(p, d);
  vec2 q = p - uSiteRect.xy;
  float broad = 7.0 * (envValueNoise(q / 900.0 + vec2(11.0, 0.0)) - 0.5) + 2.5 * (envValueNoise(q / 330.0 + vec2(0.0, 5.0)) - 0.5);
  float berm = 0.75 * exp(-pow((d - 21.0) / 7.0, 2.0));
  return ${PAD_LEVEL.toFixed(2)} + (${DUNE_HEIGHT.toFixed(1)} * field.y * duneProfile(field.x) + broad) * field.z + berm;
}
void terrainSurface(vec3 world, inout vec3 n, inout vec3 albedo, inout float rough) {
  vec2 p = world.xz;
  float d;
  vec4 field = duneField(p, d);
  float slip = step(${CREST.toFixed(2)}, field.x) * field.z;
  float crestLight = smoothstep(0.6, 0.84, field.x) * (1.0 - slip) * field.z;
  float broad = envValueNoise(p / 140.0) * 0.6 + envValueNoise(p / 37.0) * 0.4;
  vec3 sandDark = vec3(0.50, 0.275, 0.115);
  vec3 sandLight = vec3(0.68, 0.425, 0.20);
  vec3 sand = mix(sandDark, sandLight, broad);
  sand = mix(sand, sand * vec3(1.08, 1.05, 1.0), crestLight);
  sand = mix(sand, sand * vec3(0.93, 0.9, 0.88), slip * 0.6);
  // Explanada: suelo compactado con grava clara y manchas.
  float speck = envValueNoise(p * 2.7) * 0.5 + envValueNoise(p * 0.41) * 0.5;
  vec3 caliche = mix(vec3(0.42, 0.33, 0.22), vec3(0.55, 0.45, 0.32), speck);
  float padArea = 1.0 - dSmooth(4.0, 46.0, d + (envValueNoise(p / 23.0) - 0.5) * 22.0);
  // Pista: firme compactado con dos rodadas.
  float td = trackDist(p);
  float road = 1.0 - dSmooth(2.4, 7.0, td + (envValueNoise(p / 9.0) - 0.5) * 2.0);
  vec2 e = (p - uTrack.xy) / uTrack.zw;
  float signedTrack = (length(e) - 1.0) * min(uTrack.z, uTrack.w);
  float ruts = (1.0 - dSmooth(0.15, 0.5, abs(abs(signedTrack) - 0.85))) * road;
  vec3 roadColor = mix(vec3(0.37, 0.26, 0.15), vec3(0.30, 0.21, 0.12), ruts);
  float corridor = 1.0 - dSmooth(3.0, 9.0, pipeDist(p));
  albedo = mix(sand, caliche, padArea);
  albedo = mix(albedo, mix(caliche, roadColor, 0.55), corridor * 0.7);
  albedo = mix(albedo, roadColor, road);
  rough = mix(0.92, 0.97, padArea);
  // Ondulaciones de viento (no en la cara de avalancha ni en la explanada).
  float rp = dot(p, uWindDir) / 0.9 + envValueNoise(p / 6.0) * 3.5;
  float fade = 1.0 - smoothstep(0.25, 0.6, fwidth(rp));
  float rippleW = fade * (1.0 - slip) * (1.0 - padArea) * (1.0 - road) * 0.16;
  float s = fract(rp);
  float slope = s < 0.7 ? 1.0 : -2.33;
  vec3 rippleN = vec3(-uWindDir.x * slope, 0.0, -uWindDir.y * slope) * rippleW;
  n = normalize(n + rippleN);
  albedo *= 1.0 - 0.05 * rippleW * slope;
  // Espejismo: lejos y a ras, el suelo refleja el cielo y riela con el calor.
  vec3 toWorld = world - cameraPosition;
  float grazing = 1.0 - smoothstep(0.015, 0.08, -normalize(toWorld).y);
  float far = smoothstep(650.0, 2100.0, length(p - uSiteRect.xy));
  float mirage = far * grazing * (isOrthographic ? 0.0 : 1.0);
  float shimmer = envValueNoise(vec2(p.x * 0.02 + uEnvTime * 0.9, p.y * 0.06 - uEnvTime * 0.4)) - 0.5;
  n = normalize(mix(n, vec3(shimmer * 0.06, 1.0, shimmer * 0.03), mirage));
  rough = mix(rough, 0.07, mirage);
  albedo *= 1.0 - 0.55 * mirage;
}
`;

/** Matorral rodante: bola de ramas finas y curvas (unas 60), de 1 m de diámetro. */
export function tumbleweedBuilder(seed: number): MeshBuilder {
  const b = new MeshBuilder();
  const random = mulberry32(seed);
  const pick = picker(random);
  b.color("#8a6a45", 0.95, 0);
  for (let i = 0; i < 46; i++) {
    // Rama: arco desde cerca del centro hacia la superficie, con una bifurcación.
    const theta = pick.range(0, Math.PI * 2), y = pick.range(-0.95, 0.95);
    const r = Math.sqrt(1 - y * y);
    const dir = new Vector3(r * Math.cos(theta), y, r * Math.sin(theta));
    const bend = new Vector3(pick.range(-1, 1), pick.range(-1, 1), pick.range(-1, 1)).multiplyScalar(0.35);
    let prev: Vec3Like = [dir.x * 0.08, dir.y * 0.08, dir.z * 0.08];
    const steps = 4;
    for (let k = 1; k <= steps; k++) {
      const s = k / steps;
      const reach = 0.08 + s * pick.range(0.38, 0.5);
      const curve = Math.sin(s * Math.PI) * 1.0;
      const p: Vec3Like = [dir.x * reach + bend.x * curve * 0.3, dir.y * reach + bend.y * curve * 0.3, dir.z * reach + bend.z * curve * 0.3];
      b.color(k > 2 ? "#a88859" : "#7a5a38", 0.95, 0);
      b.cylinder(prev, p, 0.014 * (1.15 - s * 0.6), 0.012 * (1.15 - s * 0.6), 3, false);
      if (k === 2) {
        const fork: Vec3Like = [p[0] + pick.range(-0.18, 0.18), p[1] + pick.range(-0.18, 0.18), p[2] + pick.range(-0.18, 0.18)];
        b.cylinder(p, fork, 0.009, 0.006, 3, false);
      }
      prev = p;
    }
  }
  return b;
}

/** Camioneta de servicio (pick-up blanca con rotativo). x hacia delante. */
export function pickupBuilder(): MeshBuilder {
  const b = new MeshBuilder();
  b.color("#e9ebec", 0.45, 0.35).box(0.2, 0.85, 0, 5.2, 0.7, 1.9);
  b.box(0.75, 1.55, 0, 2.3, 0.8, 1.84);
  b.color("#1b252c", 0.1, 0.6).box(0.8, 1.6, 0, 2.34, 0.5, 1.86).box(1.92, 1.58, 0, 0.06, 0.5, 1.7);
  b.color("#d9dbdc", 0.5, 0.3).box(-1.4, 1.35, 0, 2.2, 0.32, 1.9);
  b.color("#e5891f", 0.4, 0.1).box(0.75, 2.02, 0, 0.3, 0.14, 1.1);
  b.color("#202224", 0.85, 0);
  for (const [x, z] of [[1.75, 0.82], [1.75, -0.82], [-1.35, 0.82], [-1.35, -0.82]] as const) {
    b.cylinder([x, 0.42, z - 0.13], [x, 0.42, z + 0.13], 0.42, 0.42, 12);
  }
  return b;
}

/** Meseta rocosa con escalones, cornisa y talud (sombreado facetado). */
function mesa(b: MeshBuilder, cx: number, cz: number, radius: number, height: number, seed: number) {
  const random = mulberry32(seed);
  const pick = picker(random);
  const sides = 11;
  const outline = Array.from({ length: sides }, (_, i) => {
    // Ángulo decreciente: contorno antihorario visto desde arriba (caras hacia fuera).
    const a = -(i / sides) * Math.PI * 2 + pick.range(-0.15, 0.15);
    const r = radius * pick.range(0.72, 1.08) * (1 + 0.35 * Math.cos(a * 2 + seed));
    return [Math.cos(a) * r, Math.sin(a) * r] as const;
  });
  const ring = (scale: number, y: number): Vec3Like[] => outline.map(([x, z]) => [cx + x * scale, y, cz + z * scale]);
  // Talud de derrubios.
  b.color("#9b7454", 0.95, 0).strip([ring(1.45, -6), ring(1.0, height * 0.32)], true, false);
  const tiers = [[1.0, 0.32, 0.62, "#a8704d"], [0.86, 0.62, 0.9, "#b98258"], [0.8, 0.9, 1.0, "#8e5f42"]] as const;
  for (const [scale, y0, y1, color] of tiers) {
    b.color(color, 0.95, 0).prism(outline.map(([x, z]) => [cx + x * scale, cz + z * scale] as const), height * y0, height * y1);
  }
}

export function buildDesert(ctx: SceneContext): EnvironmentScene {
  const { site, palette, quality, atmosphere } = ctx;
  const high = quality === "high";
  const layout = desertLayout(site, [palette.wind[0], palette.wind[1]]);
  const height = (x: number, z: number) => desertHeight(layout, x, z);
  const terrain = createTerrain({
    site, quality, atmosphere, height, glsl: DESERT_GLSL, name: "dunas", normalStep: 0.6,
    uniforms: {
      uSiteRect: { value: new Vector4(site.x, site.z, site.halfX, site.halfZ) },
      uTrack: { value: new Vector4(...layout.track) },
      uPipe: { value: new Vector4(...layout.pipeline) },
      uWindDir: { value: new Vector2(...layout.wind) },
    },
  });

  // Mesetas y cerros lejanos en la calima.
  const rocks = new MeshBuilder();
  const random = mulberry32(2207);
  const pick = picker(random);
  const mesas = high ? 9 : 6;
  for (let i = 0; i < mesas; i++) {
    const angle = -2.4 + (i / mesas) * Math.PI * 1.55 + pick.range(-0.2, 0.2);
    const distance = pick.range(1300, 2700);
    mesa(rocks, site.x + Math.cos(angle) * distance, site.z + Math.sin(angle) * distance, pick.range(140, 340), pick.range(55, 120), 900 + i);
  }
  for (let i = 0; i < (high ? 10 : 5); i++) {
    const angle = pick.range(0, Math.PI * 2);
    const distance = pick.range(520, 1100);
    const x = site.x + Math.cos(angle) * distance, z = site.z + Math.sin(angle) * distance;
    mesa(rocks, x, z, pick.range(14, 34), pick.range(8, 22), 1300 + i);
  }
  const rockMesh = propMesh(rocks, ctx.facets, "entorno-mesetas");

  // Oleoducto sobre durmientes hasta el horizonte, con postes de señalización.
  const pipe = new MeshBuilder();
  const [px, pz, dx, dz] = layout.pipeline;
  const side: [number, number] = [-dz, dx];
  let previous: [Vec3Like, Vec3Like] | null = null;
  for (let s = 0; s <= 3200; s += s < 400 ? 12 : 24) {
    const x = px + dx * s, z = pz + dz * s;
    const y = height(x, z);
    pipe.color("#9e9a90", 0.9, 0).at(x, y + 0.2, z, -Math.atan2(dz, dx)).box(0, 0, 0, 0.6, 0.45, 3.4).pop();
    const a: Vec3Like = [x + side[0] * 0.7, y + 0.95, z + side[1] * 0.7];
    const c: Vec3Like = [x - side[0] * 0.75, y + 0.85, z - side[1] * 0.75];
    if (previous) {
      pipe.color("#c9c3b4", 0.55, 0.35).cylinder(previous[0], a, 0.46, 0.46, 12, false);
      pipe.color("#3f4a52", 0.5, 0.45).cylinder(previous[1], c, 0.33, 0.33, 10, false);
    }
    previous = [a, c];
    if (s % 96 === 0 && s > 0) pipe.color("#e1b324", 0.6, 0.1).cylinder([x + side[0] * 2.6, y, z + side[1] * 2.6], [x + side[0] * 2.6, y + 1.5, z + side[1] * 2.6], 0.06, 0.06, 5);
  }
  const pipeMesh = propMesh(pipe, ctx.props, "entorno-oleoducto", true);

  // Camioneta de servicio por la pista y su estela de polvo.
  const [cx, cz, rx, rz] = layout.track;
  const omega = -11 / Math.hypot(rx, rz);
  const theta0 = 0.9 - omega * palette.start;
  const truck = new Group();
  truck.name = "entorno-camioneta";
  truck.matrixAutoUpdate = false;
  truck.add(propMesh(pickupBuilder(), ctx.props, "entorno-camioneta-cuerpo", true));
  const dust = createParticles(atmosphere, {
    mode: "dust", count: high ? 180 : 90, origins: [[0, 0, 0]], seed: 51, life: 7, size: [1.6, 9], rise: 0.55,
    spread: 4.5, drift: 0.22, opacity: 0.32, color: "#d8b88f", shade: "#8f7258",
    path: [cx, cz, rx, rz], path2: [omega, theta0, PAD_LEVEL + 0.1, 0],
  });

  // Arena que vuela por las crestas: emisores en crestas altas, a sotavento de la planta.
  const crests: [number, number, number][] = [];
  for (let ring = 0; ring < 30 && crests.length < (high ? 40 : 22); ring++) {
    const r = 110 + ring * 14;
    for (let k = 0; k < 40 && crests.length < (high ? 40 : 22); k++) {
      const a = (k / 40) * Math.PI * 2 + ring * 0.37;
      const x = site.x + Math.cos(a) * r, z = site.z + Math.sin(a) * r;
      const field = duneField(layout, x, z);
      if (field.f > 0.8 && field.f < 0.845 && field.amp * field.mask > 0.6) crests.push([x, height(x, z), z]);
    }
  }
  const sand = crests.length ? createParticles(atmosphere, {
    mode: "sand", count: high ? 560 : 260, origins: crests, seed: 77, life: 3.2, size: [0.7, 3.4], rise: 6.5,
    spread: 26, drift: 1, opacity: 0.22, color: "#e2c194", shade: "#9a7856",
    axis: [-layout.wind[1], layout.wind[0]],
  }) : null;

  // Remolino de polvo al fondo.
  const devil = createParticles(atmosphere, {
    mode: "devil", count: high ? 260 : 130, origins: [[0, 0, 0]], seed: 91, life: 9, size: [1.8, 7.5], rise: 58,
    spread: 0, drift: 1.6, opacity: 0.2, color: "#dcc19c", shade: "#8b6e55",
    path: [site.x - 260, site.z - 300, 45, 0.021], path2: [0, 0, height(site.x - 260, site.z - 300) - 0.5, 0],
  });

  // Matorrales rodantes: carriles a favor del viento, fuera de la planta.
  const weedGeometry = tumbleweedBuilder(4242).toGeometry();
  const weeds = new InstancedMesh(weedGeometry, ctx.props, 4);
  weeds.name = "entorno-matorrales";
  weeds.castShadow = true;
  weeds.frustumCulled = false;
  const [wx, wz] = layout.wind;
  const across: [number, number] = [-wz, wx];
  const lanes = [
    { offset: site.halfZ + 14, speed: 3.1, radius: 0.62, phase: 0.1 },
    { offset: site.halfZ + 27, speed: 2.6, radius: 0.48, phase: 0.55 },
    { offset: -(site.halfZ + 16), speed: 2.9, radius: 0.55, phase: 0.3 },
    { offset: site.halfZ + 40, speed: 3.4, radius: 0.7, phase: 0.8 },
  ];
  const span = 300;
  const matrix = new Matrix4(), rotation = new Quaternion(), spin = new Quaternion(), wobble = new Quaternion();
  const axis = new Vector3(), position = new Vector3(), scale = new Vector3();
  const up = new Vector3(0, 1, 0);
  axis.crossVectors(up, new Vector3(wx, 0, wz)).normalize();
  const updateWeeds = (t: number) => {
    lanes.forEach((lane, i) => {
      // Recorrido con ráfagas: la distancia avanzada integra la velocidad (sin deslizar).
      const travel = lane.speed * (t + 0.45 * Math.sin(t * 0.37 + i * 2) / 0.37) + lane.phase * span;
      const s = ((travel % span) + span) % span;
      const along = s - span / 2;
      const lateral = lane.offset + 3 * Math.sin(t * 0.11 + i);
      const x = site.x + wx * along + across[0] * lateral;
      const z = site.z + wz * along + across[1] * lateral;
      const hop = 0.28 * Math.max(0, Math.sin(travel * 0.55 + i)) ** 6;
      position.set(x, height(x, z) + lane.radius * (1 + hop), z);
      spin.setFromAxisAngle(axis, travel / lane.radius);
      wobble.setFromAxisAngle(up, 0.3 * Math.sin(t * 0.5 + i));
      rotation.multiplyQuaternions(wobble, spin);
      const fade = Math.min(1, s / 8, (span - s) / 8);
      scale.setScalar(lane.radius * 2 * Math.max(0.001, fade));
      weeds.setMatrixAt(i, matrix.compose(position, rotation, scale));
    });
    weeds.instanceMatrix.needsUpdate = true;
  };

  const updateTruck = (t: number) => {
    const theta = theta0 + omega * t;
    const x = cx + Math.cos(theta) * rx, z = cz + Math.sin(theta) * rz;
    const sign = Math.sign(omega);
    const heading = Math.atan2(Math.cos(theta) * rz * sign, -Math.sin(theta) * rx * sign);
    const fx = Math.cos(heading), fz = Math.sin(heading);
    const front = height(x + fx * 1.8, z + fz * 1.8), back = height(x - fx * 1.6, z - fz * 1.6);
    truck.position.set(x, height(x, z), z);
    truck.rotation.set(0, -heading, Math.atan2(front - back, 3.4), "YZX");
    truck.updateMatrix();
  };

  const group = sceneGroup("entorno-desierto", [terrain, rockMesh, pipeMesh, truck, dust, devil, weeds, ...(sand ? [sand] : [])]);
  const update = (t: number) => {
    updateWeeds(t);
    updateTruck(t);
  };
  update(palette.start);
  return standardScene(group, update);
}
