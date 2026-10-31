import { expect, it } from "vitest";
import { ifcTraces } from "./ifc-trace";
it("lee source.confidence del contrato IFC y rechaza un JSON mal formado", () => {
  const fields = { diameter: { value: 2000, unit: "mm", state: "candidate", source: { confidence: .75, document_id: "GA", page: 1 } } };
  expect(ifcTraces({ TrazIA_Traceability: { FieldsJSON: JSON.stringify(fields) } }).diameter?.source.confidence).toBe(.75);
  expect(ifcTraces({ TrazIA_Traceability: { FieldsJSON: "{" } })).toEqual({});
});
