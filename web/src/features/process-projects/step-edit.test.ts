import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  applyEquipmentEdits, applyNominalEdits, equipmentEnvelope, linesToReview, nominalAxes, nominalOf, real, splitArgs, StepModel,
} from "./step-edit";

const ifc = readFileSync(resolve(__dirname, "../../../public/demo/proceso/plataforma-marina/SIM-MAR-A.ifc"), "utf8");
const size = (e: { min: number[]; max: number[] }) => e.max.map((v, i) => v - e.min[i]!);

describe("cambios de prueba sobre el IFC de planta", () => {
  it("separa argumentos con listas y cadenas con comas", () => {
    expect(splitArgs("'a,b',(1,2),#3,$")).toEqual(["'a,b'", "(1,2)", "#3", "$"]);
    expect(splitArgs("'it''s',.T.")).toEqual(["'it''s'", ".T."]);
    expect(real(2)).toBe("2.");
    expect(real(-0.00001)).toBe("0.");
  });

  it("lee la envolvente real de un equipo desde sus piezas", () => {
    const envelope = equipmentEnvelope(new StepModel(ifc), "V-110")!;
    const [x, , z] = size(envelope);
    // Virola de 9 m más orejetas, pernos y boca de hombre que sobresalen.
    expect(x).toBeGreaterThan(9);
    expect(x).toBeLessThan(10.5);
    expect(envelope.min[2]).toBeGreaterThanOrEqual(16 - 1e-6);
    expect(z).toBeGreaterThan(4);
  });

  it("alarga el separador sin despegarlo de la cubierta y deja constancia en el IFC", () => {
    const { text, changed } = applyEquipmentEdits(ifc, { "V-110": { length: 11 } });
    const model = new StepModel(text);
    const after = equipmentEnvelope(model, "V-110")!;
    const before = changed[0]!.before;
    // Las piezas repetidas (pernos, orejetas) se desplazan sin estirarse: unos centímetros menos.
    expect(Math.abs(size(after)[0]! - 11)).toBeLessThan(0.1);
    expect(size(after)[1]).toBeCloseTo(size(before)[1]!, 3);
    expect(after.min[2]).toBeCloseTo(before.min[2], 3);
    // Centro de la huella en su sitio.
    expect(Math.abs((after.min[0] + after.max[0]) / 2 - (before.min[0] + before.max[0]) / 2)).toBeLessThan(0.05);
    expect(text).toContain("'TrazIA_Edicion'");
    expect(text).toContain("EnvolventeDespuesM");
    // Los demás equipos no se tocan.
    expect(equipmentEnvelope(model, "P-150")).toEqual(equipmentEnvelope(new StepModel(ifc), "P-150"));
    // El origen común del modelo sigue en 0,0,0.
    expect(text).toContain("#1=IFCCARTESIANPOINT((0.0,0.0,0.0));");
  });

  it("desplaza un equipo y sus puertos, y marca sus líneas para revisar", () => {
    const { text } = applyEquipmentEdits(ifc, { "P-150": { dx: 2, dy: -1 } });
    const before = equipmentEnvelope(new StepModel(ifc), "P-150")!;
    const after = equipmentEnvelope(new StepModel(text), "P-150")!;
    expect(after.min[0] - before.min[0]).toBeCloseTo(2, 3);
    expect(after.min[1] - before.min[1]).toBeCloseTo(-1, 3);
    const lines = [{ tag: "OL-05", start: "V-110", end: "P-150" }, { tag: "GS-02", start: "V-110", end: "V-120" }];
    expect(linesToReview(lines, ["P-150"])).toEqual(["OL-05"]);
  });

  it("lee y cambia cotas nominales de la ficha sin API", () => {
    const model = new StepModel(ifc);
    expect(nominalOf(model, "V-110").length?.value).toBe(9);
    const diameter = nominalOf(model, "V-110").width!.value;
    expect(nominalAxes("horizontal", "width")).toEqual([1, 2]);
    expect(nominalAxes("tank", "width")).toEqual([0, 1]);
    const { text, changed } = applyNominalEdits(ifc, [
      { tag: "V-110", field: "length", value: 9.9 },
      { tag: "V-110", field: "width", value: diameter * 1.1 },
    ], { "V-110": "horizontal" });
    const after = new StepModel(text);
    expect(nominalOf(after, "V-110").length?.value).toBeCloseTo(9.9, 3);
    expect(nominalOf(after, "V-110").width?.value).toBeCloseTo(diameter * 1.1, 3);
    const [x0, y0, z0] = size(changed[0]!.before);
    const [x1, y1, z1] = size(equipmentEnvelope(after, "V-110")!);
    expect(x1! / x0!).toBeGreaterThan(1.07);
    expect(y1! / y0!).toBeCloseTo(1.1, 1);
    expect(z1! / z0!).toBeCloseTo(1.1, 1);
  });

  it("es rápido para una planta de 2 MB", () => {
    const start = performance.now();
    applyEquipmentEdits(ifc, { "V-110": { length: 10, height: 6 } });
    expect(performance.now() - start).toBeLessThan(3000);
  });
});
