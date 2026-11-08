import { describe, expect, it } from "vitest";
import type { Preview, Target } from "./api";
import { clarifiedText, draftSignature, draftsFromOperations, elementStates, groupForSelection, toOperations, unitsFor } from "./form";

const target = (over: Partial<Target>): Target => ({
  target: "height", path: "height", label: "Longitud entre tangentes", group: "equipo", unit: "mm",
  magnitude: "length", rule: "", derived: false, datums: [], affects: [], text: false,
  current: { value: 6500, unit: "mm", state: "candidate" }, ...over,
});

describe("formulario de cambios de diseño", () => {
  it("relaciona la selección 3D con su grupo", () => {
    expect(groupForSelection("nozzle:N3")).toBe("boquilla:N3");
    expect(groupForSelection("detail:nozzle:N2/flange")).toBe("boquilla:N2");
    expect(groupForSelection("shell")).toBe("equipo");
    expect(groupForSelection(null)).toBe("equipo");
  });

  it("solo envía los campos escritos y conserva unidad y referencia explícitas", () => {
    const targets = [
      target({}),
      target({ target: "nozzles.N3.elevation", path: "nozzles.N3.elevation", group: "boquilla:N3", datums: ["suelo", "tangente_inferior"] }),
      target({ target: "attributes.material", path: "attributes.material", text: true, magnitude: null, unit: "1" }),
    ];
    const operations = toOperations({
      height: { value: " 7000 ", unit: "mm" },
      "nozzles.N3.elevation": { value: "2,85", unit: "m", datum: "tangente_inferior" },
      "attributes.material": { value: "SA-516 Gr.70", unit: "1" },
      unknown: { value: "1", unit: "mm" },
      diameter: { value: "", unit: "mm" },
    }, targets);
    expect(operations).toEqual([
      { target: "height", value: "7000", unit: "mm" },
      { target: "nozzles.N3.elevation", value: "2,85", unit: "m", datum: "tangente_inferior" },
      { target: "attributes.material", value: "SA-516 Gr.70" },
    ]);
  });

  it("cambia la firma cuando cambia una entrada o el motivo", () => {
    const base = draftSignature([{ target: "height", value: "7000", unit: "mm" }], "Capacidad");
    expect(draftSignature([{ target: "height", value: "7000", unit: "mm" }], " Capacidad ")).toBe(base);
    expect(draftSignature([{ target: "height", value: "7000", unit: "m" }], "Capacidad")).not.toBe(base);
    expect(draftSignature([{ target: "height", value: "7000", unit: "mm" }], "Otro")).not.toBe(base);
  });

  it("ofrece unidades compatibles y ninguna para texto", () => {
    expect(unitsFor(target({}))).toContain("m");
    expect(unitsFor(target({ unit: "bara", magnitude: "pressure" }))).toEqual(["bara", "psia"]);
    expect(unitsFor(target({ text: true, magnitude: null }))).toEqual([]);
  });

  it("marca en el visor las piezas regeneradas y los conflictos", () => {
    const preview = { elements: [
      { semantic_id: "shell", geometry_changed: true, conflict: false, operations: ["op-1"] },
      { semantic_id: "nozzle:N1", geometry_changed: false, conflict: false, operations: [] },
    ] } as unknown as Preview;
    expect(elementStates(preview, [{ severity: "error", code: "nozzle_conflict", message: "", path: null, operation_id: null, nozzle_id: "N4" }]))
      .toEqual({ shell: "changed", "nozzle:N4": "conflict" });
  });
});


describe("chat que prepara cambios", () => {
  it("rellena el formulario con lo que propone el chat", () => {
    const targets = [target({}), target({ target: "nozzles.N3.elevation", path: "nozzles.N3.elevation", datums: ["suelo", "tangente_inferior"] })];
    expect(draftsFromOperations([
      { target: "height", value: "7000", unit: "mm" },
      { target: "nozzles.N3.elevation", value: "4,2", unit: "m" },
      { target: "approval", value: "ok" },
    ], targets)).toEqual({
      height: { value: "7000", unit: "mm", datum: undefined },
      "nozzles.N3.elevation": { value: "4,2", unit: "m", datum: "suelo" },
    });
  });

  it("resuelve una aclaración añadiendo la magnitud elegida", () => {
    expect(clarifiedText("Aumenta la altura 500 mm", "total_height")).toBe("Aumenta la altura 500 mm (altura total)");
    expect(clarifiedText("cambia N3 a 30", "nozzles.N3.azimuth")).toBe("cambia N3 a 30 (azimut)");
  });
});
