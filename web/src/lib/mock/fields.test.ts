import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { formatInterval } from "../format";
import { flattenRevision } from "./fields";

const revision = JSON.parse(readFileSync(new URL("../../../../examples/vessel_rev_a.json", import.meta.url), "utf8"));

describe("intervalo y abstención en la revisión (E.7)", () => {
  it("formatea el intervalo conforme simétrico y el asimétrico", () => {
    expect(formatInterval(2000, { low: 1997, high: 2003, level: 0.9 }, "mm")).toBe("± 3 mm · 90 %");
    expect(formatInterval(90, { low: 89.5, high: 90.5, level: 0.9 }, "deg")).toBe("± 0,5° · 90 %");
    expect(formatInterval(2000, { low: 1990, high: 2030, level: 0.9 }, "mm")).toBe("1.990–2.030 mm · 90 %");
  });

  it("lleva intervalo, abstención y explicación del contrato al campo, y lo abstenido va primero", () => {
    const copy = structuredClone(revision);
    copy.equipment.height = {
      ...copy.equipment.height,
      state: "abstained",
      explanation: "Abstención: confírmelo en la revisión.",
      source: { ...copy.equipment.height.source, confidence: 0.99, confidence_raw: 0.75 },
    };
    copy.equipment.diameter = { ...copy.equipment.diameter, interval: { low: 1997, high: 2003, level: 0.9, method: "conformal" } };
    const fields = flattenRevision(copy);
    const height = fields.find((f) => f.path === "height")!;
    expect(fields[0]?.path).toBe("height");
    expect(height.abstained && height.calibrated && height.status === "candidate").toBe(true);
    expect(height.explanation).toContain("confírmelo");
    expect(fields.find((f) => f.path === "diameter")!.interval).toMatchObject({ low: 1997, high: 2003 });
  });
});
