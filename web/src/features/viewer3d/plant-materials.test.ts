import { describe, expect, it } from "vitest";
import { grainPixels } from "./grain-textures";
import { styleKey, surfaceFinish } from "./plant-materials";

describe("acabados por estilo IFC", () => {
  it("normaliza tildes y mayúsculas del nombre del estilo", () => {
    expect(styleKey(" Hormigón ")).toBe("hormigon");
    expect(surfaceFinish("Hormigón").kind).toBe("concrete");
    expect(surfaceFinish("ASFALTO").kind).toBe("asphalt");
  });

  it("cada familia responde a la luz de forma distinta", () => {
    const acero = surfaceFinish("Acero"), aislante = surfaceFinish("Aislante"), junta = surfaceFinish("Junta");
    expect(acero.clearcoat).toBeGreaterThan(0);
    expect(aislante.metalness).toBeGreaterThan(acero.metalness);
    expect(junta.metalness).toBe(0);
    expect(surfaceFinish("Hormigón").grain).toBeGreaterThan(0);
    expect(surfaceFinish("Motor").roughness).toBeLessThan(acero.roughness);
  });

  it("resuelve alias y, si no conoce el estilo, decide por el color", () => {
    expect(surfaceFinish("Barandilla de seguridad").kind).toBe("painted");
    expect(surfaceFinish("Acero inoxidable").kind).toBe("stainless");
    expect(surfaceFinish("Desconocido", [0.8, 0.2, 0.1]).kind).toBe("painted");
    expect(surfaceFinish(undefined, [0.55, 0.56, 0.58]).kind).toBe("steel");
  });
});

describe("textura de árido", () => {
  it("es determinista y con relieve suave", () => {
    const a = grainPixels(32), b = grainPixels(32);
    expect(a.roughness).toEqual(b.roughness);
    let tilt = 0;
    for (let i = 0; i < a.normal.length; i += 4) {
      expect(a.normal[i + 2]).toBe(255);
      tilt = Math.max(tilt, Math.abs(a.normal[i]! - 128), Math.abs(a.normal[i + 1]! - 128));
    }
    expect(tilt).toBeGreaterThan(0);
    expect(tilt).toBeLessThan(90);
  });
});
