import {
  BufferAttribute,
  BufferGeometry,
  Color,
  DirectionalLight,
  Group,
  HemisphereLight,
  Material,
  Matrix4,
  Mesh,
  Object3D,
  PMREMGenerator,
  Scene,
  ShaderMaterial,
  Vector3,
  Vector4,
  type MeshStandardMaterial,
  type Texture,
  type WebGLProgramParametersWithUniforms,
  type WebGLRenderer,
} from "three";
import {
  ATMOSPHERE_GLSL,
  CLOUDS_GLSL,
  FOG_FRAGMENT,
  FOG_FRAGMENT_PARS,
  FOG_VERTEX,
  FOG_VERTEX_PARS,
  NOISE_GLSL,
} from "./glsl";
import { fogDensity, sunDirection, type Palette, type Quality } from "./palettes";
import type { SiteFrame } from "./site";

/*
  Atmósfera común: uniformes compartidos, cielo, mapa de entorno PMREM del propio cielo y luces.

  El cielo es un triángulo que cubre la pantalla y se pinta el primero, sin escribir
  profundidad: no depende del plano lejano de la cámara. En perspectiva cada píxel mira en su
  dirección real; en ortográfica (rayos paralelos) se le da un abanico de 35° para que el cielo
  tenga el mismo degradado que en perspectiva.
*/

export type AtmosphereUniforms = {
  uEnvSunDir: { value: Vector3 };
  uEnvSunColor: { value: Color };
  uEnvSunLight: { value: Color };
  uEnvSkyLight: { value: Color };
  uEnvBounce: { value: Color };
  uEnvZenith: { value: Color };
  uEnvHorizon: { value: Color };
  uEnvHaze: { value: Color };
  uEnvGround: { value: Color };
  uEnvSite: { value: Vector3 };
  uEnvFog: { value: Vector4 };
  uEnvCloud: { value: Vector4 };
  uEnvCloudTint: { value: Color };
  uEnvCloudStreak: { value: number };
  uEnvGlow: { value: number };
  uEnvTime: { value: number };
  uEnvWind: { value: Vector3 };
  uEnvFar: { value: number };
  uEnvMotion: { value: number };
};

export function createAtmosphereUniforms(palette: Palette, site: SiteFrame): AtmosphereUniforms {
  const sun = new Vector3(...sunDirection(palette));
  const sunColor = new Color(palette.sun.color);
  const wind = new Vector3(palette.wind[0], palette.wind[1], palette.wind[2]);
  // Irradiancia difusa del cielo para los shaders propios (agua, partículas, aves): la luz
  // hemisférica más la parte difusa del mapa de entorno, como la reciben los materiales PBR.
  const skyLight = new Color(palette.hemisphere.sky)
    .multiplyScalar(palette.hemisphere.intensity + palette.environmentIntensity * 0.75);
  const bounce = new Color(palette.hemisphere.ground)
    .multiplyScalar(palette.hemisphere.intensity + palette.environmentIntensity * 0.35);
  return {
    uEnvSunDir: { value: sun },
    uEnvSunColor: { value: sunColor.clone() },
    uEnvSunLight: { value: sunColor.clone().multiplyScalar(palette.sun.intensity) },
    uEnvSkyLight: { value: skyLight },
    uEnvBounce: { value: bounce },
    uEnvZenith: { value: new Color(palette.sky.zenith) },
    uEnvHorizon: { value: new Color(palette.sky.horizon) },
    uEnvHaze: { value: new Color(palette.sky.haze) },
    uEnvGround: { value: new Color(palette.sky.ground) },
    uEnvSite: { value: new Vector3(site.x, 0, site.z) },
    uEnvFog: { value: new Vector4(palette.fog.near, fogDensity(palette), palette.fog.max, palette.fog.height) },
    uEnvCloud: { value: new Vector4(palette.clouds.coverage, palette.clouds.softness, palette.clouds.scale, palette.clouds.height) },
    uEnvCloudTint: { value: new Color(palette.clouds.tint) },
    uEnvCloudStreak: { value: palette.clouds.streak },
    uEnvGlow: { value: palette.sky.sunGlow },
    uEnvTime: { value: palette.start },
    uEnvWind: { value: wind },
    uEnvFar: { value: 1e6 },
    uEnvMotion: { value: 1 },
  };
}

const SKY_VERTEX = /* glsl */ `
varying vec3 vSkyDir;
void main() {
  vec2 ndc = position.xy;
  if (isOrthographic) {
    float aspect = projectionMatrix[1][1] / projectionMatrix[0][0];
    vec3 ray = vec3(ndc.x * aspect * 0.315, ndc.y * 0.315, -1.0);
    vSkyDir = (vec4(ray, 0.0) * viewMatrix).xyz;
  } else {
    vec4 view = inverse(projectionMatrix) * vec4(ndc, 1.0, 1.0);
    vSkyDir = (vec4(view.xyz / view.w, 0.0) * viewMatrix).xyz;
  }
  gl_Position = vec4(ndc, 1.0, 1.0);
}
`;

const SKY_FRAGMENT = /* glsl */ `
uniform float uSkyMode;
varying vec3 vSkyDir;
${NOISE_GLSL}
${ATMOSPHERE_GLSL}
${CLOUDS_GLSL}
void main() {
  vec3 dir = normalize(vSkyDir);
  vec3 color = envSky(dir, 1.0 - uSkyMode);
  #ifdef SKY_CLOUDS
    vec4 cloud = envClouds(dir, uSkyMode > 0.5 ? vec3(0.0) : cameraPosition, SKY_OCTAVES);
    color = mix(color, cloud.rgb, cloud.a);
  #endif
  if (uSkyMode > 0.5) color = mix(color, uEnvGround, smoothstep(0.0, -0.08, dir.y));
  gl_FragColor = vec4(color, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

/** Cúpula del cielo. mode "background" sigue a la cámara; "environment" es para el PMREM. */
export function createSky(uniforms: AtmosphereUniforms, mode: "background" | "environment", quality: Quality): Mesh {
  const material = new ShaderMaterial({
    name: "entorno-cielo",
    uniforms: { ...uniforms, uSkyMode: { value: mode === "environment" ? 1 : 0 } },
    vertexShader: SKY_VERTEX,
    fragmentShader: SKY_FRAGMENT,
    depthTest: false,
    depthWrite: false,
    defines: { SKY_CLOUDS: 1, SKY_OCTAVES: quality === "high" ? 5 : 3 },
  });
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array([-1, -1, 0, 3, -1, 0, -1, 3, 0]), 3));
  const mesh = new Mesh(geometry, material);
  mesh.name = "entorno-cielo";
  mesh.frustumCulled = false;
  mesh.renderOrder = -1000;
  mesh.matrixAutoUpdate = false;
  return mesh;
}

/** Mapa de entorno filtrado (PMREM) del cielo del entorno: el metal de la planta refleja este cielo. */
export function renderSkyEnvironment(gl: WebGLRenderer, uniforms: AtmosphereUniforms, quality: Quality): { texture: Texture; dispose(): void } {
  const scene = new Scene();
  const sky = createSky(uniforms, "environment", quality);
  scene.add(sky);
  const generator = new PMREMGenerator(gl);
  const result = generator.fromScene(scene, 0.02, 0.1, 100, { size: quality === "high" ? 256 : 128 });
  generator.dispose();
  sky.geometry.dispose();
  (sky.material as Material).dispose();
  return { texture: result.texture, dispose: () => result.dispose() };
}

/**
 * Pone el cielo filtrado como entorno de la escena y devuelve cómo dejarla como estaba.
 * Solo restaura si nadie lo ha cambiado entretanto.
 */
export function applySceneEnvironment(scene: Scene, texture: Texture, intensity: number): () => void {
  const previous = { environment: scene.environment, intensity: scene.environmentIntensity };
  scene.environment = texture;
  scene.environmentIntensity = intensity;
  return () => {
    if (scene.environment !== texture) return;
    scene.environment = previous.environment;
    scene.environmentIntensity = previous.intensity;
  };
}

/**
 * Reloj del entorno: avanza solo mientras anima y lleva el instante a los uniformes compartidos.
 * Con el mismo instante, la misma imagen (todo lo animado depende solo de él).
 */
export class EnvironmentClock {
  time: number;
  constructor(start: number) {
    this.time = start;
  }
  /** Avanza (como mucho 0,1 s por fotograma, para no saltar al volver de una pestaña). */
  advance(delta: number, uniforms: AtmosphereUniforms): number {
    this.time += Math.min(Math.max(delta, 0), 0.1);
    uniforms.uEnvTime.value = this.time;
    return this.time;
  }
  sync(uniforms: AtmosphereUniforms) {
    uniforms.uEnvTime.value = this.time;
  }
}

/** Datos de cada fotograma que no dependen de la animación (la niebla se apaga cerca del plano lejano). */
export function setAtmosphereFrame(uniforms: AtmosphereUniforms, far: number) {
  uniforms.uEnvFar.value = far;
}

/** 1 = animando, 0 = quieto (los destellos quedan fijos y encendidos). */
export function setAtmosphereMotion(uniforms: AtmosphereUniforms, moving: boolean) {
  uniforms.uEnvMotion.value = moving ? 1 : 0;
}

export type Lights = { group: Group; sun: DirectionalLight; hemisphere: HemisphereLight; dispose(): void };

/** Sol con sombras ajustadas a la planta y luz hemisférica de cielo y rebote del suelo. */
export function createLights(palette: Palette, site: SiteFrame, quality: Quality, margin = 14): Lights {
  const group = new Group();
  group.name = "entorno-luces";
  const direction = new Vector3(...sunDirection(palette));
  const target = new Object3D();
  const centerY = (site.minY + site.maxY) / 2;
  target.position.set(site.x, centerY, site.z);
  const sun = new DirectionalLight(new Color(palette.sun.color), palette.sun.intensity);
  sun.name = "entorno-sol";
  const distance = 600;
  sun.position.copy(target.position).addScaledVector(direction, distance);
  sun.target = target;
  sun.castShadow = true;
  const size = quality === "high" ? 2048 : 1024;
  sun.shadow.mapSize.set(size, size);
  sun.shadow.bias = -0.0002;
  sun.shadow.normalBias = 0.04;
  sun.shadow.radius = quality === "high" ? 2 : 1;
  // Caja de sombras ajustada: las ocho esquinas de la planta (con margen) en el espacio del sol.
  const view = new Matrix4().lookAt(sun.position, target.position, new Vector3(0, 1, 0)).setPosition(sun.position).invert();
  const min = new Vector3(Infinity, Infinity, Infinity);
  const max = new Vector3(-Infinity, -Infinity, -Infinity);
  const corner = new Vector3();
  for (const sx of [-1, 1]) for (const sy of [site.minY - 1, site.maxY + 2]) for (const sz of [-1, 1]) {
    corner.set(site.x + sx * (site.halfX + margin), sy, site.z + sz * (site.halfZ + margin)).applyMatrix4(view);
    min.min(corner);
    max.max(corner);
  }
  const shadow = sun.shadow.camera;
  shadow.left = min.x;
  shadow.right = max.x;
  shadow.bottom = min.y;
  shadow.top = max.y;
  shadow.near = Math.max(1, -max.z - 60);
  shadow.far = -min.z + 60;
  shadow.updateProjectionMatrix();
  sun.shadow.needsUpdate = true;
  const hemisphere = new HemisphereLight(new Color(palette.hemisphere.sky), new Color(palette.hemisphere.ground), palette.hemisphere.intensity);
  hemisphere.name = "entorno-hemisferica";
  group.add(target, sun, hemisphere);
  return { group, sun, hemisphere, dispose: () => sun.shadow.dispose() };
}

/** Inyecta la niebla radial en un material estándar (o físico) sin perder luz, sombras ni entorno. */
export function withRadialFog<T extends MeshStandardMaterial>(material: T, uniforms: AtmosphereUniforms, key = "fog"): T {
  const previous = material.onBeforeCompile;
  material.onBeforeCompile = (shader: WebGLProgramParametersWithUniforms, renderer: WebGLRenderer) => {
    previous.call(material, shader, renderer);
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", `#include <common>\n${FOG_VERTEX_PARS}`)
      .replace("#include <project_vertex>", `#include <project_vertex>\n${FOG_VERTEX}`);
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>\n${FOG_FRAGMENT_PARS}`)
      .replace("#include <tonemapping_fragment>", `${FOG_FRAGMENT}\n#include <tonemapping_fragment>`);
  };
  const previousKey = material.customProgramCacheKey.bind(material);
  material.customProgramCacheKey = () => `${previousKey()}|entorno-${key}`;
  return material;
}

/** Recorre y libera geometrías y materiales de un subárbol del entorno. */
export function disposeTree(root: Object3D) {
  const seen = new Set<object>();
  root.traverse(object => {
    const mesh = object as Mesh;
    if (mesh.geometry && !seen.has(mesh.geometry)) { seen.add(mesh.geometry); mesh.geometry.dispose(); }
    const material = mesh.material as Material | Material[] | undefined;
    for (const m of Array.isArray(material) ? material : material ? [material] : []) {
      if (seen.has(m)) continue;
      seen.add(m);
      m.dispose();
    }
  });
}
