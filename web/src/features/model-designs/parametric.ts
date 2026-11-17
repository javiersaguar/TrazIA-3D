import specs from "./design-specs.json";

/*
  Diseños paramétricos del catálogo (scripts/export_design_specs.py). La malla de cada pieza se
  calcula igual que `scripts/make_industrial_designs.py::mesh`, que generó los IFC publicados:
  un IFC regenerado sin cambios tiene los mismos vértices que el de web/public/demo/industriales.
*/

export type Vec3 = [number, number, number];
export type Axis = "" | "x" | "y" | "z";
export type PartSpec = { name: string; low: Vec3; high: Vec3; axis: Axis; ends: [number, number] };
/** `size` en mm y en el orden del generador: ancho (X), alto (Z), fondo (Y). */
export type DesignSpec = {
  tag: string;
  family: string;
  name: string;
  origin: "boceto" | "industrial";
  ifc: string | null;
  size: Vec3;
  parts: PartSpec[];
};
export type PartMesh = { name: string; vertices: Vec3[]; triangles: [number, number, number][] };

/** Cambios de una persona sobre un diseño: medidas de la envolvente y escala u ocultación por pieza. */
export type DesignEdits = {
  size?: Partial<{ width: number; height: number; depth: number }>;
  parts?: Record<string, { scale?: number; hidden?: boolean }>;
};

export const DESIGNS = specs.designs as DesignSpec[];
export const FAMILY_NAMES = specs.families as Record<string, string>;

const INDICES: Record<string, [number, number, number]> = { x: [1, 2, 0], y: [2, 0, 1], z: [0, 1, 2] };
const round4 = (value: number) => Math.round(value * 1e4) / 1e4;

export function designByTag(tag: string | null | undefined) {
  return DESIGNS.find((design) => design.tag === tag);
}

export function partMesh(part: PartSpec, size: Vec3): PartMesh {
  const [a, b, c] = INDICES[part.axis || "z"]!;
  const [w, h, d] = size;
  const spans: Vec3 = [w, d, h];
  const lo = (i: number) => part.low[i]!;
  const hi = (i: number) => part.high[i]!;
  const ring: [number, number][] = part.axis
    ? Array.from({ length: 32 }, (_, i) => [Math.cos((i * Math.PI * 2) / 32), Math.sin((i * Math.PI * 2) / 32)])
    : [[-1, -1], [1, -1], [1, 1], [-1, 1]];
  const n = ring.length;
  const vertices: Vec3[] = [];
  [lo(c), hi(c)].forEach((level, k) => {
    const ratio = part.ends[k]!;
    for (const [u, v] of ring) {
      const point: Vec3 = [0, 0, 0];
      point[a] = (lo(a) + hi(a) + u * ratio * (hi(a) - lo(a))) / 2;
      point[b] = (lo(b) + hi(b) + v * ratio * (hi(b) - lo(b))) / 2;
      point[c] = level;
      vertices.push(point.map((value, i) => round4((value * spans[i]!) / 100)) as Vec3);
    }
  });
  const triangles: [number, number, number][] = [];
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    triangles.push([i, j, j + n], [i, j + n, i + n]);
  }
  for (let i = 1; i < n - 1; i++) triangles.push([0, i + 1, i], [n, n + i, n + i + 1]);
  return { name: part.name, vertices, triangles };
}

const clamp = (value: number, low: number, high: number) => Math.min(high, Math.max(low, value));

/** Escala una pieza sobre su centro, dentro de la envolvente (0–100 %). */
function scalePart(part: PartSpec, scale: number): PartSpec {
  if (scale === 1) return part;
  const low = [...part.low] as Vec3;
  const high = [...part.high] as Vec3;
  for (let i = 0; i < 3; i++) {
    const center = (part.low[i]! + part.high[i]!) / 2;
    const half = ((part.high[i]! - part.low[i]!) / 2) * scale;
    low[i] = clamp(center - half, 0, 99.9);
    high[i] = clamp(center + half, low[i]! + 0.1, 100);
  }
  return { ...part, low, high };
}

/** El diseño con los cambios aplicados; sin cambios devuelve el mismo objeto. */
export function applyEdits(design: DesignSpec, edits: DesignEdits | undefined): DesignSpec {
  if (!edits || isPristine(edits)) return design;
  const [width, height, depth] = design.size;
  const size: Vec3 = [edits.size?.width ?? width, edits.size?.height ?? height, edits.size?.depth ?? depth];
  const parts = design.parts
    .filter((part) => !edits.parts?.[part.name]?.hidden)
    .map((part) => scalePart(part, edits.parts?.[part.name]?.scale ?? 1));
  return { ...design, size, parts };
}

export function isPristine(edits: DesignEdits | undefined) {
  if (!edits) return true;
  const sizeChanged = Object.values(edits.size ?? {}).some((value) => value !== undefined);
  const partsChanged = Object.values(edits.parts ?? {}).some((p) => p.hidden || (p.scale !== undefined && p.scale !== 1));
  return !sizeChanged && !partsChanged;
}

export function designMeshes(design: DesignSpec): PartMesh[] {
  return design.parts.map((part) => partMesh(part, design.size));
}

/** Envolvente real de las mallas en mm: ancho (X), fondo (Y) y alto (Z). */
export function envelope(meshes: PartMesh[]) {
  const low = [Infinity, Infinity, Infinity];
  const high = [-Infinity, -Infinity, -Infinity];
  for (const mesh of meshes) for (const vertex of mesh.vertices) for (let i = 0; i < 3; i++) {
    low[i] = Math.min(low[i]!, vertex[i]!);
    high[i] = Math.max(high[i]!, vertex[i]!);
  }
  if (!meshes.length) return { width: 0, depth: 0, height: 0 };
  return { width: high[0]! - low[0]!, depth: high[1]! - low[1]!, height: high[2]! - low[2]! };
}
