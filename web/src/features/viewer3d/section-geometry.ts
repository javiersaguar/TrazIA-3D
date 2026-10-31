import { BufferAttribute, BufferGeometry, ShapeUtils, Vector2 } from "three";
import type { PreparedProduct } from "./model-resource";

type Point = [number, number];
const key = (point: Point) => `${Math.round(point[0] * 1e5)},${Math.round(point[1] * 1e5)}`;

function contours(product: PreparedProduct, height: number): Point[][] {
  const vertices = new Map<string, Point>(), neighbors = new Map<string, Set<string>>();
  for (const part of product.parts) {
    for (let i = 0; i < part.indices.length; i += 3) {
      const points = [0, 1, 2].map(corner => {
        const offset = part.indices[i + corner]! * 3;
        return [part.positions[offset]! + product.center[0], part.positions[offset + 1]! + product.center[1],
          part.positions[offset + 2]! + product.center[2]];
      });
      const hits: Point[] = [];
      for (let edge = 0; edge < 3; edge++) {
        const a = points[edge]!, b = points[(edge + 1) % 3]!;
        const da = a[1]! - height, db = b[1]! - height;
        if ((da < 0 && db > 0) || (da > 0 && db < 0)) {
          const t = da / (da - db);
          hits.push([a[0]! + (b[0]! - a[0]!) * t, a[2]! + (b[2]! - a[2]!) * t]);
        }
      }
      if (hits.length !== 2) continue;
      const a = key(hits[0]!), b = key(hits[1]!);
      if (a === b) continue;
      vertices.set(a, hits[0]!); vertices.set(b, hits[1]!);
      if (!neighbors.has(a)) neighbors.set(a, new Set());
      if (!neighbors.has(b)) neighbors.set(b, new Set());
      neighbors.get(a)!.add(b); neighbors.get(b)!.add(a);
    }
  }
  const visited = new Set<string>(), loops: Point[][] = [];
  for (const start of neighbors.keys()) {
    if (visited.has(start) || neighbors.get(start)!.size !== 2) continue;
    const loop: Point[] = [];
    let current = start, previous = "";
    do {
      visited.add(current); loop.push(vertices.get(current)!);
      const next = [...(neighbors.get(current) ?? [])].find(value => value !== previous);
      if (!next) break;
      previous = current; current = next;
    } while (current !== start && !visited.has(current));
    if (current === start && loop.length >= 3) loops.push(loop);
  }
  return loops;
}

export function makeSection(product: PreparedProduct, height: number): BufferGeometry | null {
  const loops = contours(product, height).map(loop => loop.map(point => new Vector2(...point)));
  loops.sort((a, b) => Math.abs(ShapeUtils.area(b)) - Math.abs(ShapeUtils.area(a)));
  if (!loops[0]) return null;
  // Un corte puede contener varios sólidos disjuntos. Solo los contornos interiores son huecos.
  const inside = (p: Vector2, polygon: Vector2[]) => {
    let hit = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const a = polygon[i]!, b = polygon[j]!;
      if ((a.y > p.y) !== (b.y > p.y) && p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x) hit = !hit;
    }
    return hit;
  };
  const depth = loops.map((loop, i) => loops.slice(0, i).filter(other => inside(loop[0]!, other)).length);
  const points: Vector2[] = [], triangles: number[][] = [];
  loops.forEach((loop, i) => {
    if (depth[i]! % 2 !== 0) return;
    const holes = loops.filter((hole, j) => depth[j] === depth[i]! + 1 && inside(hole[0]!, loop));
    const offset = points.length;
    points.push(...loop, ...holes.flat());
    triangles.push(...ShapeUtils.triangulateShape(loop, holes).map(t => t.map(index => index + offset)));
  });
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(points.flatMap(point => [point.x, height + .0004, point.y])), 3));
  geometry.setIndex(triangles.flat());
  return geometry;
}

