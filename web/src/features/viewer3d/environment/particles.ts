import {
  Color,
  InstancedBufferAttribute,
  InstancedBufferGeometry,
  Mesh,
  NormalBlending,
  PlaneGeometry,
  ShaderMaterial,
  Vector4,
} from "three";
import type { AtmosphereUniforms } from "./atmosphere";
import { ATMOSPHERE_GLSL, NOISE_GLSL } from "./glsl";
import { mulberry32 } from "./random";

/*
  Partículas en GPU: cada sistema es una sola malla instanciada (un draw call). La posición de
  cada partícula se calcula en el vértice a partir del tiempo común y de su semilla: no hay
  estado en CPU, no se actualiza nada por fotograma y con el movimiento parado la escena queda
  quieta y completa. Cada vez que una partícula renace, su variación sale de un hash de su
  semilla y del número de ciclo: siempre igual para el mismo instante.

  Iluminación de "volumen barato": cada sprite es una esfera aparente (normal del disco) con luz
  del sol envolvente, cielo y dispersión hacia delante cuando se mira hacia el sol.
*/

export type ParticleMode = "steam" | "dust" | "sand" | "devil";

const MODE_ID: Record<ParticleMode, number> = { steam: 0, dust: 1, sand: 2, devil: 3 };

export type ParticleOptions = {
  mode: ParticleMode;
  count: number;
  /** Emisor de cada partícula (x, y, z), repetido si hay menos que partículas. */
  origins: readonly (readonly [number, number, number])[];
  seed: number;
  /** Vida media en segundos. */
  life: number;
  /** Tamaño inicial y final (m). */
  size: [number, number];
  /** steam: velocidad de subida; sand: velocidad de arrastre; devil: altura de la columna. */
  rise: number;
  /** Radio del emisor o dispersión lateral (m). */
  spread: number;
  /** Cuánto arrastra el viento (0-1). */
  drift: number;
  opacity: number;
  color: string;
  /** Color de la cara en sombra (vapor gris azulado, polvo pardo). */
  shade: string;
  /** dust: (cx, cz, rx, rz) de la elipse y (ω, fase, cota, -); devil: (cx, cz, deriva, ω). */
  path?: [number, number, number, number];
  path2?: [number, number, number, number];
  /** Dirección de la cresta (sand) en (x, z). */
  axis?: [number, number];
};

const VERTEX = /* glsl */ `
${NOISE_GLSL}
${ATMOSPHERE_GLSL}
attribute vec3 aOrigin;
attribute vec4 aSeed;
uniform float uLife;
uniform vec2 uSize;
uniform float uRise;
uniform float uSpread;
uniform float uDrift;
uniform vec4 uPath;
uniform vec4 uPath2;
uniform vec2 uAxis;
varying vec2 vCorner;
varying vec2 vNoise;
varying float vAlpha;
varying vec3 vCenter;
varying float vSeed;

vec3 windVector() { return vec3(uEnvWind.x, 0.0, uEnvWind.y) * uEnvWind.z; }

void main() {
  float t = uEnvTime;
  float life = uLife * (0.75 + 0.5 * aSeed.y);
  float cycleF = t / life + aSeed.x;
  float age01 = fract(cycleF);
  float cycle = floor(cycleF);
  float age = age01 * life;
  float jitterA = envHash1(aSeed.z * 7919.0 + cycle * 13.0);
  float jitterB = envHash1(aSeed.w * 6151.0 + cycle * 29.0 + 3.0);
  vec3 wind = windVector();
  vec3 center = aOrigin;
  float size = mix(uSize.x, uSize.y, sqrt(age01));
  float alpha = 1.0;
#if PARTICLE_MODE == 0
  // Vapor o humo: sube con empuje que se agota y se tumba con el viento al ganar altura.
  vec2 offset = (vec2(jitterA, jitterB) - 0.5) * 2.0 * uSpread;
  float rise = uRise * life * (1.0 - exp(-2.6 * age01)) / 2.6;
  center += vec3(offset.x, rise, offset.y);
  center += wind * uDrift * age * smoothstep(0.0, 0.7, age01);
  center += vec3(sin(t * 0.37 + aSeed.z * 31.0), 0.25 * sin(t * 0.29 + aSeed.w * 17.0), cos(t * 0.31 + aSeed.w * 23.0)) * age01 * uSpread * 1.6;
  alpha = smoothstep(0.0, 0.07, age01) * (1.0 - smoothstep(0.35, 1.0, age01));
#elif PARTICLE_MODE == 1
  // Estela de polvo de un vehículo que recorre una elipse: nace donde estaba hace "age" s.
  float a = uPath2.y + uPath2.x * (t - age);
  vec2 onPath = uPath.xy + vec2(cos(a) * uPath.z, sin(a) * uPath.w);
  vec2 tangent = normalize(vec2(-sin(a) * uPath.z, cos(a) * uPath.w));
  vec2 side = vec2(-tangent.y, tangent.x);
  float lateral = (jitterA - 0.5) * 2.0 * (0.8 + uSpread * age01);
  center = vec3(onPath.x + side.x * lateral, uPath2.z, onPath.y + side.y * lateral);
  center.y += 0.25 + uRise * age * (1.0 - 0.4 * age01) + jitterB * 0.4;
  center += wind * uDrift * age;
  alpha = smoothstep(0.0, 0.06, age01) * (1.0 - smoothstep(0.25, 1.0, age01));
#elif PARTICLE_MODE == 2
  // Arena que vuela por las crestas: ráfagas que barren la cresta a favor del viento.
  vec2 along = vec2(uEnvWind.x, uEnvWind.y);
  center += vec3(uAxis.x, 0.0, uAxis.y) * (jitterA - 0.5) * uSpread;
  center += vec3(along.x, 0.0, along.y) * uRise * age;
  center.y += 0.15 + 1.6 * sin(3.14159 * age01) * (0.35 + 0.65 * jitterB) - 0.6 * age01 * age01;
  float gust = smoothstep(0.42, 0.72, envValueNoise(vec2(t * 0.11 + aOrigin.x * 0.013, aOrigin.z * 0.017 + aSeed.y * 3.0)));
  alpha = sin(3.14159 * age01) * gust;
#else
  // Remolino de polvo: columna que gira, se ensancha con la altura y deriva despacio.
  vec2 base = uPath.xy + vec2(cos(t * uPath.w + 1.3), sin(t * uPath.w * 0.73)) * uPath.z;
  float h = age01 * uRise;
  float spin = aSeed.z * 6.2832 + t * uDrift * (2.2 - 1.4 * age01) + age * 0.6;
  float radius = mix(0.9, 7.5, pow(age01, 1.35)) * (0.55 + 0.45 * jitterB);
  center = vec3(base.x + cos(spin) * radius, uPath2.z + h, base.y + sin(spin) * radius);
  center += wind * 0.06 * h;
  alpha = smoothstep(0.0, 0.08, age01) * (1.0 - smoothstep(0.5, 1.0, age01)) * mix(1.0, 0.55, age01);
#endif
  vCenter = center;
  vSeed = aSeed.w;
  vAlpha = alpha;
  vCorner = position.xy * 2.0;
  float spinUv = aSeed.w * 6.2832 + age * 0.25;
  mat2 r = mat2(cos(spinUv), sin(spinUv), -sin(spinUv), cos(spinUv));
  vNoise = r * position.xy * 2.0 + vec2(aSeed.z * 13.0, cycle * 3.7);
  vec4 mv = viewMatrix * vec4(center, 1.0);
  mv.xy += position.xy * size;
  gl_Position = projectionMatrix * mv;
}
`;

const FRAGMENT = /* glsl */ `
${NOISE_GLSL}
${ATMOSPHERE_GLSL}
uniform vec3 uColor;
uniform vec3 uShade;
uniform float uOpacity;
varying vec2 vCorner;
varying vec2 vNoise;
varying float vAlpha;
varying vec3 vCenter;
varying float vSeed;
void main() {
  float r = length(vCorner);
  if (r > 1.0 || vAlpha <= 0.002) discard;
  float n = envValueNoise(vNoise * 1.6) * 0.6 + envValueNoise(vNoise * 3.7 + 7.0) * 0.4;
  float shape = 1.0 - smoothstep(0.15, 1.0, r + (n - 0.5) * 0.75);
  vec3 nView = vec3(vCorner, sqrt(max(0.0, 1.0 - r * r)));
  vec3 nWorld = normalize((vec4(nView, 0.0) * viewMatrix).xyz);
  float wrap = max(dot(nWorld, uEnvSunDir) * 0.6 + 0.4, 0.0);
  vec3 viewDir = envViewRay(vCenter);
  float forward = pow(max(dot(viewDir, uEnvSunDir), 0.0), 8.0);
  vec3 albedo = mix(uShade, uColor, wrap);
  vec3 lit = albedo * (uEnvSunLight * (wrap * 0.3 + forward * 0.35) + envAmbient(nWorld) * 0.62);
  lit = envFog(lit, vCenter);
  float a = shape * vAlpha * uOpacity;
  gl_FragColor = vec4(lit * a, a);
}
`;

export function createParticles(atmosphere: AtmosphereUniforms, options: ParticleOptions): Mesh {
  const base = new PlaneGeometry(1, 1);
  const geometry = new InstancedBufferGeometry();
  geometry.index = base.index;
  geometry.setAttribute("position", base.getAttribute("position"));
  const random = mulberry32(options.seed);
  const origins = new Float32Array(options.count * 3);
  const seeds = new Float32Array(options.count * 4);
  for (let i = 0; i < options.count; i++) {
    const origin = options.origins[i % options.origins.length]!;
    origins.set(origin, i * 3);
    seeds.set([random(), random(), random(), random()], i * 4);
  }
  geometry.setAttribute("aOrigin", new InstancedBufferAttribute(origins, 3));
  geometry.setAttribute("aSeed", new InstancedBufferAttribute(seeds, 4));
  geometry.instanceCount = options.count;
  const material = new ShaderMaterial({
    name: `entorno-particulas-${options.mode}`,
    uniforms: {
      ...atmosphere,
      uLife: { value: options.life },
      uSize: { value: options.size },
      uRise: { value: options.rise },
      uSpread: { value: options.spread },
      uDrift: { value: options.drift },
      uPath: { value: new Vector4(...(options.path ?? [0, 0, 0, 0])) },
      uPath2: { value: new Vector4(...(options.path2 ?? [0, 0, 0, 0])) },
      uAxis: { value: options.axis ?? [1, 0] },
      uColor: { value: new Color(options.color) },
      uShade: { value: new Color(options.shade) },
      uOpacity: { value: options.opacity },
    },
    vertexShader: VERTEX,
    fragmentShader: FRAGMENT,
    defines: { PARTICLE_MODE: MODE_ID[options.mode] },
    transparent: true,
    depthWrite: false,
    blending: NormalBlending,
    premultipliedAlpha: true,
  });
  const mesh = new Mesh(geometry, material);
  mesh.name = `entorno-particulas-${options.mode}`;
  mesh.frustumCulled = false;
  mesh.renderOrder = 10;
  mesh.matrixAutoUpdate = false;
  base.dispose();
  return mesh;
}
