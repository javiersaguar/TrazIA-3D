import type { Bounds } from "@/workers/ifc-protocol";

/*
  Marco del emplazamiento: dónde está la planta y cuánto ocupa, en metros y con Y arriba.

  Todo el entorno se coloca respecto a este marco (centro de los límites del IFC), no respecto
  al origen: la niebla radial, la explanada del desierto, el muelle o las unidades vecinas.
  Se redondea para que un cambio pequeño de la planta (revisión A → B) no reconstruya el entorno.
*/

export type SiteFrame = {
  /** Centro en planta (x, z) de los límites del modelo. */
  x: number;
  z: number;
  /** Semiejes en planta. */
  halfX: number;
  halfZ: number;
  /** Radio en planta que envuelve la planta entera. */
  radius: number;
  /** Cotas mínima y máxima del modelo. */
  minY: number;
  maxY: number;
  /** Clave estable para memorizar la construcción del entorno. */
  key: string;
};

const round = (value: number, step: number) => Math.round(value / step) * step;

export function siteFrame(bounds: Bounds): SiteFrame {
  const [minX, minY, minZ] = bounds.min;
  const [maxX, maxY, maxZ] = bounds.max;
  const finite = [minX, minY, minZ, maxX, maxY, maxZ].every(Number.isFinite) && maxX >= minX && maxZ >= minZ;
  if (!finite) return { x: 0, z: 0, halfX: 20, halfZ: 20, radius: 28.3, minY: 0, maxY: 10, key: "0:0:20:20" };
  const x = round((minX + maxX) / 2, 1);
  const z = round((minZ + maxZ) / 2, 1);
  const halfX = Math.max(4, round((maxX - minX) / 2, 2));
  const halfZ = Math.max(4, round((maxZ - minZ) / 2, 2));
  return {
    x, z, halfX, halfZ,
    radius: Math.hypot(halfX, halfZ),
    minY: round(minY, 0.5),
    maxY: round(maxY, 0.5),
    key: [x, z, halfX, halfZ].join(":"),
  };
}

/** Distancia con signo (en planta) al rectángulo de la planta ampliado `margin` y redondeado. */
export function siteDistance(site: SiteFrame, x: number, z: number, margin = 0): number {
  const dx = Math.abs(x - site.x) - site.halfX - margin;
  const dz = Math.abs(z - site.z) - site.halfZ - margin;
  const outside = Math.hypot(Math.max(dx, 0), Math.max(dz, 0));
  return outside + Math.min(Math.max(dx, dz), 0);
}
