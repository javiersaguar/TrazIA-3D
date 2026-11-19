import { Box3, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import { elevationOf, focusMargin, ghostsFor, placedBox, unionBox, type Placed } from "./focus";
import { validPose } from "./saved-views";

const pieza = (semanticId: string, min: [number, number, number], max: [number, number, number]): Placed => ({
  semanticId,
  bounds: { min, max },
  center: [(min[0] + max[0]) / 2, (min[1] + max[1]) / 2, (min[2] + max[2]) / 2],
});

describe("encuadre por selección", () => {
  it("da más holgura a lo pequeño que a lo grande", () => {
    const margins = [1, 4, 12, 40].map(focusMargin);
    for (let i = 1; i < margins.length; i++) expect(margins[i]).toBeLessThan(margins[i - 1]!);
    expect(focusMargin(2)).toBeGreaterThan(2.1);
    expect(focusMargin(40)).toBeGreaterThan(1.35);
    expect(focusMargin(40)).toBeLessThan(1.5);
  });

  it("une las cajas de las piezas tal y como se dibujan", () => {
    const bomba = pieza("element:P-150", [0, 0, 0], [2, 1, 1]);
    const motor = pieza("detail:element:P-150/motor", [2, 0, 0], [3, 1, 1]);
    const explosion = new Map([["detail:element:P-150/motor", [3.5, 0.5, 0.5] as [number, number, number]]]);
    expect(placedBox(motor, [3.5, 0.5, 0.5]).min.x).toBeCloseTo(3);
    const caja = unionBox([bomba, motor], new Set([bomba.semanticId, motor.semanticId]), explosion);
    expect(caja.min.toArray()).toEqual([0, 0, 0]);
    expect(caja.max.toArray()).toEqual([4, 1, 1]);
    expect(unionBox([bomba], new Set(["element:V-110"])).isEmpty()).toBe(true);
  });

  it("atenúa lo que tapa, pero no lo que sostiene o envuelve el objetivo", () => {
    const objetivo = new Box3(new Vector3(0, 1, 0), new Vector3(2, 2, 1));
    const cajas = new Map([
      ["element:V-110", new Box3(new Vector3(4, 0, 0), new Vector3(6, 4, 2))],
      ["element:ST-00", new Box3(new Vector3(-10, 0, -10), new Vector3(10, 3, 10))],
      ["detail:element:L-01/tramo-1", new Box3(new Vector3(3, 1, 0), new Vector3(3.2, 1.2, 4))],
    ]);
    const bloqueos = new Map([
      ["detail:element:L-01/tramo-1", 0.02],
      ["element:ST-00", 0.4],
      ["element:V-110", 0.12],
      ["element:X-1", 0.3],
    ]);
    expect(ghostsFor(bloqueos, objetivo, cajas)).toEqual(["element:X-1", "element:V-110"]);
    expect(ghostsFor(bloqueos, objetivo, cajas, 0.01)).toContain("detail:element:L-01/tramo-1");
  });

  it("mide la elevación de la cámara sobre el objetivo", () => {
    expect(elevationOf([10, 10, 0], [0, 0, 0])).toBeCloseTo(45);
    expect(elevationOf([0, 0, 5], [0, 0, 0])).toBeCloseTo(0);
  });

  it("acepta vistas guardadas en perspectiva con zoom equivalente pequeño", () => {
    const pose = { eye: [80, 40, 80], target: [0, 0, 0], zoom: 0.4 };
    expect(validPose({ ...pose, projection: "perspective" })).toBe(true);
    expect(validPose(pose)).toBe(false);
  });
});
