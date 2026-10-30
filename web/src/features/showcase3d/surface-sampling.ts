import { Mesh, Vector3 } from "three";
import { MeshSurfaceSampler } from "three/addons/math/MeshSurfaceSampler.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import type { EquipmentGeometry } from "./equipment-geometry";

export function randomSequence(seed = 2026) {
  return () => {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

export function sampleSurface(model: EquipmentGeometry, count = 18_000) {
  const geometry = mergeGeometries(model.batches.map(b => b.geometry))!;
  const mesh = new Mesh(geometry);
  const sampler = new MeshSurfaceSampler(mesh);
  // API presente en three 0.186; la declaración de @types/three aún no la incluye.
  (sampler as MeshSurfaceSampler & { setRandomGenerator(fn: () => number): MeshSurfaceSampler }).setRandomGenerator(randomSequence());
  sampler.build();
  const point = new Vector3(), result = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) { sampler.sample(point); point.toArray(result, i * 3); }
  geometry.dispose();
  if (!Array.isArray(mesh.material)) mesh.material.dispose();
  return result;
}

export function scatterSurface(points: Float32Array) {
  const result = new Float32Array(points.length), random = randomSequence(42);
  for (let i = 0; i < points.length; i += 3) {
    result[i] = (random() - .5) * 12;
    result[i + 1] = random() * 9;
    result[i + 2] = (random() - .5) * 12;
  }
  return result;
}
