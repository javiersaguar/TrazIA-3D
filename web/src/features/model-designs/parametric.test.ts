import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { applyEdits, designByTag, DESIGNS, designMeshes, envelope, isPristine, type DesignSpec } from "./parametric";

/** Listas de puntos del IFC publicado, en el orden en que aparecen las piezas. */
function publishedPoints(ifc: string): number[][][] {
  const text = readFileSync(join(process.cwd(), "public", ifc.replace(/^\//, "")), "utf8");
  return [...text.matchAll(/IFCCARTESIANPOINTLIST3D\(\((.*?)\)\);/g)].map((match) =>
    [...match[1]!.matchAll(/\(([^()]+)\)/g)].map((point) => point[1]!.split(",").map(Number)),
  );
}

const industrial = DESIGNS.filter((design) => design.ifc);

describe("diseños paramétricos", () => {
  it("lista todos los diseños del catálogo con tags únicos", () => {
    expect(DESIGNS.length).toBe(72);
    expect(new Set(DESIGNS.map((design) => design.tag)).size).toBe(DESIGNS.length);
    expect(industrial.length).toBe(56);
  });

  it("cada pieza cae dentro de la envolvente y tiene volumen", () => {
    for (const design of DESIGNS) {
      expect(design.parts.length, design.tag).toBeGreaterThan(0);
      for (const part of design.parts) {
        for (let i = 0; i < 3; i++) {
          expect(part.low[i]!, `${design.tag}/${part.name}`).toBeGreaterThanOrEqual(0);
          expect(part.high[i]!, `${design.tag}/${part.name}`).toBeLessThanOrEqual(100);
          expect(part.high[i]!, `${design.tag}/${part.name}`).toBeGreaterThan(part.low[i]!);
        }
      }
    }
  });

  it.each(industrial.map((design) => [design.tag, design] as const))(
    "sin cambios, %s genera los mismos vértices que su IFC publicado",
    (_tag, design: DesignSpec) => {
      const published = publishedPoints(design.ifc!);
      const meshes = designMeshes(design);
      expect(published.length).toBe(meshes.length);
      meshes.forEach((mesh, index) => {
        const points = published[index]!;
        expect(points.length, mesh.name).toBe(mesh.vertices.length);
        mesh.vertices.forEach((vertex, k) => {
          for (let i = 0; i < 3; i++) expect(Math.abs(vertex[i]! - points[k]![i]!), mesh.name).toBeLessThan(1e-3);
        });
      });
    },
  );
});

describe("cambios en directo", () => {
  const design = designByTag("BC-AC101")!;

  it("sin cambios devuelve el mismo diseño", () => {
    expect(isPristine(undefined)).toBe(true);
    expect(isPristine({ size: { height: undefined }, parts: { Colector: { scale: 1 } } })).toBe(true);
    expect(applyEdits(design, { size: { height: undefined } })).toBe(design);
  });

  it("cambiar el alto escala la envolvente del IFC", () => {
    const [, height] = design.size;
    const edited = applyEdits(design, { size: { height: height * 2 } });
    expect(isPristine({ size: { height: height * 2 } })).toBe(false);
    const before = envelope(designMeshes(design));
    const after = envelope(designMeshes(edited));
    expect(after.height).toBeCloseTo(before.height * 2, 3);
    expect(after.width).toBeCloseTo(before.width, 3);
    expect(after.depth).toBeCloseTo(before.depth, 3);
  });

  it("ocultar una pieza la quita del IFC", () => {
    const name = design.parts[0]!.name;
    const edited = applyEdits(design, { parts: { [name]: { hidden: true } } });
    expect(edited.parts.map((part) => part.name)).not.toContain(name);
    expect(edited.parts.length).toBe(design.parts.length - 1);
  });

  it("escalar una pieza la agranda sobre su centro sin salir de la envolvente", () => {
    for (const part of design.parts) {
      const edited = applyEdits(design, { parts: { [part.name]: { scale: 1.5 } } });
      const scaled = edited.parts.find((p) => p.name === part.name)!;
      for (let i = 0; i < 3; i++) {
        expect(scaled.low[i]!).toBeGreaterThanOrEqual(0);
        expect(scaled.high[i]!).toBeLessThanOrEqual(100);
        expect(scaled.high[i]! - scaled.low[i]!).toBeGreaterThanOrEqual(part.high[i]! - part.low[i]! - 1e-9);
      }
    }
  });
});
