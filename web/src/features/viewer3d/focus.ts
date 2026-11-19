import { Box3, Vector3 } from "three";
import type { Bounds, Vec3 } from "@/workers/ifc-protocol";

/*
  Piezas auxiliares del encuadre por selección (ver framing.ts y occlusion.ts):

  - la caja de un componente tal y como se dibuja (con el desplazamiento del explosionado);
  - qué piezas atenuar porque aún tapan el componente desde la cámara.

  Una pieza se atenúa si tapa una parte apreciable de lo que se ve del objetivo y no lo sostiene
  ni lo envuelve: la estructura de la cubierta o un rack cuya caja contiene el centro del equipo se
  quedan opacos, porque atenuarlos dejaría el equipo flotando en el aire. Con las plantas
  descompuestas (barandillas, pedestales y chapas como piezas propias) solo se atenúa la pieza
  concreta que estorba.
*/

/** Fracción mínima de lo visible del objetivo que debe tapar una pieza para atenuarla. */
export const GHOST_SHARE = 0.05;
/** Muestras de superficie del objetivo para puntuar la visibilidad y buscar lo que lo tapa. */
export const FOCUS_SAMPLES = 64;

/**
 * Holgura del encuadre según el tamaño (diagonal en metros): una pieza pequeña necesita más
 * contexto alrededor para saber dónde está; un equipo grande puede llenar más el cuadro.
 * 2 m → 2,3 · 7 m → 1,95 · 17 m → 1,6 · 40 m → 1,4.
 */
export function focusMargin(diagonal: number): number {
  return 1.35 + 1.1 * Math.exp(-Math.max(0, diagonal) / 12);
}

export type Placed = { semanticId: string; bounds: Bounds; center: Vec3 };

/** Caja de una pieza dibujada en `position` (su centro desplazado, p. ej. en explosionado). */
export function placedBox(product: Placed, position: Vec3 = product.center): Box3 {
  const shift = new Vector3(position[0] - product.center[0], position[1] - product.center[1], position[2] - product.center[2]);
  return new Box3(new Vector3(...product.bounds.min).add(shift), new Vector3(...product.bounds.max).add(shift));
}

/** Unión de las cajas de las piezas `ids`. */
export function unionBox(products: Placed[], ids: ReadonlySet<string>, positions?: ReadonlyMap<string, Vec3>): Box3 {
  const box = new Box3();
  for (const product of products) {
    if (ids.has(product.semanticId)) box.union(placedBox(product, positions?.get(product.semanticId)));
  }
  return box;
}

/** Piezas que atenuar, de más a menos estorbo. */
export function ghostsFor(
  blockers: ReadonlyMap<string, number>,
  target: Box3,
  boxes: ReadonlyMap<string, Box3>,
  share = GHOST_SHARE,
): string[] {
  const center = target.getCenter(new Vector3());
  return [...blockers.entries()]
    .filter(([id, fraction]) => {
      if (fraction < share) return false;
      const box = boxes.get(id);
      return !box || !box.containsPoint(center);
    })
    .sort((a, b) => b[1] - a[1])
    .map(([id]) => id);
}

/** Elevación (grados) del ojo sobre el objetivo. */
export function elevationOf(eye: Vec3, target: Vec3): number {
  const dx = eye[0] - target[0], dy = eye[1] - target[1], dz = eye[2] - target[2];
  return (Math.atan2(dy, Math.hypot(dx, dz)) * 180) / Math.PI;
}
