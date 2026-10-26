import { describe, expect, it } from "vitest";
import { changeSteps, clampProgress, interpolateBounds, morphState, pairByGlobalId } from "./morph.ts";
import { semanticId } from "../viewer3d/semantic.ts";

const product = (globalId, center, size = [2, 6, 2]) => ({ globalId, center,
  bounds: { min: center.map((v, i) => v - size[i] / 2), max: center.map((v, i) => v + size[i] / 2) } });

describe("identidad y correspondencia IFC", () => {
  it("empareja por GUID aunque cambien el orden y el nombre", () => {
    const a = [{ globalId: "a", name: "N3" }, { globalId: "b", name: "Virola" }];
    const b = [{ globalId: "b", name: "Otro tag" }, { globalId: "a", name: "Nueva etiqueta" }];
    expect(pairByGlobalId(a, b).map(p => p.after.name)).toEqual(["Nueva etiqueta", "Otro tag"]);
  });
  it("preserva altas y bajas", () => {
    const pairs = pairByGlobalId([{ globalId: "removed" }], [{ globalId: "new" }]);
    expect(pairs[0].after).toBeNull(); expect(pairs[1].before).toBeNull();
  });
  it("rechaza identificadores ambiguos", () => {
    expect(() => pairByGlobalId([{ globalId: "a" }, { globalId: "a" }], [])).toThrow();
    expect(() => pairByGlobalId([], [{ globalId: "" }])).toThrow();
  });
  it("conserva el contrato semántico de las pantallas", () => {
    expect(semanticId("V-101", "IfcTank")).toBe("shell");
    expect(semanticId("V-101/top_head", "IfcBuildingElementProxy")).toBe("head-top");
    expect(semanticId("V-101/N3", "IfcPipeSegment")).toBe("nozzle:N3");
    expect(semanticId("etiqueta nueva", "IfcPipeSegment", { TrazIA_Identity: { ComponentId: "N4" } })).toBe("nozzle:N4");
  });
});

describe("interpolación de revisiones", () => {
  const a = product("stable", [0, 4.2, 0]), b = product("stable", [0, 4.6, 0], [2, 6.5, 2]);
  it("reproduce las cajas inicial y final", () => {
    expect(interpolateBounds(a.bounds, b.bounds, 0)).toEqual({ position: a.center, scale: [1, 1, 1] });
    expect(interpolateBounds(a.bounds, b.bounds, 1).position).toEqual(b.center);
    expect(interpolateBounds(a.bounds, b.bounds, 1).scale[1]).toBeCloseTo(6.5 / 6);
  });
  it("calcula el punto medio sin alterar los originales", () => {
    const original = structuredClone(a);
    expect(interpolateBounds(a.bounds, b.bounds, .5).position[1]).toBeCloseTo(4.4);
    expect(a).toEqual(original);
  });
  it("termina en las mallas exactas B y oculta las retiradas", () => {
    expect(morphState({ before: a, after: b }, 1)).toMatchObject({ sourceOpacity: 0, targetOpacity: 1, exactTarget: true });
    expect(morphState({ before: a, after: null }, 1).sourceOpacity).toBe(0);
    expect(morphState({ before: null, after: b }, 0).targetOpacity).toBe(0);
  });
  it("limita entradas y evita divisiones por cero", () => {
    expect([clampProgress(-1), clampProgress(2), clampProgress(NaN)]).toEqual([0, 1, 0]);
    const flat = { min: [0, 0, 0], max: [0, 0, 0] };
    expect(interpolateBounds(flat, b.bounds, 1).scale).toEqual([1, 1, 1]);
  });
  it("las etiquetas de cambio proceden del delta", () => {
    const steps = changeSteps({ changes: [{ path: "nozzles.N3.elevation", operation: "modified",
      before: { value: 3500, unit: "mm" }, after: { value: 3700, unit: "mm" }, affects_geometry: true }] });
    expect(steps[0]).toMatchObject({ elementId: "nozzle:N3", label: "+200 mm" });
    expect(changeSteps(undefined)).toEqual([]);
  });
});
