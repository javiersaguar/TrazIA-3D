import type { Bounds, Vec3 } from "@/workers/ifc-protocol";

/*
  Dónde corta el IFC la lámina de agua.

  Se recorren los triángulos de las piezas que cruzan la cota del agua y se guarda el segmento en
  que cada triángulo corta el plano. Los puntos se agrupan por celdas vecinas (una pata, un
  pilote, una defensa) y de cada grupo sale su centro y su radio. El agua pinta espuma alrededor
  de cada contacto y una estela aguas abajo. Se lee la geometría real del modelo: si cambia el
  jacket, cambia la espuma.
*/

export type Contact = { x: number; z: number; radius: number; weight: number };

type Part = { positions: ArrayLike<number>; indices: ArrayLike<number> };
export type ContactProduct = { center: Vec3; bounds: Bounds; parts: readonly Part[] };

export type ContactOptions = {
  /** Lado de la celda de agrupación, en metros. */
  cell?: number;
  /** Número máximo de contactos (el shader tiene un número fijo de huecos). */
  limit?: number;
  /** Radio máximo: algo más grande no es una pata sino un muelle o un casco. */
  maxRadius?: number;
};

export const CONTACT_LIMIT = 24;

export function waterlineContacts(
  products: readonly ContactProduct[],
  level: number,
  options: ContactOptions = {},
): Contact[] {
  const cell = options.cell ?? 0.8;
  const limit = options.limit ?? CONTACT_LIMIT;
  const maxRadius = options.maxRadius ?? 6;
  const points: number[] = [];
  for (const product of products) {
    if (product.bounds.min[1] > level || product.bounds.max[1] < level) continue;
    const [cx, cy, cz] = product.center;
    for (const part of product.parts) {
      const p = part.positions;
      const index = part.indices;
      for (let t = 0; t + 2 < index.length; t += 3) {
        const ia = index[t]! * 3, ib = index[t + 1]! * 3, ic = index[t + 2]! * 3;
        const ya = p[ia + 1]! + cy - level;
        const yb = p[ib + 1]! + cy - level;
        const yc = p[ic + 1]! + cy - level;
        if ((ya > 0 && yb > 0 && yc > 0) || (ya < 0 && yb < 0 && yc < 0)) continue;
        // Cada arista que cruza el plano aporta un punto del corte.
        const edges: [number, number, number, number][] = [[ia, ya, ib, yb], [ib, yb, ic, yc], [ic, yc, ia, ya]];
        for (const [i0, y0, i1, y1] of edges) {
          if ((y0 > 0) === (y1 > 0) || y0 === y1) continue;
          const s = y0 / (y0 - y1);
          points.push(
            p[i0]! + (p[i1]! - p[i0]!) * s + cx,
            p[i0 + 2]! + (p[i1 + 2]! - p[i0 + 2]!) * s + cz,
          );
        }
      }
    }
  }
  return clusterContacts(points, cell, limit, maxRadius);
}

/** Agrupa puntos (x, z) por celdas contiguas y devuelve un círculo por grupo, de mayor a menor. */
export function clusterContacts(flat: readonly number[], cell: number, limit = CONTACT_LIMIT, maxRadius = 6): Contact[] {
  const count = flat.length / 2;
  if (!count) return [];
  const cells = new Map<string, number[]>();
  const key = (i: number, j: number) => `${i}:${j}`;
  for (let n = 0; n < count; n++) {
    const id = key(Math.floor(flat[n * 2]! / cell), Math.floor(flat[n * 2 + 1]! / cell));
    const list = cells.get(id);
    if (list) list.push(n); else cells.set(id, [n]);
  }
  const parent = new Map<string, string>();
  const find = (a: string): string => {
    let root = a;
    while (parent.get(root) !== root) root = parent.get(root)!;
    let node = a;
    while (parent.get(node) !== root) { const next = parent.get(node)!; parent.set(node, root); node = next; }
    return root;
  };
  for (const id of cells.keys()) parent.set(id, id);
  for (const id of cells.keys()) {
    const [i, j] = id.split(":").map(Number) as [number, number];
    for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) {
      const other = key(i + di, j + dj);
      if (!cells.has(other)) continue;
      const a = find(id), b = find(other);
      if (a !== b) parent.set(a < b ? b : a, a < b ? a : b);
    }
  }
  const groups = new Map<string, number[]>();
  for (const [id, members] of cells) {
    const root = find(id);
    const list = groups.get(root);
    if (list) list.push(...members); else groups.set(root, [...members]);
  }
  const contacts: Contact[] = [];
  for (const members of groups.values()) {
    let sx = 0, sz = 0;
    for (const n of members) { sx += flat[n * 2]!; sz += flat[n * 2 + 1]!; }
    const x = sx / members.length, z = sz / members.length;
    let radius = 0;
    for (const n of members) radius = Math.max(radius, Math.hypot(flat[n * 2]! - x, flat[n * 2 + 1]! - z));
    if (radius < 0.04 || radius > maxRadius) continue;
    contacts.push({ x, z, radius, weight: Math.min(1, 0.35 + radius / 1.5) });
  }
  contacts.sort((a, b) => b.radius - a.radius || a.x - b.x || a.z - b.z);
  return contacts.slice(0, limit);
}
