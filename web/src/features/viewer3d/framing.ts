import { Box3, Vector3 } from "three";

/*
  Encuadre de un componente con su tamaño real y sin que lo tapen otros.

  CameraControls.fitToBox redondea azimut y polar a múltiplos de 90°: deja la cámara de lado y a
  ras de suelo. Aquí se prueban direcciones en una semiesfera (azimut × elevación), se lanzan
  rayos desde puntos del objetivo hacia cada cámara candidata y se puntúa:

  - visibilidad (fracción de rayos que llegan sin chocar con otra pieza), que manda;
  - elevación cercana a la preferida, para ver el equipo desde arriba y en perspectiva;
  - continuidad con la dirección actual, para no desorientar;
  - mirar desde fuera de la planta hacia dentro;
  - en piezas alargadas, mirar en perpendicular a su eje largo.

  Los candidatos se evalúan de más a menos prometedor y cada uno abandona sus rayos en cuanto ya
  no puede superar al mejor: con cientos de piezas el encuadre cuesta unos pocos milisegundos.

  La distancia (o el zoom ortográfico) sale de proyectar las ocho esquinas en la base de la
  cámara, con margen. Todo es Y arriba, en metros, como el visor. Funciones puras: el rayo lo
  aporta quien llama (three-mesh-bvh en el visor, cajas en las pruebas).
*/

export type Hit = { distance: number; id: string };
/** Primer impacto desde `origin` en `direction` (unitario) hasta `far`, ignorando el objetivo. */
export type Raycast = (origin: Vector3, direction: Vector3, far: number) => Hit | null;

export type Lens =
  | { kind: "perspective"; fov: number; aspect: number } // fov vertical en grados
  | { kind: "orthographic"; width: number; height: number }; // tamaño del visor en píxeles

/** Punto del objetivo; con normal, solo cuenta si mira hacia la cámara y pesa según lo de frente que esté. */
export type Sample = Vector3 | { point: Vector3; normal?: Vector3 };

export type FramingOptions = {
  /** Elevación preferida sobre el horizonte, en grados. */
  elevation?: number;
  elevations?: number[];
  azimuthSteps?: number;
  /** Holgura alrededor del objetivo: 1 lo deja tocando los bordes. */
  margin?: number;
  /** Cota mínima del ojo (p. ej. la lámina de agua o el terreno). */
  groundY?: number;
};

export type Framing = {
  /** Del objetivo hacia la cámara, unitario. */
  direction: Vector3;
  eye: Vector3;
  target: Vector3;
  distance: number;
  /** Solo en ortográfica: zoom de la cámara para que el objetivo llene el visor con margen. */
  zoom?: number;
  visibility: number;
  score: number;
  /** Piezas que siguen tapando parte del objetivo desde la dirección elegida, de más a menos. */
  occluders: string[];
  /** Candidatos evaluados y rayos lanzados (para medir el coste). */
  stats?: { candidates: number; rays: number };
};

const DEG = Math.PI / 180;
const UP = new Vector3(0, 1, 0);

export function candidateDirections(
  azimuthSteps = 24,
  elevations: number[] = [16, 26, 36, 48, 62],
): Vector3[] {
  const result: Vector3[] = [];
  for (const elevation of elevations) {
    const e = elevation * DEG;
    for (let i = 0; i < azimuthSteps; i++) {
      const a = (i / azimuthSteps) * Math.PI * 2;
      result.push(new Vector3(Math.cos(e) * Math.sin(a), Math.sin(e), Math.cos(e) * Math.cos(a)));
    }
  }
  return result;
}

/**
 * Puntos del objetivo desde los que se comprueba la visibilidad: centro, esquinas y centros de
 * cara metidos hacia dentro (un rayo que sale justo de una cara chocaría con la pieza vecina
 * sobre la que apoya) y, si se dan, vértices reales de la pieza.
 */
export function samplePoints(box: Box3, extra: Vector3[] = [], shrink = 0.14): Vector3[] {
  const center = box.getCenter(new Vector3());
  const half = box.getSize(new Vector3()).multiplyScalar(0.5 * (1 - shrink));
  const points = [center.clone()];
  for (const x of [-1, 1]) for (const y of [-1, 1]) for (const z of [-1, 1]) {
    points.push(new Vector3(center.x + x * half.x, center.y + y * half.y, center.z + z * half.z));
  }
  for (let axis = 0; axis < 3; axis++) {
    for (const side of [-1, 1]) {
      const p = center.clone();
      p.setComponent(axis, p.getComponent(axis) + side * half.getComponent(axis));
      points.push(p);
    }
  }
  return points.concat(extra);
}

/** Base de la cámara que mira hacia el objetivo desde `direction`. */
function basis(direction: Vector3) {
  const forward = direction.clone().negate();
  const right = new Vector3().crossVectors(forward, UP);
  if (right.lengthSq() < 1e-8) right.set(1, 0, 0);
  right.normalize();
  const up = new Vector3().crossVectors(right, forward).normalize();
  return { right, up };
}

const corners = (box: Box3) => {
  const result: Vector3[] = [];
  for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) {
    result.push(new Vector3(x, y, z));
  }
  return result;
};

/**
 * Distancia del centro a la cámara (perspectiva) o zoom (ortográfica) para ver todos los puntos,
 * mirando hacia `center` desde `direction`.
 */
export function fitPoints(points: Vector3[], center: Vector3, direction: Vector3, lens: Lens, margin = 1.3) {
  const { right, up } = basis(direction);
  let radius = 0.05;
  const offset = new Vector3();
  for (const p of points) radius = Math.max(radius, offset.subVectors(p, center).length());
  if (lens.kind === "orthographic") {
    let width = 0, height = 0;
    for (const p of points) {
      offset.subVectors(p, center);
      width = Math.max(width, Math.abs(offset.dot(right)) * 2);
      height = Math.max(height, Math.abs(offset.dot(up)) * 2);
    }
    const zoom = Math.min(lens.width / Math.max(width * margin, 0.1), lens.height / Math.max(height * margin, 0.1));
    return { distance: Math.max(10, radius * 4), zoom };
  }
  const tanV = Math.tan((lens.fov * DEG) / 2);
  const tanH = tanV * Math.max(0.1, lens.aspect);
  let distance = 0;
  for (const p of points) {
    offset.subVectors(p, center);
    const depth = offset.dot(direction);
    distance = Math.max(
      distance,
      depth + (margin * Math.abs(offset.dot(right))) / tanH,
      depth + (margin * Math.abs(offset.dot(up))) / tanV,
    );
  }
  return { distance: Math.max(distance, radius * 1.05 + 0.5) };
}

/** Distancia del centro a la cámara (perspectiva) o zoom (ortográfica) para ver la caja entera. */
export function fitDistance(box: Box3, direction: Vector3, lens: Lens, margin = 1.3) {
  return fitPoints(corners(box), box.getCenter(new Vector3()), direction, lens, margin);
}

/** Eje largo de una pieza claramente alargada (p. ej. un recipiente horizontal o un tramo). */
function longAxis(box: Box3): Vector3 | null {
  const size = box.getSize(new Vector3());
  const axes = [size.x, size.y, size.z];
  const order = [0, 1, 2].sort((a, b) => axes[b]! - axes[a]!);
  if (axes[order[0]!]! < 1.6 * Math.max(axes[order[1]!]!, 0.01)) return null;
  return new Vector3().setComponent(order[0]!, 1);
}

type Weighted = { point: Vector3; normal?: Vector3 };
const asWeighted = (sample: Sample): Weighted => (sample instanceof Vector3 ? { point: sample } : sample);

/**
 * Visibilidad ponderada desde `eye` (perspectiva) o en `direction` (ortográfica). Con `bound`, deja
 * de lanzar rayos en cuanto la visibilidad máxima alcanzable no llega a `bound`.
 */
function visibilityFrom(
  direction: Vector3,
  eye: Vector3,
  samples: Weighted[],
  raycast: Raycast,
  lens: Lens,
  reach: number,
  bound = -Infinity,
) {
  const rays: { origin: Vector3; ray: Vector3; far: number; weight: number }[] = [];
  let total = 0;
  for (const { point, normal } of samples) {
    const ray = new Vector3();
    let far: number;
    if (lens.kind === "perspective") {
      ray.subVectors(eye, point);
      far = ray.length();
      ray.divideScalar(Math.max(far, 1e-6));
    } else {
      ray.copy(direction);
      far = reach;
    }
    const weight = normal ? normal.dot(ray) : 1;
    if (weight <= 0.02) continue; // cara de espaldas: el propio objetivo la tapa
    total += weight;
    rays.push({ origin: point.clone().addScaledVector(ray, 0.04), ray, far, weight });
  }
  if (!rays.length || total <= 0) return { visibility: 0, occluders: [] as string[], cast: 0, complete: true };
  const counts = new Map<string, number>();
  let clear = 0, remaining = total, cast = 0;
  for (const { origin, ray, far, weight } of rays) {
    if ((clear + remaining) / total < bound) return { visibility: (clear + remaining) / total, occluders: [], cast, complete: false };
    const hit = raycast(origin, ray, Math.max(0, far - 0.04));
    cast++;
    remaining -= weight;
    if (!hit) clear += weight;
    else counts.set(hit.id, (counts.get(hit.id) ?? 0) + weight);
  }
  const occluders = [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([id]) => id);
  return { visibility: clear / total, occluders, cast, complete: true };
}

/** Piezas que tapan el objetivo desde una cámara concreta (al terminar de mover la cámara). */
export function occludersFrom(eye: Vector3, target: Box3, samples: Sample[], raycast: Raycast, lens: Lens) {
  const center = target.getCenter(new Vector3());
  const direction = eye.clone().sub(center).normalize();
  const reach = eye.distanceTo(center) * 2 + 10;
  return visibilityFrom(direction, eye, samples.map(asWeighted), raycast, lens, reach);
}

export function chooseFraming({
  target,
  scene,
  samples = samplePoints(target),
  raycast,
  lens,
  current,
  options = {},
}: {
  target: Box3;
  scene: Box3;
  samples?: Sample[];
  raycast: Raycast;
  lens: Lens;
  /** Dirección actual del objetivo hacia la cámara, para premiar giros cortos. */
  current?: Vector3;
  options?: FramingOptions;
}): Framing {
  const preferred = options.elevation ?? 32;
  const margin = options.margin ?? 1.3;
  const center = target.getCenter(new Vector3());
  const sceneCenter = scene.getCenter(new Vector3());
  const sceneSize = scene.getSize(new Vector3());
  const reach = sceneSize.length() * 1.5 + 10;
  const groundY = options.groundY ?? scene.min.y;
  const outward = new Vector3(center.x - sceneCenter.x, 0, center.z - sceneCenter.z);
  const offCenter = Math.min(1, outward.length() / Math.max(0.25 * Math.hypot(sceneSize.x, sceneSize.z), 1e-3));
  if (outward.lengthSq() > 1e-8) outward.normalize();
  const flatCurrent = current ? new Vector3(current.x, 0, current.z) : null;
  if (flatCurrent && flatCurrent.lengthSq() > 1e-8) flatCurrent.normalize();
  const axis = longAxis(target);
  const weighted = samples.map(asWeighted);

  // Puntuación previa (sin rayos) de cada candidato válido; la visibilidad suma como mucho 1.
  const candidates = candidateDirections(options.azimuthSteps, options.elevations).flatMap(direction => {
    const fit = fitDistance(target, direction, lens, margin);
    const eye = center.clone().addScaledVector(direction, fit.distance);
    if (lens.kind === "perspective" && eye.y < groundY + 1.5) return [];
    const elevation = Math.asin(Math.min(1, Math.max(-1, direction.y))) / DEG;
    const flat = new Vector3(direction.x, 0, direction.z).normalize();
    let prior = 0.25 * Math.exp(-(((elevation - preferred) / 16) ** 2));
    if (flatCurrent && flatCurrent.lengthSq() > 0) prior += 0.12 * (1 + flat.dot(flatCurrent)) / 2;
    if (outward.lengthSq() > 0) prior += 0.12 * offCenter * (1 + flat.dot(outward)) / 2;
    if (axis) prior += 0.12 * (1 - Math.abs(direction.dot(axis)));
    return [{ direction, fit, eye, prior }];
  }).sort((a, b) => b.prior - a.prior);

  let best: Framing | null = null;
  let rays = 0, evaluated = 0;
  for (const { direction, fit, eye, prior } of candidates) {
    if (best && prior + 1 <= best.score + 1e-9) break; // ni con visibilidad total supera al mejor
    evaluated++;
    const needed = best ? best.score - prior + 1e-9 : -Infinity;
    const result = visibilityFrom(direction, eye, weighted, raycast, lens, reach, needed);
    rays += result.cast;
    if (!result.complete) continue;
    const score = prior + result.visibility;
    if (!best || score > best.score + 1e-9) {
      best = {
        direction: direction.clone(),
        eye,
        target: center.clone(),
        distance: fit.distance,
        zoom: fit.zoom,
        visibility: result.visibility,
        score,
        occluders: result.occluders,
      };
    }
  }
  if (best) return { ...best, stats: { candidates: evaluated, rays } };
  // Ningún candidato por encima del suelo: vista alta por defecto.
  const direction = new Vector3(0.55, 0.62, 0.55).normalize();
  const fit = fitDistance(target, direction, lens, margin);
  return {
    direction,
    eye: center.clone().addScaledVector(direction, fit.distance),
    target: center,
    distance: fit.distance,
    zoom: fit.zoom,
    visibility: 0,
    score: 0,
    occluders: [],
    stats: { candidates: evaluated, rays },
  };
}

export type OverviewOptions = {
  /** Azimut desde +Z hacia +X, en grados (45 = tres cuartos). */
  azimuth?: number;
  /** Elevación del ojo sobre el centro de la planta, en grados. */
  elevation?: number;
  /**
   * Altura del horizonte en el encuadre (coordenada normalizada, 1 = borde superior). Inclina la
   * cámara hacia arriba lo justo para que asome el cielo; sin valor se mira al centro.
   */
  horizon?: number;
  /** Holgura en los bordes: 1 deja la planta tocándolos. */
  margin?: number;
};

/**
 * Vista general en perspectiva: ojo en tres cuartos y elevado, distancia mínima para que la
 * planta entera quepa y, si se pide, cámara algo inclinada hacia arriba para dejar ver el
 * horizonte. Devuelve el ojo y un objetivo en el eje de la cámara sobre la vertical del centro.
 */
export function overviewFraming(points: Vector3[], center: Vector3, lens: Extract<Lens, { kind: "perspective" }>, options: OverviewOptions = {}) {
  const azimuth = (options.azimuth ?? 40) * DEG;
  const elevation = (options.elevation ?? 26) * DEG;
  const margin = options.margin ?? 1.08;
  const tanV = Math.tan((lens.fov * DEG) / 2), tanH = tanV * Math.max(0.1, lens.aspect);
  const flat = new Vector3(Math.sin(azimuth), 0, Math.cos(azimuth));
  const direction = flat.clone().multiplyScalar(Math.cos(elevation)).addScaledVector(UP, Math.sin(elevation));
  // Inclinación de la cámara: la del ojo, o menor para que el horizonte quede en `horizon`.
  const pitch = options.horizon === undefined ? elevation : Math.min(elevation, Math.atan(options.horizon * tanV));
  const forward = flat.clone().multiplyScalar(-Math.cos(pitch)).addScaledVector(UP, -Math.sin(pitch));
  const right = new Vector3().crossVectors(forward, UP).normalize();
  const up = new Vector3().crossVectors(right, forward).normalize();
  const limit = 1 / margin;
  const offset = new Vector3();
  const fits = (distance: number) => {
    const eye = center.clone().addScaledVector(direction, distance);
    for (const p of points) {
      offset.subVectors(p, eye);
      const depth = offset.dot(forward);
      if (depth < 0.5) return false;
      if (Math.abs(offset.dot(right) / (depth * tanH)) > limit) return false;
      if (Math.abs(offset.dot(up) / (depth * tanV)) > limit) return false;
    }
    return true;
  };
  let radius = 1;
  for (const p of points) radius = Math.max(radius, offset.subVectors(p, center).length());
  let low = radius * 0.5, high = radius * 4;
  for (let i = 0; i < 40 && !fits(high); i++) high *= 1.6;
  if (!fits(high)) return null; // la inclinación pedida deja la planta fuera de cuadro
  for (let i = 0; i < 40; i++) {
    const mid = (low + high) / 2;
    if (fits(mid)) high = mid;
    else low = mid;
  }
  const eye = center.clone().addScaledVector(direction, high);
  // Objetivo en el eje de la cámara, a la distancia horizontal del centro: la órbita no se desplaza.
  const horizontal = Math.hypot(eye.x - center.x, eye.z - center.z);
  const along = horizontal / Math.max(Math.cos(pitch), 1e-3);
  const target = eye.clone().addScaledVector(forward, along);
  return { eye, target, distance: high, pitch: pitch / DEG, elevation: elevation / DEG };
}
