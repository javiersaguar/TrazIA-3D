import {
  Color,
  Mesh,
  ShaderMaterial,
  UniformsLib,
  UniformsUtils,
  Vector2,
  Vector3,
  Vector4,
} from "three";
import { CONTACT_LIMIT, type Contact } from "./contacts";
import { radialGrid } from "./builder";
import { ATMOSPHERE_GLSL, NOISE_GLSL } from "./glsl";
import type { AtmosphereUniforms } from "./atmosphere";
import type { Quality } from "./palettes";
import type { SiteFrame } from "./site";
import { maxAmplitude, waveUniforms, WAVES_GLSL, type Wave } from "./waves";

/*
  Lámina de agua: malla radial centrada en la planta (densa cerca, hasta el horizonte) con olas
  de Gerstner en el vértice, normales por píxel con detalle procedural, reflejo del cielo con
  Fresnel, destello del sol, dispersión en las crestas, espuma (crestas, contactos con el IFC,
  estelas de barcos y, en la costa, rompiente) y la niebla radial común. Recibe la sombra del sol.
*/

export const VESSEL_SLOTS = 2;

export type WaterOptions = {
  waves: Wave[];
  level: number;
  site: SiteFrame;
  quality: Quality;
  deep: string;
  scatter: string;
  shallow?: string;
  /** Dirección (x, z) de la corriente: la estela de las patas va hacia allí. */
  current: [number, number];
  /** Código GLSL con `float seabed(vec2 p)` (cota del fondo) y `float shelter(vec2 p)`: activa la costa. */
  shore?: string;
};

export type VesselWake = {
  /** Centro (x, z), radio y velocidad angular (rad/s, con signo) de la trayectoria circular. */
  cx: number;
  cz: number;
  radius: number;
  speed: number;
  /** Ángulo inicial, manga, duración de la estela (s) e intensidad. */
  angle: number;
  beam: number;
  duration: number;
  strength: number;
};

const VERTEX = /* glsl */ `
#include <common>
#include <shadowmap_pars_vertex>
uniform float uEnvTime;
uniform vec3 uGridCenter;
uniform float uLevel;
uniform float uSegments;
${WAVES_GLSL}
#ifdef WATER_SHORE
uniform float uShoreUnused;
WATER_SHORE_CODE
#endif
varying vec3 vWorld;
varying vec2 vBase;
void main() {
  vec2 base = position.xz + uGridCenter.xz;
  float spacing = max(length(position.xz) * 6.2832 / uSegments, 0.25);
  vec3 d = waveDisplace(base, uEnvTime, spacing * 3.2);
  #ifdef WATER_SHORE
    d *= shelter(base);
  #endif
  vec4 worldPosition = vec4(base.x + d.x, uLevel + d.y, base.y + d.z, 1.0);
  vWorld = worldPosition.xyz;
  vBase = base;
  vec4 mvPosition = viewMatrix * worldPosition;
  gl_Position = projectionMatrix * mvPosition;
  vec3 transformedNormal = (viewMatrix * vec4(0.0, 1.0, 0.0, 0.0)).xyz;
  #include <shadowmap_vertex>
}
`;

const FRAGMENT = /* glsl */ `
#include <common>
#include <packing>
#include <bsdfs>
#include <lights_pars_begin>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
${NOISE_GLSL}
${ATMOSPHERE_GLSL}
${WAVES_GLSL}
uniform vec3 uDeep;
uniform vec3 uScatter;
uniform vec3 uShallow;
uniform vec3 uFoam;
uniform float uLevel;
uniform float uAmplitude;
uniform vec4 uContacts[${CONTACT_LIMIT}];
uniform int uContactCount;
uniform vec2 uCurrent;
uniform vec4 uVesselPath[${VESSEL_SLOTS}];
uniform vec4 uVesselState[${VESSEL_SLOTS}];
#ifdef WATER_SHORE
WATER_SHORE_CODE
#endif
varying vec3 vWorld;
varying vec2 vBase;

/* Encaje de espuma: manchas con hilos, que se deshacen con el tiempo. */
float foamLace(vec2 p, float t) {
  float a = envValueNoise(p * 1.7 + vec2(t * 0.11, -t * 0.07));
  float b = envValueNoise(p * 4.3 - vec2(t * 0.19, t * 0.13));
  float c = envValueNoise(p * 0.55 + vec2(-t * 0.03, t * 0.05));
  return clamp(a * 0.55 + b * 0.3 + c * 0.35 - 0.12, 0.0, 1.0);
}

float contactFoam(vec2 p, float t, out float churn) {
  float foam = 0.0;
  churn = 0.0;
  vec2 across = vec2(-uCurrent.y, uCurrent.x);
  for (int i = 0; i < ${CONTACT_LIMIT}; i++) {
    if (i >= uContactCount) break;
    vec4 c = uContacts[i];
    vec2 rel = p - c.xy;
    float dist = length(rel) - c.z;
    float pulse = 0.75 + 0.25 * sin(t * 1.3 + c.x * 0.7 + c.y * 0.3);
    float ring = exp(-max(dist, 0.0) / (0.16 + 0.28 * c.z)) * pulse;
    float along = dot(rel, uCurrent);
    float side = abs(dot(rel, across));
    float width = c.z * (1.05 + max(along, 0.0) * 0.045);
    float wake = smoothstep(-c.z, c.z * 0.5, along) * exp(-max(along, 0.0) / (c.z * 6.0 + 3.0))
      * (1.0 - smoothstep(width * 0.45, width, side));
    foam = max(foam, c.w * 0.8 * max(ring, wake * 0.55));
    churn = max(churn, c.w * exp(-max(dist, 0.0) / (0.8 + c.z * 1.1)));
  }
  return foam;
}

float vesselFoam(vec2 p, float t) {
  float foam = 0.0;
  for (int i = 0; i < ${VESSEL_SLOTS}; i++) {
    vec4 P = uVesselPath[i];
    vec4 S = uVesselState[i];
    if (S.w <= 0.0) continue;
    vec2 rel = p - P.xy;
    float r = length(rel);
    float lag = mod((S.x + P.w * t - atan(rel.y, rel.x)) * sign(P.w), 6.2831853);
    float behind = lag * P.z;
    float age = lag / max(abs(P.w), 1e-4);
    if (age > S.z) continue;
    float across = abs(r - P.z);
    float halfWidth = S.y * 0.55 + behind * 0.045;
    float turbulent = (1.0 - smoothstep(halfWidth * 0.25, halfWidth, across)) * exp(-age / (S.z * 0.3));
    float arm = exp(-pow((across - behind * 0.33 - S.y * 0.5) / (0.8 + behind * 0.02), 2.0)) * exp(-age / (S.z * 0.45));
    float fadeIn = smoothstep(0.0, S.y * 0.6, behind);
    foam = max(foam, (turbulent + arm * 0.55) * S.w * fadeIn);
  }
  return foam;
}

void main() {
  float t = uEnvTime;
  vec2 p = vBase;
  float footprint = max(length(fwidth(vWorld.xz)), 1e-3);
  vec4 wn = waveNormal(p, t, max(footprint * 3.0, 0.15));
  vec3 n = wn.xyz;
  float fold = wn.w;
  float detail = 1.0 - smoothstep(0.06, 0.55, footprint);
  vec3 r1 = envNoised(p * 0.85 + uEnvWind.xy * t * 0.55);
  vec3 r2 = envNoised(p * 2.4 - uEnvWind.xy * t * 0.8 + 3.7);
  vec3 r3 = envNoised(p * 0.21 + vec2(t * 0.05, -t * 0.03));
  n.xz -= (r1.yz * 0.05 + r2.yz * 0.024) * detail + r3.yz * 0.045 * (1.0 - smoothstep(0.5, 6.0, footprint));
  #ifdef WATER_SHORE
    float depth = uLevel - seabed(p);
    // Tierra firme por encima del agua: no se dibuja (evita que la lámina asome bajo el terreno).
    if (depth < -0.35) discard;
    float calm = shelter(p);
    n.xz *= mix(0.35, 1.0, calm);
  #endif
  n = normalize(n);
  vec3 view = -envViewRay(vWorld);
  float ndv = max(dot(n, view), 1e-3);
  float fresnel = 0.02 + 0.98 * pow(1.0 - ndv, 5.0);
  vec3 reflected = reflect(-view, n);
  reflected.y = abs(reflected.y) + 0.02;
  vec3 sky = envSky(normalize(reflected), 0.0);
  float shadow = getShadowMask();
  vec3 l = uEnvSunDir;
  vec3 h = normalize(l + view);
  float ndl = max(dot(n, l), 0.0);
  float ndh = max(dot(n, h), 0.0);
  float rough = mix(0.045, 0.2, smoothstep(0.03, 2.0, footprint));
  float a2 = rough * rough * rough * rough;
  float denom = ndh * ndh * (a2 - 1.0) + 1.0;
  float ggx = a2 / (3.14159 * denom * denom);
  float fsun = 0.02 + 0.98 * pow(1.0 - max(dot(view, h), 0.0), 5.0);
  vec3 glitter = uEnvSunLight * ggx * fsun * ndl / (4.0 * ndv + 0.2) * shadow;
  float crest = clamp((vWorld.y - uLevel) / max(uAmplitude, 0.01) * 0.5 + 0.5, 0.0, 1.0);
  vec3 ambient = uEnvSkyLight;
  vec3 deep = uDeep;
  #ifdef WATER_SHORE
    float shallow = 1.0 - smoothstep(0.4, 9.0, depth);
    deep = mix(deep, uShallow, shallow);
  #endif
  vec3 body = deep * (ambient * 0.85 + uEnvSunLight * 0.12 * ndl * mix(0.4, 1.0, shadow));
  float through = pow(clamp(dot(view, -l) * 0.5 + 0.5, 0.0, 1.0), 3.0);
  body += uScatter * uEnvSunLight * 0.035 * (crest * crest * 0.9 + through * crest * 2.2) * mix(0.35, 1.0, shadow);
  vec3 color = mix(body, sky, fresnel) + glitter;

  // Espuma: borreguillos en crestas plegadas, contactos con el IFC, estelas y rompiente.
  float lace = foamLace(p, t);
  float patches = smoothstep(0.42, 0.78, envValueNoise(p * 0.035 + vec2(t * 0.012, t * 0.006)));
  float whitecap = smoothstep(0.34, 0.7, fold + 0.22 * (lace - 0.5)) * mix(0.35, 1.0, patches);
  float churn;
  float contact = contactFoam(p, t, churn);
  float wake = vesselFoam(p, t);
  float foam = whitecap * smoothstep(0.25, 0.75, lace) * 0.85;
  foam = max(foam, contact * smoothstep(0.12, 0.62, lace + contact * 0.35));
  foam = max(foam, wake * smoothstep(0.1, 0.6, lace + wake * 0.3));
  #ifdef WATER_SHORE
    float surfBand = 1.0 - smoothstep(0.0, 2.6, depth);
    float surfLines = smoothstep(0.55, 0.95, sin(depth * 3.1 + t * 1.35 + lace * 2.2) * 0.5 + 0.5);
    float wash = surfBand * max(surfLines, 1.0 - smoothstep(0.0, 0.5, depth));
    foam = max(foam * calm, wash * smoothstep(0.15, 0.6, lace + wash * 0.35));
  #endif
  color = mix(color, color * 0.86 + uScatter * uEnvSunLight * 0.02, churn * 0.5);
  vec3 foamLit = uFoam * (uEnvSunLight * (0.2 + 0.25 * ndl) * mix(0.45, 1.0, shadow) + ambient * 0.75);
  color = mix(color, foamLit, clamp(foam, 0.0, 1.0) * (1.0 - smoothstep(30.0, 400.0, footprint * 600.0)));
  color = envFog(color, vWorld);
  gl_FragColor = vec4(color, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

export type Water = {
  mesh: Mesh;
  setContacts(contacts: readonly Contact[]): void;
  setVessels(wakes: readonly (VesselWake | null)[]): void;
};

export function createWater(atmosphere: AtmosphereUniforms, options: WaterOptions): Water {
  const high = options.quality === "high";
  const segments = high ? 320 : 176;
  const geometry = radialGrid(high ? 0.6 : 1.2, 9000, segments, 1.08);
  const { a, b } = waveUniforms(options.waves);
  const contacts = Array.from({ length: CONTACT_LIMIT }, () => new Vector4());
  const paths = Array.from({ length: VESSEL_SLOTS }, () => new Vector4());
  const states = Array.from({ length: VESSEL_SLOTS }, () => new Vector4());
  const current = new Vector2(...options.current).normalize();
  const shoreCode = options.shore ?? "";
  const replaceShore = (code: string) => code.replace(/WATER_SHORE_CODE/g, shoreCode);
  const material = new ShaderMaterial({
    name: "entorno-agua",
    lights: true,
    uniforms: {
      ...UniformsUtils.clone(UniformsLib.lights),
      ...atmosphere,
      uWaveA: { value: a },
      uWaveB: { value: b },
      uGridCenter: { value: new Vector3(options.site.x, 0, options.site.z) },
      uLevel: { value: options.level },
      uSegments: { value: segments },
      uAmplitude: { value: maxAmplitude(options.waves) * 0.55 },
      uDeep: { value: new Color(options.deep) },
      uScatter: { value: new Color(options.scatter) },
      uShallow: { value: new Color(options.shallow ?? options.deep) },
      uFoam: { value: new Color("#f2f5f6") },
      uContacts: { value: contacts },
      uContactCount: { value: 0 },
      uCurrent: { value: current },
      uVesselPath: { value: paths },
      uVesselState: { value: states },
    },
    vertexShader: replaceShore(VERTEX),
    fragmentShader: replaceShore(FRAGMENT),
    defines: options.shore ? { WATER_SHORE: 1 } : {},
  });
  const mesh = new Mesh(geometry, material);
  mesh.name = "entorno-agua";
  mesh.frustumCulled = false;
  mesh.receiveShadow = true;
  mesh.renderOrder = -10;
  return {
    mesh,
    setContacts(list) {
      material.uniforms.uContactCount!.value = Math.min(list.length, CONTACT_LIMIT);
      list.slice(0, CONTACT_LIMIT).forEach((c, i) => contacts[i]!.set(c.x, c.z, c.radius, c.weight));
    },
    setVessels(wakes) {
      for (let i = 0; i < VESSEL_SLOTS; i++) {
        const wake = wakes[i];
        if (!wake) { states[i]!.set(0, 0, 0, 0); continue; }
        paths[i]!.set(wake.cx, wake.cz, wake.radius, wake.speed);
        states[i]!.set(wake.angle, wake.beam, wake.duration, wake.strength);
      }
    },
  };
}
