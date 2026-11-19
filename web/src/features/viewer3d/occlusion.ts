import { Box3, DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Triangle, Vector3 } from "three";
import { acceleratedRaycast, ObjectBVH } from "three-mesh-bvh";
import type { Vec3 } from "@/workers/ifc-protocol";
import type { Raycast, Sample } from "./framing";
import type { PreparedProduct } from "./model-resource";

/*
  Índice de oclusión para el encuadre: mallas auxiliares que comparten la geometría (y su MeshBVH)
  de cada producto, colocadas donde se dibuja, pero que NO se añaden a la escena. Un ObjectBVH
  sobre ellas resuelve cada rayo en microsegundos; las piezas del objetivo se excluyen marcándolas
  invisibles durante la consulta (ObjectBVH salta los objetos ocultos).
*/

const material = new MeshBasicMaterial({ side: DoubleSide });

export class OcclusionIndex {
  private meshes: Mesh[] = [];
  private byId = new Map<string, Mesh[]>();
  private bvh: ObjectBVH | null = null;
  private ray = new Raycaster();

  constructor(private products: PreparedProduct[], positions: Map<string, Vec3>) {
    this.ray.firstHitOnly = true;
    for (const product of products) {
      const position = positions.get(product.semanticId) ?? product.center;
      const list: Mesh[] = [];
      for (const geometry of product.geometries) {
        const mesh = new Mesh(geometry, material);
        mesh.raycast = acceleratedRaycast;
        mesh.position.set(...position);
        mesh.updateMatrixWorld(true);
        mesh.userData.id = product.semanticId;
        list.push(mesh);
        this.meshes.push(mesh);
      }
      this.byId.set(product.semanticId, list);
    }
  }

  private tree() {
    this.bvh ??= this.meshes.length ? new ObjectBVH(this.meshes) : null;
    return this.bvh;
  }

  /** Rayos contra todo salvo `exclude` (el objetivo y sus piezas). */
  raycaster(exclude: Iterable<string>): Raycast {
    const hidden = [...exclude].flatMap(id => this.byId.get(id) ?? []);
    return (origin, direction, far) => {
      const tree = this.tree();
      if (!tree) return null;
      for (const mesh of hidden) mesh.visible = false;
      try {
        this.ray.set(origin, direction);
        this.ray.near = 0;
        this.ray.far = far;
        const hits = tree.raycast(this.ray, []);
        let best: { distance: number; id: string } | null = null;
        for (const hit of hits) {
          if (hit.distance <= far && (!best || hit.distance < best.distance)) best = { distance: hit.distance, id: String(hit.object.userData.id) };
        }
        return best;
      } finally {
        for (const mesh of hidden) mesh.visible = true;
      }
    };
  }

  /**
   * Piezas que se interponen entre la cámara y el objetivo, con la fracción (0–1) del peso de las
   * muestras que tapa cada una. A diferencia del encuadre, cuenta TODAS las piezas que corta cada
   * rayo, no solo la primera: si se atenúa la barandilla, el pedestal de detrás también debe
   * atenuarse. En ortográfica los rayos son paralelos al eje de la cámara.
   */
  blockers(eye: Vector3, target: Vector3, samples: Sample[], exclude: Iterable<string>, orthographic = false): Map<string, number> {
    const result = new Map<string, number>();
    const tree = this.tree();
    if (!tree || !samples.length) return result;
    const hidden = [...exclude].flatMap(id => this.byId.get(id) ?? []);
    const all = new Raycaster();
    all.firstHitOnly = false;
    const axis = eye.clone().sub(target).normalize();
    const reach = eye.distanceTo(target) * 2 + 50;
    const ray = new Vector3();
    let total = 0;
    for (const mesh of hidden) mesh.visible = false;
    try {
      for (const sample of samples) {
        const point = sample instanceof Vector3 ? sample : sample.point;
        const normal = sample instanceof Vector3 ? undefined : sample.normal;
        let far: number;
        if (orthographic) {
          ray.copy(axis);
          far = reach;
        } else {
          ray.subVectors(eye, point);
          far = ray.length();
          ray.divideScalar(Math.max(far, 1e-6));
        }
        const weight = normal ? normal.dot(ray) : 1;
        if (weight <= 0.02) continue;
        total += weight;
        all.set(point.clone().addScaledVector(ray, 0.04), ray);
        all.near = 0;
        all.far = Math.max(0, far - 0.04);
        const seen = new Set<string>();
        for (const hit of tree.raycast(all, [])) {
          if (hit.distance > all.far) continue;
          const id = String(hit.object.userData.id);
          if (seen.has(id)) continue;
          seen.add(id);
          result.set(id, (result.get(id) ?? 0) + weight);
        }
      }
    } finally {
      for (const mesh of hidden) mesh.visible = true;
    }
    if (total > 0) for (const [id, weight] of result) result.set(id, weight / total);
    return result;
  }

  /**
   * Puntos repartidos por la superficie de las piezas (ponderados por área, deterministas) con su
   * normal, más el centro de la caja: la visibilidad mide lo que se ve de verdad del objetivo.
   */
  samples(ids: string[], count = 28): Sample[] {
    const triangles: { a: Vector3; b: Vector3; c: Vector3; area: number }[] = [];
    let total = 0;
    const box = new Box3();
    for (const id of ids) {
      for (const mesh of this.byId.get(id) ?? []) {
        const position = mesh.geometry.getAttribute("position");
        const index = mesh.geometry.getIndex();
        if (!position) continue;
        const triangleCount = (index ? index.count : position.count) / 3;
        // Con mallas grandes basta con una muestra de triángulos repartida por el índice.
        const stride = Math.max(1, Math.floor(triangleCount / 4000));
        for (let t = 0; t < triangleCount; t += stride) {
          const vertex = (k: number) => new Vector3().fromBufferAttribute(position, index ? index.getX(t * 3 + k) : t * 3 + k).add(mesh.position);
          const a = vertex(0), b = vertex(1), c = vertex(2);
          const area = new Triangle(a, b, c).getArea();
          if (area < 1e-6) continue;
          total += area;
          triangles.push({ a, b, c, area: total });
          box.expandByPoint(a).expandByPoint(b).expandByPoint(c);
        }
      }
    }
    if (!triangles.length) return [];
    let state = 0x9e3779b9;
    const random = () => ((state = (Math.imul(1664525, state) + 1013904223) >>> 0) / 4294967296);
    const result: Sample[] = [box.getCenter(new Vector3())];
    for (let k = 0; k < count; k++) {
      const r = random() * total;
      let low = 0, high = triangles.length - 1;
      while (low < high) {
        const mid = (low + high) >> 1;
        if (triangles[mid]!.area < r) low = mid + 1;
        else high = mid;
      }
      const { a, b, c } = triangles[low]!;
      let u = random(), v = random();
      if (u + v > 1) { u = 1 - u; v = 1 - v; }
      const point = a.clone().multiplyScalar(1 - u - v).addScaledVector(b, u).addScaledVector(c, v);
      result.push({ point, normal: new Triangle(a, b, c).getNormal(new Vector3()) });
    }
    return result;
  }

  get size() {
    return this.products.length;
  }

  dispose() {
    this.bvh = null;
    this.meshes = [];
    this.byId.clear();
  }
}
