import {
  AdditiveBlending,
  Color,
  InstancedBufferAttribute,
  InstancedBufferGeometry,
  Mesh,
  PlaneGeometry,
  ShaderMaterial,
} from "three";
import type { AtmosphereUniforms } from "./atmosphere";
import { ATMOSPHERE_GLSL, NOISE_GLSL } from "./glsl";

/*
  Luces de efecto: balizas que destellan (obstáculos, bocana del puerto) y llamas de antorcha.
  Son sprites aditivos con color por encima de 1: el bloom del posprocesado los hace brillar sin
  luces reales ni sombras. Todo depende del tiempo común: con el movimiento parado quedan fijos
  (una baliza parada se ve encendida para que la escena quede completa: `uEnvMotion`).
*/

export type Beacon = {
  position: readonly [number, number, number];
  color: string;
  /** Intensidad (HDR) del núcleo. */
  intensity: number;
  /** Periodo (s), fase (0-1) y fracción encendida; duty 1 = fija. */
  period: number;
  phase: number;
  duty: number;
  /** Tamaño mínimo del halo en metros. */
  size: number;
};

const BEACON_VERTEX = /* glsl */ `
${ATMOSPHERE_GLSL}
attribute vec3 aPosition;
attribute vec3 aColor;
attribute vec4 aBlink;
varying vec2 vCorner;
varying vec3 vColor;
void main() {
  float cycle = fract(uEnvTime / aBlink.x + aBlink.y);
  float on = aBlink.z >= 1.0 ? 1.0 : smoothstep(0.0, 0.04, cycle) * (1.0 - smoothstep(aBlink.z, aBlink.z + 0.05, cycle));
  on = mix(1.0, on, uEnvMotion);
  vec4 mv = viewMatrix * vec4(aPosition, 1.0);
  float dist = isOrthographic ? 120.0 : -mv.z;
  float size = max(aBlink.w, dist * 0.0075) * mix(0.55, 1.0, on);
  vColor = aColor * on * (1.0 - envFogAmount(aPosition) * 0.85);
  vCorner = position.xy * 2.0;
  mv.xy += position.xy * size;
  gl_Position = projectionMatrix * mv;
}
`;

const BEACON_FRAGMENT = /* glsl */ `
varying vec2 vCorner;
varying vec3 vColor;
void main() {
  float r2 = dot(vCorner, vCorner);
  if (r2 > 1.0) discard;
  float core = exp(-r2 * 38.0);
  float halo = exp(-r2 * 5.0) * 0.16;
  gl_FragColor = vec4(vColor * (core + halo), 1.0);
}
`;

/** Todas las balizas de un entorno en un draw call. */
export function createBeacons(atmosphere: AtmosphereUniforms, beacons: readonly Beacon[]): Mesh {
  const base = new PlaneGeometry(1, 1);
  const geometry = new InstancedBufferGeometry();
  geometry.index = base.index;
  geometry.setAttribute("position", base.getAttribute("position"));
  const positions = new Float32Array(beacons.length * 3);
  const colors = new Float32Array(beacons.length * 3);
  const blink = new Float32Array(beacons.length * 4);
  beacons.forEach((beacon, i) => {
    positions.set(beacon.position, i * 3);
    const color = new Color(beacon.color).multiplyScalar(beacon.intensity);
    colors.set([color.r, color.g, color.b], i * 3);
    blink.set([beacon.period, beacon.phase, beacon.duty, beacon.size], i * 4);
  });
  geometry.setAttribute("aPosition", new InstancedBufferAttribute(positions, 3));
  geometry.setAttribute("aColor", new InstancedBufferAttribute(colors, 3));
  geometry.setAttribute("aBlink", new InstancedBufferAttribute(blink, 4));
  geometry.instanceCount = beacons.length;
  const material = new ShaderMaterial({
    name: "entorno-balizas",
    uniforms: { ...atmosphere },
    vertexShader: BEACON_VERTEX,
    fragmentShader: BEACON_FRAGMENT,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
  });
  const mesh = new Mesh(geometry, material);
  mesh.name = "entorno-balizas";
  mesh.frustumCulled = false;
  mesh.renderOrder = 20;
  mesh.matrixAutoUpdate = false;
  base.dispose();
  return mesh;
}

export type Flame = {
  /** Punta de la antorcha (donde nace la llama). */
  base: readonly [number, number, number];
  /** Altura y anchura de la llama (m). */
  height: number;
  width: number;
  /** Intensidad HDR. */
  intensity: number;
  seed: number;
};

const FLAME_VERTEX = /* glsl */ `
${ATMOSPHERE_GLSL}
attribute vec3 aBase;
attribute vec4 aShape;
varying vec2 vUv;
varying float vSeed;
varying float vFog;
void main() {
  // Billboard cilíndrico: el eje de la llama se tumba con el viento y el ancho mira a cámara.
  float t = uEnvTime;
  vec3 wind = vec3(uEnvWind.x, 0.0, uEnvWind.y);
  float lean = 0.32 + 0.06 * sin(t * 1.7 + aShape.w * 9.0);
  vec3 axis = normalize(vec3(0.0, 1.0, 0.0) + wind * lean * uEnvWind.z * 0.12);
  vec3 toCamera = isOrthographic ? -envForward() : normalize(cameraPosition - aBase);
  vec3 side = normalize(cross(axis, toCamera));
  vec2 uv = position.xy + vec2(0.0, 0.5);
  vUv = uv;
  vSeed = aShape.w;
  float height = aShape.x * (1.0 + 0.08 * sin(t * 2.3 + aShape.w * 5.0));
  vec3 world = aBase + axis * (uv.y * height - height * 0.06) + side * (position.x * aShape.y);
  vFog = envFogAmount(aBase);
  gl_Position = projectionMatrix * viewMatrix * vec4(world, 1.0);
}
`;

const FLAME_FRAGMENT = /* glsl */ `
${NOISE_GLSL}
uniform float uEnvTime;
uniform vec3 uFlameCore;
uniform vec3 uFlameOuter;
uniform float uFlameIntensity;
varying vec2 vUv;
varying float vSeed;
varying float vFog;
void main() {
  float y = vUv.y;
  float x = vUv.x * 2.0;
  float t = uEnvTime;
  vec2 q = vec2(x * 1.6, y * 2.6 - t * 2.4 + vSeed * 7.0);
  float n = envValueNoise(q) * 0.55 + envValueNoise(q * 2.3 + vec2(0.0, -t * 1.3)) * 0.3 + envValueNoise(q * 5.1) * 0.15;
  // Perfil de la llama: ancha abajo, lengua que se deshace arriba.
  float width = (1.0 - smoothstep(0.08, 1.0, y)) * 0.85 + 0.12;
  float body = 1.0 - smoothstep(width * 0.55, width, abs(x + (n - 0.5) * 0.55 * y));
  float lick = smoothstep(0.25, 0.75, n + (1.0 - y) * 0.55 - y * 0.25);
  float flame = body * lick * smoothstep(0.0, 0.06, y);
  float core = smoothstep(0.55, 0.95, flame) * (1.0 - smoothstep(0.1, 0.55, y));
  vec3 color = mix(uFlameOuter, uFlameCore, core) * (0.55 + 0.75 * flame);
  float alpha = flame * (1.0 - vFog * 0.85);
  gl_FragColor = vec4(color * alpha * uFlameIntensity, 1.0);
}
`;

/** Llamas de antorcha (todas las de un entorno en un draw call). */
export function createFlames(atmosphere: AtmosphereUniforms, flames: readonly Flame[]): Mesh {
  const base = new PlaneGeometry(1, 1, 1, 6);
  const geometry = new InstancedBufferGeometry();
  geometry.index = base.index;
  geometry.setAttribute("position", base.getAttribute("position"));
  const bases = new Float32Array(flames.length * 3);
  const shapes = new Float32Array(flames.length * 4);
  flames.forEach((flame, i) => {
    bases.set(flame.base, i * 3);
    shapes.set([flame.height, flame.width, flame.intensity, flame.seed], i * 4);
  });
  geometry.setAttribute("aBase", new InstancedBufferAttribute(bases, 3));
  geometry.setAttribute("aShape", new InstancedBufferAttribute(shapes, 4));
  geometry.instanceCount = flames.length;
  const material = new ShaderMaterial({
    name: "entorno-llamas",
    uniforms: {
      ...atmosphere,
      uFlameCore: { value: new Color("#fff1c4") },
      uFlameOuter: { value: new Color("#ff6a1a") },
      uFlameIntensity: { value: flames[0]?.intensity ?? 4 },
    },
    vertexShader: FLAME_VERTEX,
    fragmentShader: FLAME_FRAGMENT,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
  });
  const mesh = new Mesh(geometry, material);
  mesh.name = "entorno-llamas";
  mesh.frustumCulled = false;
  mesh.renderOrder = 21;
  mesh.matrixAutoUpdate = false;
  base.dispose();
  return mesh;
}
