import { expect, it } from "vitest";
import { Vector3 } from "three";
import { buildTank } from "./equipment-geometry";
import { sampleSurface, scatterSurface } from "./surface-sampling";

it("muestrea la superficie ilustrativa de forma reproducible y dentro de sus límites", () => {
  const model = buildTank();
  try {
    const a = sampleSurface(model, 300), b = sampleSurface(model, 300);
    expect(a).toEqual(b);
    for (let i = 0; i < a.length; i += 3) expect(model.bounds.containsPoint(new Vector3(a[i], a[i + 1], a[i + 2]))).toBe(true);
    const cloud = scatterSurface(a);
    expect(cloud).toEqual(scatterSurface(a));
    expect(cloud.some((n, i) => Math.abs(n - a[i]!) > 2)).toBe(true);
  } finally { model.dispose(); }
});
