import { describe, expect, it } from "vitest";
import { readViews, validPose, viewsKey } from "./saved-views";
describe("vistas por IFC", () => {
  it("descarta almacenamiento corrupto y cámaras inválidas", () => {
    expect(readViews("{" )).toEqual([]);
    expect(validPose({ eye: [0, 0, 0], target: [0, 0, 0], zoom: 50 })).toBe(false);
    const pose = { eye: [1, 2, 3], target: [0, 0, 0], zoom: 50 };
    expect(readViews(JSON.stringify([{ id: "one", name: "Plano", pose }]))).toHaveLength(1);
    expect(validPose({ ...pose, zoom: Infinity })).toBe(false);
    expect(viewsKey("a.ifc")).not.toBe(viewsKey("b.ifc"));
  });
});
