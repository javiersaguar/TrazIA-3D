import { describe, expect, it } from "vitest";
import { hasAssumption, parentElementId, productLabel, semanticId, shortLabel } from "./semantic";

it("un supuesto del faldón no pinta la virola como supuesta", () => {
  const psets = { TrazIA_Traceability: { FieldsJSON: JSON.stringify({ skirt_height: { state: "assumed" }, diameter: { state: "candidate" } }) } };
  expect(hasAssumption("skirt", psets)).toBe(true);
  expect(hasAssumption("shell", psets)).toBe(false);
  expect(hasAssumption("detail:skirt/base/ring", psets)).toBe(true);
  expect(hasAssumption("shell", { TrazIA_Traceability: { FieldsJSON: "bad" } })).toBe(false);
});

describe("identidad de proceso (contrato C2)", () => {
  const trace = (fields: Record<string, string>) => ({
    TrazIA_Traceability: { Dataset: "synthetic", ProcessProject: "SIM-MAR", Revision: "A", ...fields },
  });

  it("la raíz de un equipo es element:TAG", () => {
    expect(semanticId("V-110", "IfcTank", trace({ Component: "V-110", Role: "equipment" }))).toBe("element:V-110");
    // Sin Component manda el Tag del IFC y, si falta, el nombre.
    expect(semanticId("V-110", "IfcTank", trace({ Role: "equipment" }), "V-110")).toBe("element:V-110");
    expect(semanticId("ST-00", "IfcElementAssembly", trace({ Role: "structure" }))).toBe("element:ST-00");
  });

  it("una pieza es detail:element:TAG/clave y vuelve a su equipo", () => {
    const id = semanticId("V-110 · Virola", "IfcBuildingElementProxy",
      trace({ Component: "V-110/virola", ParentComponent: "V-110", Role: "component" }), "V-110/virola");
    expect(id).toBe("detail:element:V-110/virola");
    expect(parentElementId(id)).toBe("element:V-110");
    const nozzle = semanticId("GS-02 · Boquilla", "IfcPipeFitting",
      trace({ Component: "GS-02/boquilla-gs-02", ParentComponent: "GS-02", Role: "component" }));
    expect(nozzle).toBe("detail:element:GS-02/boquilla-gs-02");
    expect(parentElementId(nozzle)).toBe("element:GS-02");
  });

  it("rotula «tag · nombre» desde Description y Name", () => {
    const root = { semanticId: "element:P-150", name: "P-150", tag: "P-150", description: "Bomba de inyección",
      psets: trace({ Component: "P-150", Role: "equipment", Description: "Bomba de inyección" }) };
    expect(productLabel(root)).toBe("P-150 · Bomba de inyección");
    expect(shortLabel(root)).toBe("Bomba de inyección");
    const piece = { semanticId: "detail:element:P-150/motor-a", name: "P-150 · Motor A", tag: "P-150/motor-a",
      psets: trace({ Component: "P-150/motor-a", ParentComponent: "P-150", Role: "component", Description: "Motor A" }) };
    expect(productLabel(piece)).toBe("P-150 · Motor A");
    expect(shortLabel(piece)).toBe("Motor A");
    // Sin Description: la etiqueta sale del Name «TAG · Etiqueta».
    const bare = { ...piece, psets: trace({ Component: "P-150/motor-a", ParentComponent: "P-150" }) };
    expect(shortLabel(bare)).toBe("Motor A");
    // Fuera de proceso se conserva el rótulo de siempre.
    expect(productLabel({ semanticId: "shell", name: "V-101", psets: {} })).toBe("Virola");
  });
});
