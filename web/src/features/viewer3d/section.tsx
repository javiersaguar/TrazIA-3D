"use client";

import { useEffect, useMemo } from "react";
import { BufferAttribute, BufferGeometry, DoubleSide, ShapeUtils, Vector2 } from "three";
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

function makeSection(product: PreparedProduct, height: number): BufferGeometry | null {
  const loops = contours(product, height).map(loop => loop.map(point => new Vector2(...point)));
  loops.sort((a, b) => Math.abs(ShapeUtils.area(b)) - Math.abs(ShapeUtils.area(a)));
  if (!loops[0]) return null;
  const triangles = ShapeUtils.triangulateShape(loops[0], loops.slice(1));
  const points = loops.flat();
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(points.flatMap(point => [point.x, height + .0004, point.y])), 3));
  geometry.setIndex(triangles.flat());
  return geometry;
}

const vertexShader = `varying vec2 cutCoord; void main(){vec4 world=modelMatrix*vec4(position,1.);cutCoord=world.xz;gl_Position=projectionMatrix*viewMatrix*world;}`;
const fragmentShader = `varying vec2 cutCoord; void main(){float stripe=step(.8,fract((cutCoord.x+cutCoord.y)*14.));gl_FragColor=vec4(mix(vec3(.13,.21,.30),vec3(.5,.65,.82),stripe),1.);}`;

export function SectionCaps({ products, height }: { products: PreparedProduct[]; height: number }) {
  const caps = useMemo(() => products.map(product => makeSection(product, height)).filter((geometry): geometry is BufferGeometry => !!geometry), [products, height]);
  useEffect(() => () => { caps.forEach(geometry => geometry.dispose()); }, [caps]);
  return <>{caps.map((geometry, index) => <mesh key={index} geometry={geometry} renderOrder={2}>
    <shaderMaterial vertexShader={vertexShader} fragmentShader={fragmentShader} side={DoubleSide} />
  </mesh>)}</>;
}
