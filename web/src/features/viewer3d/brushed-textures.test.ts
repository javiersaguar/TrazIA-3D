import { describe, expect, it } from "vitest";
import { brushedPixels } from "./brushed-textures";

describe("superficie de acero", () => {
  it("es repetible al cambiar de escena y conserva normales opacas", () => {
    const a = brushedPixels(32), b = brushedPixels(32);
    expect(a.normal).toEqual(b.normal);
    expect(a.roughness).toEqual(b.roughness);
    expect(a.normal.length).toBe(32 * 32 * 4);
    for (let i = 0; i < a.normal.length; i += 4) {
      expect(a.normal[i + 2]).toBeGreaterThan(250);
      expect(a.normal[i + 3]).toBe(255);
      expect(a.roughness[i + 3]).toBe(255);
    }
  });

  it("tiene cepillado direccional sin una textura de pigmento", () => {
    const { normal, roughness } = brushedPixels(32);
    expect(new Set(Array.from(normal).filter((_, i) => i % 4 === 1)).size).toBeGreaterThan(10);
    for (let i = 0; i < roughness.length; i += 4) {
      expect(roughness[i]).toBe(roughness[i + 1]);
      expect(roughness[i]).toBe(roughness[i + 2]);
    }
  });
});
