import { Box3, PerspectiveCamera, Ray, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import { chooseFraming, fitDistance, occludersFrom, overviewFraming, type Lens, type Raycast } from "./framing";

const box = (min: [number, number, number], max: [number, number, number]) =>
  new Box3(new Vector3(...min), new Vector3(...max));

/** Rayos contra cajas con nombre, como harían las piezas IFC con three-mesh-bvh. */
function boxes(obstacles: Record<string, Box3>): Raycast {
  return (origin, direction, far) => {
    const ray = new Ray(origin, direction);
    let best: { distance: number; id: string } | null = null;
    const point = new Vector3();
    for (const [id, obstacle] of Object.entries(obstacles)) {
      if (obstacle.containsPoint(origin)) return { distance: 0, id };
      if (!ray.intersectBox(obstacle, point)) continue;
      const distance = point.distanceTo(origin);
      if (distance <= far && (!best || distance < best.distance)) best = { distance, id };
    }
    return best;
  };
}

const lens: Lens = { kind: "perspective", fov: 35, aspect: 1.6 };
const elevationOf = (v: Vector3) => (Math.asin(v.y) * 180) / Math.PI;

describe("encuadre de un componente", () => {
  const target = box([-1, 0, -1], [1, 3, 1]);
  const scene = box([-30, 0, -30], [30, 12, 30]);

  it("sin obstáculos mira desde arriba en perspectiva, no a ras de suelo", () => {
    const framing = chooseFraming({ target, scene, raycast: boxes({}), lens, current: new Vector3(1, 0, 1) });
    expect(framing.visibility).toBe(1);
    expect(elevationOf(framing.direction)).toBeGreaterThan(20);
    expect(elevationOf(framing.direction)).toBeLessThan(50);
    expect(framing.eye.y).toBeGreaterThan(target.max.y);
  });

  it("gira lo justo: prefiere la dirección desde la que ya se miraba", () => {
    const current = new Vector3(1, 0.6, 0).normalize();
    const framing = chooseFraming({ target, scene, raycast: boxes({}), lens, current });
    expect(framing.direction.x).toBeGreaterThan(0.6);
  });

  it("rodea un muro que tapa el objetivo desde la vista actual", () => {
    const wall = box([2.5, 0, -6], [3.2, 9, 6]);
    const current = new Vector3(1, 0.5, 0).normalize();
    const framing = chooseFraming({ target, scene, raycast: boxes({ muro: wall }), lens, current });
    expect(framing.visibility).toBeGreaterThan(0.9);
    // El muro está en +X: la cámara se va a otro lado.
    expect(framing.direction.x).toBeLessThan(0.5);
  });

  it("si no hay forma de verlo entero, informa de lo que tapa", () => {
    const shell = { cubierta: box([-4, 3.5, -4], [4, 4, 4]), norte: box([-4, 0, 2], [4, 4, 2.5]),
      sur: box([-4, 0, -2.5], [4, 4, -2]), este: box([2, 0, -4], [2.5, 4, 4]), oeste: box([-2.5, 0, -4], [-2, 4, 4]) };
    const framing = chooseFraming({ target, scene, raycast: boxes(shell), lens });
    expect(framing.visibility).toBeLessThan(0.5);
    expect(framing.occluders.length).toBeGreaterThan(0);
  });

  it("en una pieza alargada mira en perpendicular a su eje", () => {
    const drum = box([-6, 1, -1], [6, 3, 1]);
    const framing = chooseFraming({ target: drum, scene, raycast: boxes({}), lens, current: new Vector3(1, 0.5, 0.2).normalize() });
    expect(Math.abs(framing.direction.x)).toBeLessThan(0.6);
  });

  it("el ojo no baja de la lámina de agua", () => {
    const low = box([-1, -1, -1], [1, 0.5, 1]);
    const framing = chooseFraming({ target: low, scene: box([-30, -9, -30], [30, 20, 30]), raycast: boxes({}), lens,
      options: { groundY: 0 } });
    expect(framing.eye.y).toBeGreaterThan(1.5);
  });
});

describe("distancia de encuadre", () => {
  it("en perspectiva deja las ocho esquinas dentro del encuadre con margen", () => {
    const target = box([-2, 0, -1], [2, 6, 1]);
    const direction = new Vector3(0.6, 0.5, 0.62).normalize();
    const { distance } = fitDistance(target, direction, lens, 1.3);
    const camera = new PerspectiveCamera(35, 1.6, 0.01, 1000);
    const center = target.getCenter(new Vector3());
    camera.position.copy(center).addScaledVector(direction, distance);
    camera.lookAt(center);
    camera.updateMatrixWorld();
    let extent = 0;
    for (const x of [-2, 2]) for (const y of [0, 6]) for (const z of [-1, 1]) {
      const p = new Vector3(x, y, z).project(camera);
      extent = Math.max(extent, Math.abs(p.x), Math.abs(p.y));
    }
    expect(extent).toBeLessThanOrEqual(1);
    // Ni demasiado lejos: el objetivo ocupa buena parte del visor.
    expect(extent).toBeGreaterThan(0.55);
  });

  it("en ortográfica devuelve un zoom que llena el visor con margen", () => {
    const target = box([-1, 0, -1], [1, 2, 1]);
    const { zoom } = fitDistance(target, new Vector3(0, 0, 1), { kind: "orthographic", width: 800, height: 400 }, 1.25);
    expect(zoom).toBeCloseTo(400 / (2 * 1.25), 5);
  });
});

describe("muestras con normal", () => {
  const target = box([-1, 0, -1], [1, 2, 1]);
  // Un tubo que atraviesa el volumen del objetivo: desde +X solo lo verían los rayos de la cara -X.
  const raycast = boxes({ tubo: box([-0.6, 0.2, -2], [-0.4, 1.8, 2]) });
  const face = (x: number, nx: number) => [0.5, 1, 1.5].flatMap(y => [-0.5, 0.5].map(z => ({ point: new Vector3(x, y, z), normal: new Vector3(nx, 0, 0) })));
  const eye = new Vector3(9, 4, 0.5);

  it("una cara de espaldas no cuenta: lo de dentro no penaliza la vista", () => {
    const withNormals = occludersFrom(eye, target, [...face(0.99, 1), ...face(-0.99, -1)], raycast, lens);
    expect(withNormals.visibility).toBe(1);
    expect(withNormals.occluders).toEqual([]);
  });

  it("sin normales los mismos puntos sí cuentan", () => {
    const plain = [...face(0.99, 1), ...face(-0.99, -1)].map(sample => sample.point);
    const result = occludersFrom(eye, target, plain, raycast, lens);
    expect(result.visibility).toBeCloseTo(0.5, 5);
    expect(result.occluders).toEqual(["tubo"]);
  });
});

describe("vista general en perspectiva", () => {
  const corners = (b: Box3) => [b.min.x, b.max.x].flatMap(x => [b.min.y, b.max.y].flatMap(y => [b.min.z, b.max.z].map(z => new Vector3(x, y, z))));
  const plant = box([-40, 0, -25], [40, 30, 25]);
  const center = plant.getCenter(new Vector3());
  const lens35 = { kind: "perspective" as const, fov: 35, aspect: 1.6 };

  function project(view: { eye: Vector3; target: Vector3 }) {
    const camera = new PerspectiveCamera(35, 1.6, 0.1, 5000);
    camera.position.copy(view.eye);
    camera.lookAt(view.target);
    camera.updateMatrixWorld();
    return camera;
  }

  it("cabe entera, en tres cuartos y elevada, llenando el encuadre", () => {
    const view = overviewFraming(corners(plant), center, lens35, { azimuth: 40, elevation: 26 })!;
    expect(view).not.toBeNull();
    const camera = project(view);
    let extent = 0;
    for (const p of corners(plant)) {
      const ndc = p.clone().project(camera);
      extent = Math.max(extent, Math.abs(ndc.x), Math.abs(ndc.y));
    }
    expect(extent).toBeLessThanOrEqual(1);
    expect(extent).toBeGreaterThan(0.8);
    const elevation = (Math.asin((view.eye.y - center.y) / view.eye.distanceTo(center)) * 180) / Math.PI;
    expect(elevation).toBeCloseTo(26, 3);
  });

  it("con horizonte, la cámara se inclina menos y el cielo asoma por arriba", () => {
    const view = overviewFraming(corners(plant), center, lens35, { elevation: 26, horizon: 0.8 })!;
    expect(view.pitch).toBeLessThan(26);
    const camera = project(view);
    // Un punto muy lejano a la altura del ojo (el horizonte) cae dentro del encuadre, cerca de arriba.
    const far = view.target.clone().sub(view.eye).setY(0).normalize().multiplyScalar(1e5).add(view.eye);
    const ndc = far.project(camera);
    expect(ndc.y).toBeGreaterThan(0.6);
    expect(ndc.y).toBeLessThan(1);
    for (const p of corners(plant)) expect(Math.abs(p.clone().project(camera).y)).toBeLessThanOrEqual(1);
  });
});
