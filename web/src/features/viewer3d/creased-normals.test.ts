import { describe, expect, it } from "vitest";
import { creasedNormals } from "./creased-normals";

/** Malla «sopa de triángulos» como la de web-ifc: tres vértices propios por triángulo. */
function soup(triangles: number[][][]) {
  const positions = new Float32Array(triangles.flat(2));
  const indices = new Uint32Array(positions.length / 3).map((_, i) => i);
  return { positions, indices };
}

function cylinder(segments: number, radius = 1, height = 2) {
  const triangles: number[][][] = [];
  for (let i = 0; i < segments; i++) {
    const a0 = (i / segments) * Math.PI * 2, a1 = ((i + 1) / segments) * Math.PI * 2;
    const p = (a: number, y: number) => [radius * Math.cos(a), y, radius * Math.sin(a)];
    triangles.push([p(a0, 0), p(a1, height), p(a1, 0)], [p(a0, 0), p(a0, height), p(a1, height)]);
    triangles.push([[0, height, 0], p(a1, height), p(a0, height)]); // tapa
  }
  return soup(triangles);
}

describe("normales con ángulo de pliegue", () => {
  it("suaviza la virola de un cilindro y mantiene plana la tapa", () => {
    const { positions, indices } = cylinder(24);
    const normals = creasedNormals(positions, indices, 38);
    for (let v = 0; v < positions.length / 3; v++) {
      const [x, y, z] = [positions[v * 3]!, positions[v * 3 + 1]!, positions[v * 3 + 2]!];
      const n = [normals[v * 3]!, normals[v * 3 + 1]!, normals[v * 3 + 2]!];
      expect(Math.hypot(...n)).toBeCloseTo(1, 5);
      const cap = Math.floor(v / 3) % 3 === 2;
      if (cap) {
        expect(n[1]).toBeCloseTo(1, 5);
      } else {
        // En la virola la normal es radial, no la de la cara.
        const r = Math.hypot(x, z);
        expect(n[0]).toBeCloseTo(x / r, 4);
        expect(n[1]).toBeCloseTo(0, 5);
        expect(n[2]).toBeCloseTo(z / r, 4);
        expect(y === 0 || y === 2).toBe(true);
      }
    }
  });

  it("no redondea las aristas vivas de una caja", () => {
    const q = (a: number[], b: number[], c: number[], d: number[]) => [[a, b, c], [a, c, d]];
    const box = soup([
      ...q([0, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0]),
      ...q([0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]),
      ...q([0, 0, 0], [0, 0, 1], [0, 1, 1], [0, 1, 0]),
      ...q([1, 0, 0], [1, 1, 0], [1, 1, 1], [1, 0, 1]),
      ...q([0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]),
      ...q([0, 1, 0], [0, 1, 1], [1, 1, 1], [1, 1, 0]),
    ]);
    const normals = creasedNormals(box.positions, box.indices, 38);
    for (let t = 0; t < 12; t++) {
      const face = [normals[t * 9]!, normals[t * 9 + 1]!, normals[t * 9 + 2]!];
      // Los tres vértices de cada triángulo conservan la normal de su cara (un eje).
      expect(Math.max(...face.map(Math.abs))).toBeCloseTo(1, 5);
      for (let k = 1; k < 3; k++) {
        for (let axis = 0; axis < 3; axis++) expect(normals[t * 9 + k * 3 + axis]).toBeCloseTo(face[axis]!, 5);
      }
    }
  });

  it("deja la normal original en un triángulo degenerado", () => {
    const { positions, indices } = soup([[[0, 0, 0], [1, 0, 0], [2, 0, 0]]]);
    const normals = creasedNormals(positions, indices, 38, new Float32Array([0, 0, 1, 0, 0, 1, 0, 0, 1]));
    expect([...normals]).toEqual([0, 0, 1, 0, 0, 1, 0, 0, 1]);
  });

  it("procesa una planta de 100.000 triángulos en un tiempo de carga razonable", () => {
    const { positions, indices } = cylinder(48 * 700, 1, 2);
    const start = performance.now();
    creasedNormals(positions, indices, 38);
    // Referencia en portátil: ~25 ms; el margen cubre máquinas de integración lentas.
    expect(performance.now() - start).toBeLessThan(400);
  });
});
