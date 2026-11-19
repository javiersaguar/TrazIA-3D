import {
  BufferAttribute,
  Mesh,
  MeshStandardMaterial,
  type IUniform,
} from "three";
import { withRadialFog, type AtmosphereUniforms } from "./atmosphere";
import { radialGrid } from "./builder";
import { NOISE_GLSL } from "./glsl";
import type { Quality } from "./palettes";
import type { SiteFrame } from "./site";

/*
  Terreno: malla radial centrada en la planta (densa cerca, hasta el horizonte) con la cota de
  una función de altura en CPU. Así proyecta y recibe sombras como cualquier malla.

  El sombreado es PBR estándar de three (sol, sombras, cielo y mapa de entorno), con el albedo,
  la rugosidad y la normal calculados por píxel en GLSL: la normal sale de la misma función de
  altura evaluada en el píxel, así las crestas quedan nítidas aunque la malla lejana sea gruesa.

  Cada entorno aporta:
    float terrainHeight(vec2 p)                     — misma fórmula que `height` en TS
    void terrainSurface(vec3 world, inout vec3 n, inout vec3 albedo, inout float rough)
*/

export type TerrainOptions = {
  site: SiteFrame;
  quality: Quality;
  atmosphere: AtmosphereUniforms;
  /** Cota del terreno en (x, z) del mundo. */
  height: (x: number, z: number) => number;
  /** GLSL con terrainHeight y terrainSurface. */
  glsl: string;
  uniforms?: Record<string, IUniform>;
  outer?: number;
  /** Paso de la malla en el centro. */
  inner?: number;
  name: string;
  /** Paso (m) para la normal por píxel; 0 = usar la normal de la malla. */
  normalStep?: number;
  defines?: Record<string, string | number>;
};

export function createTerrain(options: TerrainOptions): Mesh {
  const high = options.quality === "high";
  const segments = high ? 288 : 168;
  const geometry = radialGrid(options.inner ?? (high ? 0.8 : 1.5), options.outer ?? 7000, segments, 1.1);
  const position = geometry.getAttribute("position") as BufferAttribute;
  const normal = geometry.getAttribute("normal") as BufferAttribute;
  const { site, height } = options;
  for (let i = 0; i < position.count; i++) {
    const x = position.getX(i) + site.x;
    const z = position.getZ(i) + site.z;
    const r = Math.hypot(position.getX(i), position.getZ(i));
    const e = Math.max(0.25, r * 0.01);
    const h = height(x, z);
    const dx = (height(x + e, z) - height(x - e, z)) / (2 * e);
    const dz = (height(x, z + e) - height(x, z - e)) / (2 * e);
    const len = Math.hypot(dx, 1, dz);
    position.setXYZ(i, x, h, z);
    normal.setXYZ(i, -dx / len, 1 / len, -dz / len);
  }
  geometry.computeBoundingSphere();
  const material = new MeshStandardMaterial({ color: 0xffffff, roughness: 0.9, metalness: 0 });
  material.name = `entorno-${options.name}`;
  const extra = options.uniforms ?? {};
  const step = options.normalStep ?? 0;
  material.onBeforeCompile = shader => {
    Object.assign(shader.uniforms, extra);
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>\n${NOISE_GLSL}\n__TERRAIN__`)
      .replace("#include <normal_fragment_maps>", /* glsl */ `#include <normal_fragment_maps>
      {
        vec3 tN = vec3(0.0, 1.0, 0.0);
        ${step > 0 ? `
        float tStep = max(${step.toFixed(3)}, length(fwidth(vEnvWorld.xz)) * 0.75);
        vec2 tp = vEnvWorld.xz;
        float hx = terrainHeight(tp + vec2(tStep, 0.0)) - terrainHeight(tp - vec2(tStep, 0.0));
        float hz = terrainHeight(tp + vec2(0.0, tStep)) - terrainHeight(tp - vec2(0.0, tStep));
        tN = normalize(vec3(-hx, 2.0 * tStep, -hz));` : `
        tN = normalize((vec4(normal, 0.0) * viewMatrix).xyz);`}
        vec3 tAlbedo = diffuseColor.rgb;
        float tRough = roughnessFactor;
        terrainSurface(vEnvWorld, tN, tAlbedo, tRough);
        diffuseColor.rgb = tAlbedo;
        roughnessFactor = tRough;
        normal = normalize((viewMatrix * vec4(tN, 0.0)).xyz);
      }`);
  };
  material.customProgramCacheKey = () => `terreno-${options.name}`;
  withRadialFog(material, options.atmosphere, `terreno-${options.name}`);
  // La niebla declara los uniformes uEnv* y vEnvWorld delante del ruido: el código del entorno
  // va en la marca, detrás de los dos.
  const previous = material.onBeforeCompile;
  material.onBeforeCompile = (shader, renderer) => {
    previous.call(material, shader, renderer);
    shader.fragmentShader = shader.fragmentShader.replace("__TERRAIN__", options.glsl);
    if (options.defines) for (const [key, value] of Object.entries(options.defines)) {
      shader.fragmentShader = `#define ${key} ${value}\n${shader.fragmentShader}`;
    }
  };
  const mesh = new Mesh(geometry, material);
  mesh.name = `entorno-${options.name}`;
  mesh.receiveShadow = true;
  mesh.frustumCulled = false;
  mesh.matrixAutoUpdate = false;
  mesh.renderOrder = -5;
  return mesh;
}
