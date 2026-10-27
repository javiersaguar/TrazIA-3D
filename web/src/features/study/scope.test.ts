import { describe, expect, it } from "vitest";
import report from "../../../../docs/evidencias/fase1/estudio.json";
import type { StudyReport } from "@/lib/mock/estudio-types";
import { studyScope } from "./scope";

describe("alcance del estudio", () => {
  it("cuenta solo equipos y estilos medidos en el informe", () => {
    const scope = studyScope(report as unknown as StudyReport);
    expect(scope.datasets).toEqual(["S-dev"]);
    expect(scope.equipment).toBe(24);
    expect(scope.vendors).toBe(6);
    expect(scope.degradations).toBe(3);
  });
  it("no presupone ocho estilos ni tres degradaciones en un estudio parcial", () => {
    const partial = structuredClone(report) as unknown as StudyReport;
    partial.sets = undefined;
    for (const variant of partial.variants) {
      variant.by_style = { atlas: variant.metrics };
      variant.by_degradation = { vectorial: variant.metrics };
    }
    expect(studyScope(partial)).toMatchObject({ equipment: 0, vendors: 1, degradations: 1 });
  });
});
