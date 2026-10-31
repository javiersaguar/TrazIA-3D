import { expect, it } from "vitest";
import { hasAssumption } from "./semantic";
it("un supuesto del faldón no pinta la virola como supuesta", () => {
  const psets = { TrazIA_Traceability: { FieldsJSON: JSON.stringify({ skirt_height: { state: "assumed" }, diameter: { state: "candidate" } }) } };
  expect(hasAssumption("skirt", psets)).toBe(true);
  expect(hasAssumption("shell", psets)).toBe(false);
  expect(hasAssumption("detail:skirt/base/ring", psets)).toBe(true);
  expect(hasAssumption("shell", { TrazIA_Traceability: { FieldsJSON: "bad" } })).toBe(false);
});
