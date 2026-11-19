import { describe, expect, it } from "vitest";
import type { Bounds, IfcAssembly } from "@/workers/ifc-protocol";
import { buildHierarchy, clickTarget, isWithin, levelUp, type ProductLike } from "./hierarchy";

const box = (min: [number, number, number], max: [number, number, number]): Bounds => ({ min, max });
const product = (semanticId: string, globalId: string, parentGlobalId?: string): ProductLike => ({
  semanticId, globalId, name: semanticId, ifcType: "IfcBuildingElementProxy", psets: {},
  bounds: box([0, 0, 0], [1, 1, 1]), center: [0.5, 0.5, 0.5], parentGlobalId,
  parts: [{ indices: new Uint32Array(36) }],
});
const pump: IfcAssembly = {
  expressId: 1, globalId: "G-P", name: "P-150", tag: "P-150", ifcType: "IfcPump", semanticId: "element:P-150",
  psets: {}, children: ["G-C", "G-M"], bounds: box([0, 0, 0], [3, 1, 1]), center: [1.5, 0.5, 0.5],
};

describe("selección jerárquica (C2)", () => {
  const hierarchy = buildHierarchy([
    product("detail:element:P-150/carcasa", "G-C", "G-P"),
    product("detail:element:P-150/motor-a", "G-M", "G-P"),
    product("element:V-110", "G-V"),
  ], [pump]);

  it("agrupa las piezas bajo su equipo", () => {
    expect(hierarchy.nested).toBe(true);
    expect(hierarchy.roots).toEqual(["element:P-150", "element:V-110"]);
    const node = hierarchy.nodes.get("element:P-150")!;
    expect(node.isAssembly).toBe(true);
    expect(node.childIds).toEqual(["detail:element:P-150/carcasa", "detail:element:P-150/motor-a"]);
    expect(node.productIds).toHaveLength(2);
    expect(node.triangles).toBe(0);
    expect(hierarchy.nodes.get("detail:element:P-150/carcasa")!.triangles).toBe(12);
  });

  it("primer clic al equipo, segundo a la pieza, Esc vuelve arriba", () => {
    const motor = "detail:element:P-150/motor-a";
    expect(clickTarget(hierarchy, motor)).toBe("element:P-150");
    expect(clickTarget(hierarchy, motor, "element:V-110")).toBe("element:P-150");
    expect(clickTarget(hierarchy, motor, "element:P-150")).toBe(motor);
    expect(clickTarget(hierarchy, motor, motor)).toBe(motor);
    // Con una pieza seleccionada, la pieza hermana vuelve a pasar por el equipo.
    expect(clickTarget(hierarchy, "detail:element:P-150/carcasa", motor)).toBe("element:P-150");
    expect(levelUp(hierarchy, motor)).toBe("element:P-150");
    expect(levelUp(hierarchy, "element:P-150")).toBeUndefined();
    expect(isWithin(hierarchy, motor, "element:P-150")).toBe(true);
    expect(isWithin(hierarchy, "element:V-110", "element:P-150")).toBe(false);
  });

  it("sin ensamblajes cada producto se selecciona directamente", () => {
    const flat = buildHierarchy([product("element:V-110", "G-V"), product("element:P-150", "G-P2")]);
    expect(flat.nested).toBe(false);
    expect(clickTarget(flat, "element:P-150")).toBe("element:P-150");
    expect(levelUp(flat, "element:P-150")).toBeUndefined();
  });
});
