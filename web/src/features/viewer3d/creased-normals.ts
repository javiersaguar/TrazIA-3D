/*
  Normales suavizadas con ángulo de pliegue, solo para el sombreado.

  web-ifc entrega cada triángulo con sus tres vértices y la normal de su cara: las virolas, las
  tuberías y los fondos se ven facetados. Aquí se agrupan los vértices que ocupan la misma posición
  y, para cada uno, se promedian las normales de las caras vecinas que forman con la suya un ángulo
  menor que el pliegue (ponderadas por el ángulo de la esquina, que no depende de cómo se
  triangule un cuadrilátero). Las aristas vivas (bridas, cajas, perfiles) siguen marcadas.

  No cambia posiciones ni índices: devuelve un atributo de normales nuevo. Es lineal en vértices
  con una tabla hash de posiciones cuantizadas; equivalente a toCreasedNormals de three sin
  desindexar la malla.
*/

const EMPTY = -1;

export function creasedNormals(
  positions: ArrayLike<number>,
  indices: ArrayLike<number>,
  creaseDeg = 38,
  /** Normales originales para los vértices de caras degeneradas. */
  fallback?: ArrayLike<number>,
  quantum = 1e-4,
): Float32Array {
  const vertexCount = Math.floor(positions.length / 3);
  const triangleCount = Math.floor(indices.length / 3);
  const result = new Float32Array(vertexCount * 3);
  if (!vertexCount || !triangleCount) return result;
  const cosCrease = Math.cos((creaseDeg * Math.PI) / 180);

  // Normal unitaria de cada cara y ángulo de cada esquina.
  const faceNormal = new Float32Array(triangleCount * 3);
  const cornerAngle = new Float32Array(triangleCount * 3);
  for (let t = 0; t < triangleCount; t++) {
    const a = indices[t * 3]! * 3, b = indices[t * 3 + 1]! * 3, c = indices[t * 3 + 2]! * 3;
    const abx = positions[b]! - positions[a]!, aby = positions[b + 1]! - positions[a + 1]!, abz = positions[b + 2]! - positions[a + 2]!;
    const acx = positions[c]! - positions[a]!, acy = positions[c + 1]! - positions[a + 1]!, acz = positions[c + 2]! - positions[a + 2]!;
    const bcx = positions[c]! - positions[b]!, bcy = positions[c + 1]! - positions[b + 1]!, bcz = positions[c + 2]! - positions[b + 2]!;
    let nx = aby * acz - abz * acy, ny = abz * acx - abx * acz, nz = abx * acy - aby * acx;
    const length = Math.hypot(nx, ny, nz);
    if (length < 1e-12) continue; // degenerado: sin peso
    nx /= length; ny /= length; nz /= length;
    faceNormal[t * 3] = nx; faceNormal[t * 3 + 1] = ny; faceNormal[t * 3 + 2] = nz;
    const lab = Math.hypot(abx, aby, abz), lac = Math.hypot(acx, acy, acz), lbc = Math.hypot(bcx, bcy, bcz);
    const angle = (dot: number, l1: number, l2: number) => Math.acos(Math.max(-1, Math.min(1, dot / Math.max(l1 * l2, 1e-20))));
    cornerAngle[t * 3] = angle(abx * acx + aby * acy + abz * acz, lab, lac);
    cornerAngle[t * 3 + 1] = angle(-abx * bcx - aby * bcy - abz * bcz, lab, lbc);
    cornerAngle[t * 3 + 2] = Math.max(0, Math.PI - cornerAngle[t * 3]! - cornerAngle[t * 3 + 1]!);
  }

  // Grupo de posición de cada vértice (tabla hash abierta sobre coordenadas cuantizadas).
  const qx = new Int32Array(vertexCount), qy = new Int32Array(vertexCount), qz = new Int32Array(vertexCount);
  let size = 1;
  while (size < vertexCount * 2) size <<= 1;
  const table = new Int32Array(size).fill(EMPTY);
  const group = new Int32Array(vertexCount);
  for (let v = 0; v < vertexCount; v++) {
    const x = Math.round(positions[v * 3]! / quantum), y = Math.round(positions[v * 3 + 1]! / quantum), z = Math.round(positions[v * 3 + 2]! / quantum);
    qx[v] = x; qy[v] = y; qz[v] = z;
    let slot = ((Math.imul(x, 73856093) ^ Math.imul(y, 19349663) ^ Math.imul(z, 83492791)) >>> 0) & (size - 1);
    for (;;) {
      const other = table[slot]!;
      if (other === EMPTY) { table[slot] = v; group[v] = v; break; }
      if (qx[other] === x && qy[other] === y && qz[other] === z) { group[v] = other; break; }
      slot = (slot + 1) & (size - 1);
    }
  }

  // Esquinas agrupadas por posición (ordenación por cuentas).
  const cornerCount = triangleCount * 3;
  const count = new Int32Array(vertexCount + 1);
  for (let k = 0; k < cornerCount; k++) count[group[indices[k]!]! + 1]!++;
  for (let v = 0; v < vertexCount; v++) count[v + 1]! += count[v]!;
  const start = count.slice();
  const corners = new Int32Array(cornerCount);
  for (let k = 0; k < cornerCount; k++) corners[start[group[indices[k]!]!]!++] = k;
  // Cara propia de cada vértice: la primera esquina que lo usa.
  const ownFace = new Int32Array(vertexCount).fill(EMPTY);
  for (let k = 0; k < cornerCount; k++) {
    const v = indices[k]!;
    if (ownFace[v] === EMPTY) ownFace[v] = Math.floor(k / 3);
  }

  for (let v = 0; v < vertexCount; v++) {
    const face = ownFace[v]!;
    if (face === EMPTY || cornerAngle[face * 3]! + cornerAngle[face * 3 + 1]! === 0) {
      if (fallback) { result[v * 3] = fallback[v * 3]!; result[v * 3 + 1] = fallback[v * 3 + 1]!; result[v * 3 + 2] = fallback[v * 3 + 2]!; }
      continue;
    }
    const fx = faceNormal[face * 3]!, fy = faceNormal[face * 3 + 1]!, fz = faceNormal[face * 3 + 2]!;
    const g = group[v]!;
    const from = count[g]!, to = count[g + 1]!;
    let sx = 0, sy = 0, sz = 0;
    // Un vértice compartido por cientos de caras (vértice de un cono) no merece el coste cuadrático.
    if (to - from <= 512) {
      for (let i = from; i < to; i++) {
        const corner = corners[i]!, t = Math.floor(corner / 3);
        const nx = faceNormal[t * 3]!, ny = faceNormal[t * 3 + 1]!, nz = faceNormal[t * 3 + 2]!;
        if (nx * fx + ny * fy + nz * fz < cosCrease) continue;
        const weight = cornerAngle[corner]!;
        sx += nx * weight; sy += ny * weight; sz += nz * weight;
      }
    }
    const length = Math.hypot(sx, sy, sz);
    if (length > 1e-12) {
      result[v * 3] = sx / length; result[v * 3 + 1] = sy / length; result[v * 3 + 2] = sz / length;
    } else {
      result[v * 3] = fx; result[v * 3 + 1] = fy; result[v * 3 + 2] = fz;
    }
  }
  return result;
}
