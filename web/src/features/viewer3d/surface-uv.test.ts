import { BufferAttribute, BufferGeometry } from "three";
import { expect, it } from "vitest";
import { addSurfaceUV } from "./surface-uv";

it("añade textura sin sustituir ninguna posición ni triángulo IFC", () => {
  const geometry = new BufferGeometry();
  const positions = new Float32Array([0, 0, 0, 2, 0, 0, 0, 6, 0]);
  geometry.setAttribute("position", new BufferAttribute(positions, 3));
  geometry.setIndex([0, 1, 2]);
  const index = geometry.index;
  addSurfaceUV(geometry);
  expect(geometry.getAttribute("position").array).toBe(positions);
  expect(geometry.index).toBe(index);
  expect([...geometry.getAttribute("uv").array]).toEqual([0, 0, 1, 0, 0, 1]);
  const uv = geometry.getAttribute("uv");
  addSurfaceUV(geometry);
  expect(geometry.getAttribute("uv")).toBe(uv);
  geometry.dispose();
});
