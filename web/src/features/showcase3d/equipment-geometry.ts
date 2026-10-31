import {
  Box3, BoxGeometry, BufferGeometry, ConeGeometry, CylinderGeometry, ExtrudeGeometry,
  LatheGeometry, Matrix4, Quaternion, Shape, TorusGeometry, Vector2, Vector3,
} from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { Brush, Evaluator, SUBTRACTION } from "three-bvh-csg";

export type EquipmentKind = "vertical" | "horizontal" | "column" | "exchanger" | "tank";
export type Finish = "steel" | "paint" | "machined" | "bolts";
type Point = [number, number, number];
export type EquipmentGeometry = {
  kind: EquipmentKind;
  source: "illustrative";
  batches: { finish: Finish; geometry: BufferGeometry }[];
  boltGeometry: BufferGeometry;
  bolts: Matrix4[];
  bounds: Box3;
  anchors: Partial<Record<"flange" | "skirt" | "lug", Vector3>>;
  dispose(): void;
};
const up = new Vector3(0, 1, 0);
const q = (axis: Point) => new Quaternion().setFromUnitVectors(up, new Vector3(...axis).normalize());
const transform = (at: Point, axis: Point = [0, 1, 0], scale = 1) => new Matrix4().compose(
  new Vector3(...at), q(axis), new Vector3(scale, scale, scale),
);

function subtract(base: BufferGeometry, cutter: BufferGeometry) {
  const evaluator = new Evaluator();
  evaluator.useGroups = false;
  evaluator.attributes = ["position", "normal", "uv"];
  const a = new Brush(base), b = new Brush(cutter);
  a.updateMatrixWorld(); b.updateMatrixWorld();
  const result = evaluator.evaluate(a, b, SUBTRACTION).geometry;
  a.disposeCacheData(); b.disposeCacheData();
  base.dispose(); cutter.dispose();
  return result;
}

function annulus(outer: number, inner: number, thickness: number, segments = 32) {
  const bevel = Math.min(thickness * .12, .007);
  return new LatheGeometry([
    new Vector2(inner, -thickness / 2), new Vector2(outer - bevel, -thickness / 2),
    new Vector2(outer, -thickness / 2 + bevel), new Vector2(outer, thickness / 2 - bevel),
    new Vector2(outer - bevel, thickness / 2), new Vector2(inner, thickness / 2),
    new Vector2(inner, -thickness / 2),
  ], segments);
}

function head(radius: number, top: boolean) {
  const profile = Array.from({ length: 17 }, (_, i) => {
    const angle = (top ? 16 - i : i) / 16 * Math.PI / 2;
    return new Vector2(radius * Math.sin(angle), (top ? 1 : -1) * radius / 2 * Math.cos(angle));
  });
  return new LatheGeometry(profile, 48);
}

class Builder {
  parts: Record<Finish, BufferGeometry[]> = { steel: [], paint: [], machined: [], bolts: [] };
  bolts: Matrix4[] = [];
  anchors: EquipmentGeometry["anchors"] = {};

  add(geometry: BufferGeometry, finish: Finish = "steel", at: Point = [0, 0, 0], axis: Point = [0, 1, 0]) {
    geometry.applyMatrix4(transform(at, axis));
    this.parts[finish].push(geometry);
  }
  bolt(at: Point, axis: Point = [0, 1, 0], scale = 1) { this.bolts.push(transform(at, axis, scale)); }
  rod(from: Point, to: Point, radius = .025, finish: Finish = "steel") {
    const a = new Vector3(...from), b = new Vector3(...to), direction = b.clone().sub(a);
    this.add(new CylinderGeometry(radius, radius, direction.length(), 12), finish,
      a.add(b).multiplyScalar(.5).toArray() as Point, direction.toArray() as Point);
  }
  ring(radius: number, y: number, at: Point = [0, 0, 0], axis: Point = [0, 1, 0]) {
    const geometry = new TorusGeometry(radius, .012, 6, 48).rotateX(Math.PI / 2).translate(0, y, 0);
    this.add(geometry, "bolts", at, axis);
  }
  nozzle(at: Point, axis: Point, radius = .13, blind = false) {
    const rotation = transform(at, axis), length = radius > .2 ? .3 : .34;
    const flange = radius * 1.85;
    const neck = annulus(radius, radius * .78, length).translate(0, length / 2, 0);
    this.parts.steel.push(neck.applyMatrix4(rotation));
    const face = (blind ? new CylinderGeometry(flange, flange, .075, 64) : annulus(flange, radius * .78, .075)).translate(0, length + .035, 0);
    this.parts.machined.push(face.applyMatrix4(rotation));
    const weld = new TorusGeometry(radius * 1.05, .018, 6, 32).rotateX(Math.PI / 2).translate(0, .025, 0);
    this.parts.bolts.push(weld.applyMatrix4(rotation));
    const count = radius > .2 ? 16 : 8;
    for (let i = 0; i < count; i++) {
      const angle = i / count * Math.PI * 2;
      this.bolts.push(rotation.clone().multiply(transform(
        [Math.cos(angle) * flange * .8, length + .07, Math.sin(angle) * flange * .8], [0, 1, 0], radius > .2 ? 1.1 : .8,
      )));
    }
  }
  shell(radius: number, length: number, at: Point, axis: Point = [0, 1, 0], cutaway = false) {
    const rotation = transform(at, axis);
    const shell = new CylinderGeometry(radius, radius, length, 48, 1, true, cutaway ? .75 : 0, cutaway ? Math.PI * 2 - 1.5 : Math.PI * 2);
    this.parts.steel.push(shell.applyMatrix4(rotation));
    for (const side of [-1, 1]) {
      if (!cutaway) this.parts.steel.push(head(radius, side > 0).translate(0, side * length / 2, 0).applyMatrix4(rotation));
      this.ring(radius + .005, side * length / 2, at, axis);
    }
    this.ring(radius + .005, 0, at, axis);
  }
  ladder(y: number, height: number, z: number, x = 0) {
    for (const side of [-1, 1]) this.rod([x + side * .22, y, z], [x + side * .22, y + height, z], .025);
    for (let h = .2; h < height; h += .3) this.rod([x - .22, y + h, z], [x + .22, y + h, z], .018, "bolts");
  }
  finish(kind: EquipmentKind): EquipmentGeometry {
    const batches = Object.entries(this.parts).flatMap(([finish, parts]) => {
      if (!parts.length) return [];
      const nonIndexed = parts.map(g => g.index ? g.toNonIndexed() : g);
      const geometry = mergeGeometries(nonIndexed);
      for (const item of new Set([...parts, ...nonIndexed])) item.dispose();
      if (!geometry) throw new Error("No se pudo unir el equipo ilustrativo");
      geometry.computeBoundingBox(); geometry.computeBoundingSphere();
      return [{ finish: finish as Finish, geometry }];
    });
    const shaft = new CylinderGeometry(.023, .023, .14, 8);
    const washer = annulus(.055, .024, .012, 16).translate(0, .05, 0);
    const hex = new CylinderGeometry(.043, .043, .04, 6).translate(0, .075, 0);
    const boltGeometry = mergeGeometries([shaft.toNonIndexed(), washer.toNonIndexed(), hex.toNonIndexed()])!;
    shaft.dispose(); washer.dispose(); hex.dispose();
    const bounds = new Box3();
    for (const batch of batches) bounds.union(batch.geometry.boundingBox!);
    return { kind, source: "illustrative", batches, boltGeometry, bolts: this.bolts, bounds, anchors: this.anchors,
      dispose() { for (const batch of batches) batch.geometry.dispose(); boltGeometry.dispose(); } };
  }
}

export function buildVerticalVessel(spec: { radius?: number; height?: number; platform?: boolean } = {}): EquipmentGeometry {
  const radius = spec.radius ?? 1.05, height = spec.height ?? 4.8;
  if (!(radius > 0 && height > radius)) throw new Error("Dimensiones ilustrativas no válidas");
  const b = new Builder(), bottom = 1.55, top = bottom + height;
  b.shell(radius, height, [0, bottom + height / 2, 0]);
  let skirt = subtract(new CylinderGeometry(radius * .98, radius * .98, 1.5, 48),
    new CylinderGeometry(radius * .98 - .05, radius * .98 - .05, 1.6, 48));
  for (const angle of [0, Math.PI / 2]) {
    const cut = new BoxGeometry(.42, .65, radius * 3).translate(0, -.32, 0).rotateY(angle);
    skirt = subtract(skirt, cut);
  }
  b.add(skirt, "steel", [0, .8, 0]);
  b.add(annulus(radius * 1.2, radius * .93, .09), "machined", [0, .09, 0]);
  for (let i = 0; i < 12; i++) {
    const angle = i / 12 * Math.PI * 2, r = radius * 1.1;
    b.bolt([Math.cos(angle) * r, .1, Math.sin(angle) * r], [0, 1, 0], 1.2);
  }
  for (let i = 0; i < 8; i++) {
    const angle = (i + .5) / 8 * Math.PI * 2;
    b.add(new BoxGeometry(.05, .5, .22).translate(0, 0, radius).rotateY(angle), "steel", [0, .35, 0]);
  }
  b.nozzle([0, top - .9, radius], [0, 0, 1]);
  b.nozzle([radius, bottom + 1.1, 0], [1, 0, 0], .16);
  b.nozzle([0, top + radius / 2, 0], [0, 1, 0], .14);
  b.nozzle([0, bottom + 1.05, radius], [0, 0, 1], .31, true);
  b.rod([-.62, bottom + .7, radius + .45], [-.62, bottom + 1.8, radius + .45]);
  b.rod([-.62, bottom + 1.8, radius + .45], [0, bottom + 1.8, radius + .6]);
  b.rod([0, bottom + 1.8, radius + .6], [0, bottom + 1.35, radius + .6], .018);
  const lugShape = new Shape();
  lugShape.moveTo(-.16, 0); lugShape.lineTo(.16, 0); lugShape.lineTo(.16, .32);
  lugShape.absarc(0, .32, .16, 0, Math.PI, false); lugShape.closePath();
  const lug = subtract(new ExtrudeGeometry(lugShape, { depth: .08, bevelEnabled: false, curveSegments: 16 }),
    new CylinderGeometry(.075, .075, .2, 24).rotateX(Math.PI / 2).translate(0, .32, .04));
  for (const side of [-1, 1]) b.add(lug.clone(), "steel", [radius * .9 * side, top - .02, 0]);
  lug.dispose();
  b.add(new BoxGeometry(.27, .17, .015), "machined", [.4, bottom + 2.2, radius]);
  if (spec.platform) {
    for (const level of [.25, .6, .85]) {
      b.add(annulus(radius + .5, radius + .08, .06), "paint", [0, bottom + height * level, 0]);
      b.ring(radius + .48, bottom + height * level + .65);
      for (let i = 0; i < 10; i++) {
        const a = i / 10 * Math.PI * 2;
        b.rod([Math.cos(a) * (radius + .48), bottom + height * level, Math.sin(a) * (radius + .48)],
          [Math.cos(a) * (radius + .48), bottom + height * level + .65, Math.sin(a) * (radius + .48)], .015);
      }
    }
    for (let y = bottom + .6; y < top - .3; y += 1) b.add(new CylinderGeometry(radius * .96, radius * .96, .025, 48), "machined", [0, y, 0]);
    b.ladder(.2, top, radius + .6);
  }
  b.anchors = { flange: new Vector3(0, top - .9, radius + .4), skirt: new Vector3(0, .47, radius), lug: new Vector3(-radius * .9, top + .3, .04) };
  return b.finish("vertical");
}

function saddles(b: Builder, length: number, radius: number, centerY: number) {
  for (const x of [-length * .3, length * .3]) {
    const saddle = subtract(new BoxGeometry(.32, centerY - .35, radius * 2.5),
      new CylinderGeometry(radius * 1.01, radius * 1.01, .5, 48).rotateZ(Math.PI / 2).translate(0, (centerY + .35) / 2, 0));
    b.add(saddle, "paint", [x, (centerY - .35) / 2 + .1, 0]);
    b.add(new BoxGeometry(.7, .12, radius * 2.8), "machined", [x, .1, 0]);
    for (const z of [-radius * 1.1, radius * 1.1]) b.bolt([x, .16, z]);
  }
}

export function buildHorizontalDrum(): EquipmentGeometry {
  const b = new Builder();
  b.shell(.95, 5.4, [0, 1.8, 0], [1, 0, 0]);
  saddles(b, 5.4, .95, 1.8);
  b.nozzle([-1.4, 2.75, 0], [0, 1, 0], .18);
  b.nozzle([1.3, 2.75, 0], [0, 1, 0]);
  b.nozzle([3.175, 1.8, 0], [1, 0, 0], .28, true);
  b.anchors = { flange: new Vector3(-1.4, 3.1, 0), skirt: new Vector3(-1.62, .7, 0) };
  return b.finish("horizontal");
}

export function buildColumn(): EquipmentGeometry {
  const model = buildVerticalVessel({ radius: .75, height: 7, platform: true });
  model.kind = "column";
  return model;
}

export function buildHeatExchanger(): EquipmentGeometry {
  const b = new Builder(), radius = .85, length = 4.6, y = 1.65;
  b.shell(radius, length, [0, y, 0], [1, 0, 0], true);
  saddles(b, length, radius, y);
  for (let row = -3; row <= 3; row++) for (let col = -3; col <= 3; col++) {
    const a = row * .17, c = col * .17;
    if (Math.hypot(a, c) < .64) b.add(annulus(.045, .031, length, 12), "machined", [0, y + a, c], [1, 0, 0]);
  }
  for (const side of [-1, 1]) {
    b.add(annulus(1, .68, .12), "machined", [side * length / 2, y, 0], [1, 0, 0]);
    for (let i = 0; i < 16; i++) {
      const a = i / 16 * Math.PI * 2;
      b.bolt([side * (length / 2 + .07), y + Math.cos(a) * .88, Math.sin(a) * .88], [side, 0, 0]);
    }
  }
  b.nozzle([-1.4, y + radius, 0], [0, 1, 0], .17);
  b.nozzle([1.4, y - radius, 0], [0, -1, 0], .17);
  b.anchors = { flange: new Vector3(2.4, y, 0), skirt: new Vector3(-1.4, .7, 0) };
  return b.finish("exchanger");
}

export function buildTank(): EquipmentGeometry {
  const b = new Builder(), r = 1.9, h = 3.5;
  b.add(new CylinderGeometry(r, r, h, 80, 1, true), "steel", [0, h / 2 + .15, 0]);
  b.add(new ConeGeometry(r, .65, 80), "steel", [0, h + .475, 0]);
  b.add(new CylinderGeometry(r, r, .12, 80), "steel", [0, .1, 0]);
  for (const y of [.2, 1.35, 2.5, 3.65]) b.ring(r + .01, y);
  b.add(annulus(r + .15, r - .1, .08), "machined", [0, .1, 0]);
  for (let i = 0; i < 20; i++) {
    const a = i / 20 * Math.PI * 2;
    b.bolt([Math.cos(a) * (r + .06), .13, Math.sin(a) * (r + .06)]);
  }
  b.nozzle([0, 4.3, 0], [0, 1, 0], .1);
  b.nozzle([0, .65, r], [0, 0, 1], .2);
  b.nozzle([0, 1.3, r], [0, 0, 1], .32, true);
  b.ladder(.2, 3.8, -r - .2);
  b.anchors = { flange: new Vector3(0, .65, r + .4), skirt: new Vector3(0, .1, r) };
  return b.finish("tank");
}

const builders = { vertical: buildVerticalVessel, horizontal: buildHorizontalDrum, column: buildColumn, exchanger: buildHeatExchanger, tank: buildTank };
const cache = new Map<EquipmentKind, { model: EquipmentGeometry; users: number; timer?: ReturnType<typeof setTimeout> }>();
export function equipmentGeometry(kind: EquipmentKind) {
  let entry = cache.get(kind);
  if (!entry) { entry = { model: builders[kind](), users: 0 }; cache.set(kind, entry); }
  return entry.model;
}
export function retainEquipment(kind: EquipmentKind) {
  const entry = cache.get(kind);
  if (!entry) return () => {};
  clearTimeout(entry.timer); entry.users++;
  return () => { entry.users--; if (!entry.users) entry.timer = setTimeout(() => {
    if (entry.users) return;
    entry.model.dispose(); cache.delete(kind);
  }, 200); };
}
