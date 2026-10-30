import { BufferAttribute, type BufferGeometry } from "three";

/** Solo coordenadas de textura: no cambia posiciones, índices ni normales del IFC. */
export function addSurfaceUV(geometry: BufferGeometry) {
  if (geometry.getAttribute("uv")) return;
  const positions = geometry.getAttribute("position");
  geometry.computeBoundingBox();
  const box = geometry.boundingBox;
  if (!box || !positions) return;
  const sizes = [box.max.x - box.min.x, box.max.y - box.min.y, box.max.z - box.min.z];
  const axes = [0, 1, 2].sort((a, b) => sizes[b]! - sizes[a]!);
  const u = axes[1]!, v = axes[0]!;
  const min = [box.min.x, box.min.y, box.min.z];
  const uv = new Float32Array(positions.count * 2);
  for (let i = 0; i < positions.count; i++) {
    uv[i * 2] = (positions.getComponent(i, u) - min[u]!) / Math.max(sizes[u]!, .001);
    uv[i * 2 + 1] = (positions.getComponent(i, v) - min[v]!) / Math.max(sizes[v]!, .001);
  }
  geometry.setAttribute("uv", new BufferAttribute(uv, 2));
}
