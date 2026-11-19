import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { IfcAPI } from "web-ifc";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { readIfcModel } from "./ifc-parse";
import type { IfcModel } from "./ifc-protocol";

/*
  Lee IFC sintéticos con el WASM de web-ifc en Node, igual que el worker del visor:
  - tests/fixtures/ifc/ensamblaje_proceso.ifc: equipo raíz sin geometría con tres piezas agregadas,
    una línea IfcElementAssembly con un tramo y un equipo sin piezas (contrato C1);
  - un IFC de proceso publicado, sin descomposición, que debe leerse como antes.
*/
const here = dirname(fileURLToPath(import.meta.url));
const web = join(here, "..", "..");
const api = new IfcAPI();

function read(path: string): IfcModel {
  const bytes = readFileSync(path);
  const modelId = api.OpenModel(new Uint8Array(bytes), { COORDINATE_TO_ORIGIN: false, CIRCLE_SEGMENTS: 24 });
  try {
    return readIfcModel(api, modelId, { url: path, bytes: bytes.byteLength, start: performance.now() });
  } finally {
    api.CloseModel(modelId);
  }
}

beforeAll(async () => {
  api.SetWasmPath(join(web, "node_modules", "web-ifc") + "/", true);
  await api.Init(undefined, true);
});
afterAll(() => api.Dispose());

describe("lectura IFC con ensamblajes", () => {
  it("cuelga cada pieza de su equipo o línea y calcula los límites del ensamblaje", () => {
    const model = read(join(web, "..", "tests", "fixtures", "ifc", "ensamblaje_proceso.ifc"));
    const ids = model.products.map(product => product.semanticId).sort();
    expect(ids).toEqual([
      "detail:element:L-01/tramo-1",
      "detail:element:P-900/bancada",
      "detail:element:P-900/carcasa",
      "detail:element:P-900/motor-a",
      "element:V-901",
    ]);
    const assemblies = model.assemblies ?? [];
    expect(assemblies.map(assembly => assembly.semanticId).sort()).toEqual(["element:L-01", "element:P-900"]);
    const pump = assemblies.find(assembly => assembly.semanticId === "element:P-900")!;
    expect(pump.ifcType).toBe("IfcPump");
    expect(pump.tag).toBe("P-900");
    expect(pump.description).toBe("Bomba de prueba");
    expect(pump.psets.TrazIA_Traceability?.Role).toBe("equipment");
    expect(pump.children).toHaveLength(3);
    const pieces = model.products.filter(product => product.parentGlobalId === pump.globalId);
    expect(pieces.map(piece => piece.tag).sort()).toEqual(["P-900/bancada", "P-900/carcasa", "P-900/motor-a"]);
    for (const piece of pieces) {
      for (let axis = 0; axis < 3; axis++) {
        expect(pump.bounds.min[axis]).toBeLessThanOrEqual(piece.bounds.min[axis]! + 1e-6);
        expect(pump.bounds.max[axis]).toBeGreaterThanOrEqual(piece.bounds.max[axis]! - 1e-6);
      }
    }
    // IFC Z arriba → visor Y arriba: la bancada (0–0,6 m) y el motor (hasta 1,35 m).
    expect(pump.bounds.min[1]).toBeCloseTo(0, 4);
    expect(pump.bounds.max[1]).toBeCloseTo(1.4, 4);
    expect(pump.center[1]).toBeCloseTo(0.7, 4);
    const line = assemblies.find(assembly => assembly.semanticId === "element:L-01")!;
    expect(line.ifcType).toBe("IfcElementAssembly");
    expect(line.children).toEqual([model.products.find(p => p.tag === "L-01/tramo-1")!.globalId]);
    const vessel = model.products.find(product => product.semanticId === "element:V-901")!;
    expect(vessel.parentGlobalId).toBeUndefined();
  });

  it("lee el nombre del estilo de cada geometría", () => {
    const model = read(join(web, "..", "tests", "fixtures", "ifc", "ensamblaje_proceso.ifc"));
    const motor = model.products.find(product => product.tag === "P-900/motor-a")!;
    expect(motor.name).toBe("P-900 · Motor A");
    expect(motor.parts.map(part => part.style).sort()).toEqual(["Junta", "Motor"]);
    const base = model.products.find(product => product.tag === "P-900/bancada")!;
    expect(base.parts[0]!.style).toBe("Hormigón");
    expect(base.psets.TrazIA_Dimensiones?.LongitudM).toBeCloseTo(2.6, 6);
  });

  it("el IFC de planta publica sus equipos, piezas y acabados", () => {
    const model = read(join(web, "public", "demo", "proceso", "plataforma-marina", "SIM-MAR-A.ifc"));
    expect(model.assemblies).toHaveLength(14);
    expect(model.products.length).toBeGreaterThan(100);
    const pump = model.assemblies!.find(product => product.name === "P-150")!;
    expect(pump.semanticId).toBe("element:P-150");
    expect(pump.tag).toBe("P-150");
    expect(pump.parentGlobalId).toBeUndefined();
    expect(pump.psets.TrazIA_Traceability?.Component).toBe("P-150");
    expect(model.products.some(product => product.parentGlobalId === pump.globalId)).toBe(true);
    const styles = new Set(model.products.flatMap(product => product.parts.map(part => part.style)));
    expect(styles.has("Acero")).toBe(true);
    expect(styles.has(undefined)).toBe(false);
  });

  it("conserva la lectura de un equipo sin árbol de planta", () => {
    const model = read(join(web, "public", "demo", "ifc", "rev_a.ifc"));
    expect(model.products.length).toBeGreaterThan(0);
    expect(model.products.some(product => product.semanticId === "shell")).toBe(true);
  });
});
