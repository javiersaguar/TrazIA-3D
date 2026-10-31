import { describe, expect, it } from "vitest";
import { BoxGeometry } from "three";
import { makeSection } from "./section-geometry";
import type { PreparedProduct } from "./model-resource";

describe("sección desde triángulos", () => {
  it("conserva dos sólidos disjuntos en vez de tratar el segundo como un hueco", () => {
    const boxes = [-2, 2].map(x => new BoxGeometry(1, 1, 1).translate(x, 0, 0));
    const parts = boxes.map(box => ({ positions: box.attributes.position!.array,
      indices: new Uint32Array(box.index!.array) }));
    const product = { center: [0, 0, 0], parts } as unknown as PreparedProduct;
    const section = makeSection(product, .1)!;
    expect(section).toBeTruthy();
    const positions = section.attributes.position!, index = section.index!;
    let area = 0;
    for (let i = 0; i < index.count; i += 3) {
      const [a, b, c] = [index.getX(i), index.getX(i + 1), index.getX(i + 2)];
      area += Math.abs((positions.getX(b) - positions.getX(a)) * (positions.getZ(c) - positions.getZ(a))
        - (positions.getX(c) - positions.getX(a)) * (positions.getZ(b) - positions.getZ(a))) / 2;
    }
    expect(area).toBeCloseTo(2, 5);
    expect(makeSection(product, 2)).toBeNull();
    section.dispose(); boxes.forEach(box => box.dispose());
  });
});
