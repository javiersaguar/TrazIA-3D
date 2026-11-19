import {
  Mesh,
  MeshStandardMaterial,
  type BufferGeometry,
  type WebGLProgramParametersWithUniforms,
  type WebGLRenderer,
} from "three";
import { withRadialFog, type AtmosphereUniforms } from "./atmosphere";
import type { MeshBuilder } from "./builder";

/*
  Material del atrezo: PBR estándar de three (sol, sombras, luz hemisférica y mapa de entorno del
  cielo) con color, rugosidad y metalicidad por vértice y la niebla radial común. Así cada
  conjunto de atrezo (un barco, una unidad de refinería, una escollera) sale en un draw call.
*/

export function createPropMaterial(atmosphere: AtmosphereUniforms, options: { key?: string; flatShading?: boolean } = {}): MeshStandardMaterial {
  const material = new MeshStandardMaterial({ vertexColors: true, roughness: 1, metalness: 1, flatShading: options.flatShading ?? false });
  material.name = `entorno-atrezo${options.key ? `-${options.key}` : ""}`;
  material.onBeforeCompile = (shader: WebGLProgramParametersWithUniforms) => {
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nattribute vec2 surface;\nvarying vec2 vSurface;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvSurface = surface;");
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec2 vSurface;")
      .replace("#include <roughnessmap_fragment>", "float roughnessFactor = roughness * vSurface.x;")
      .replace("#include <metalnessmap_fragment>", "float metalnessFactor = metalness * vSurface.y;");
  };
  const key = `atrezo${options.flatShading ? "-plano" : ""}`;
  material.customProgramCacheKey = () => key;
  return withRadialFog(material, atmosphere, key);
}

/** Malla de atrezo a partir de un constructor: sombra arrojada solo si está cerca de la planta. */
export function propMesh(builder: MeshBuilder, material: MeshStandardMaterial, name: string, castShadow = false): Mesh {
  const mesh = new Mesh(builder.toGeometry(), material);
  mesh.name = name;
  mesh.castShadow = castShadow;
  mesh.receiveShadow = castShadow;
  mesh.matrixAutoUpdate = false;
  mesh.updateMatrix();
  return mesh;
}

/** Inyección genérica: añade código GLSL a un material estándar sin perder lo que ya tuviera. */
export function patchMaterial(
  material: MeshStandardMaterial,
  key: string,
  patch: (shader: WebGLProgramParametersWithUniforms, renderer: WebGLRenderer) => void,
) {
  const previous = material.onBeforeCompile;
  material.onBeforeCompile = (shader, renderer) => {
    previous.call(material, shader, renderer);
    patch(shader, renderer);
  };
  const previousKey = material.customProgramCacheKey.bind(material);
  material.customProgramCacheKey = () => `${previousKey()}|${key}`;
  return material;
}

export function geometryTriangles(geometry: BufferGeometry): number {
  return (geometry.index ? geometry.index.count : geometry.getAttribute("position").count) / 3;
}
