import { describe, expect, it } from "vitest";
import { Vector3 } from "three";
import { buildColumn, buildHeatExchanger, buildHorizontalDrum, buildTank, buildVerticalVessel } from "./equipment-geometry";

describe("familias ilustrativas (sin IFC)", () => {
  for (const build of [buildVerticalVessel, buildHorizontalDrum, buildColumn, buildHeatExchanger, buildTank]) {
    it(`${build.name}: geometría finita, escala métrica y pernos instanciables`, () => {
      const model = build();
      try {
        expect(model.source).toBe("illustrative");
        expect(model.bolts.length).toBeGreaterThan(10);
        expect(model.batches.length).toBeLessThanOrEqual(4);
        const size = model.bounds.getSize(new Vector3());
        expect(Math.max(size.x, size.y, size.z)).toBeGreaterThan(3);
        expect(Math.max(size.x, size.y, size.z)).toBeLessThan(12);
        let triangles = 0;
        for (const batch of model.batches) {
          const positions = batch.geometry.getAttribute("position");
          expect(Array.from(positions.array).every(Number.isFinite)).toBe(true);
          triangles += positions.count / 3;
        }
        triangles += (model.boltGeometry.index?.count ?? model.boltGeometry.getAttribute("position").count) / 3 * model.bolts.length;
        // Dos recipientes y dos pases principales en el holograma, con margen para overlays.
        expect(triangles * 4).toBeLessThan(190_000);
      } finally { model.dispose(); }
    });
  }
  it("distingue la orientación horizontal y la columna esbelta", () => {
    const horizontal = buildHorizontalDrum(), column = buildColumn();
    try {
      const h = horizontal.bounds.getSize(new Vector3()), c = column.bounds.getSize(new Vector3());
      expect(h.x).toBeGreaterThan(h.y * 1.5);
      expect(c.y).toBeGreaterThan(c.x * 2);
    } finally { horizontal.dispose(); column.dispose(); }
  });
});
