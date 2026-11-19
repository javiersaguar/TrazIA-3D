import {
  BufferAttribute,
  BufferGeometry,
  Color,
  Matrix3,
  Matrix4,
  Quaternion,
  Vector3,
} from "three";

/*
  Constructor de mallas del atrezo. Escribe primitivas (cajas, cilindros, esferas, tornos…) en
  arrays planos con color por vértice, con una pila de transformaciones. Así cada objeto del
  entorno sale en una sola malla y un solo draw call por material, sin crear miles de geometrías
  intermedias.

  Opcionalmente proyecta cada primitiva sobre el suelo según el sol y guarda su envolvente
  convexa: son las sombras "pintadas" de lo que queda fuera del mapa de sombras real.
*/

export type Vec3Like = readonly [number, number, number];
export type ShadowOptions = { direction: Vec3Like; groundY: number };

const tmp = new Vector3();
const tmpNormal = new Vector3();
const yAxis = new Vector3(0, 1, 0);

/** Color sRGB (hex o rgb) a lineal. */
export function linear(hex: string): [number, number, number] {
  const color = new Color(hex);
  return [color.r, color.g, color.b];
}

export class MeshBuilder {
  positions: number[] = [];
  normals: number[] = [];
  colors: number[] = [];
  /** Rugosidad y metalicidad por vértice (atributo `surface`). */
  surfaces: number[] = [];
  indices: number[] = [];
  private matrix = new Matrix4();
  private normalMatrix = new Matrix3();
  private stack: Matrix4[] = [];
  private rgb: [number, number, number] = [0.6, 0.6, 0.6];
  private finish: [number, number] = [0.8, 0];
  private shadowing: ShadowOptions | null = null;
  /** Triángulos de sombra proyectada (solo posiciones), si se activó `shadow`. */
  shadow: number[] = [];

  constructor(options?: { shadow?: ShadowOptions }) {
    this.shadowing = options?.shadow ?? null;
  }

  get vertexCount() {
    return this.positions.length / 3;
  }

  color(value: string | readonly [number, number, number], roughness?: number, metalness?: number) {
    this.rgb = typeof value === "string" ? linear(value) : [value[0], value[1], value[2]];
    if (roughness !== undefined) this.finish = [roughness, metalness ?? 0];
    return this;
  }

  /** Acabado de lo que se dibuje a continuación: rugosidad y metalicidad PBR. */
  surface(roughness: number, metalness = 0) {
    this.finish = [roughness, metalness];
    return this;
  }

  push(transform?: Matrix4) {
    this.stack.push(this.matrix.clone());
    if (transform) this.matrix.multiply(transform);
    this.normalMatrix.getNormalMatrix(this.matrix);
    return this;
  }

  pop() {
    this.matrix = this.stack.pop() ?? new Matrix4();
    this.normalMatrix.getNormalMatrix(this.matrix);
    return this;
  }

  /** Traslada (y gira en Y, en radianes) el sistema actual. */
  at(x: number, y: number, z: number, rotationY = 0, scale = 1) {
    const m = new Matrix4().makeRotationY(rotationY).setPosition(x, y, z);
    if (scale !== 1) m.scale(new Vector3(scale, scale, scale));
    return this.push(m);
  }

  private vertex(x: number, y: number, z: number, nx: number, ny: number, nz: number) {
    tmp.set(x, y, z).applyMatrix4(this.matrix);
    tmpNormal.set(nx, ny, nz).applyMatrix3(this.normalMatrix).normalize();
    this.positions.push(tmp.x, tmp.y, tmp.z);
    this.normals.push(tmpNormal.x, tmpNormal.y, tmpNormal.z);
    this.colors.push(this.rgb[0], this.rgb[1], this.rgb[2]);
    this.surfaces.push(this.finish[0], this.finish[1]);
    return this.positions.length / 3 - 1;
  }

  private castShadow(first: number, shadow: boolean) {
    if (!shadow || !this.shadowing) return;
    const { direction, groundY } = this.shadowing;
    const points: [number, number][] = [];
    const last = this.positions.length / 3;
    for (let i = first; i < last; i++) {
      const x = this.positions[i * 3]!;
      const y = this.positions[i * 3 + 1]!;
      const z = this.positions[i * 3 + 2]!;
      const t = (y - groundY) / Math.max(direction[1], 0.05);
      points.push([x - direction[0] * t, z - direction[2] * t]);
    }
    const hull = convexHull(points);
    for (let i = 1; i + 1 < hull.length; i++) {
      const a = hull[0]!, b = hull[i]!, c = hull[i + 1]!;
      this.shadow.push(a[0], groundY, a[1], c[0], groundY, c[1], b[0], groundY, b[1]);
    }
  }

  /** Caja centrada en (x, y, z) con tamaño (sx, sy, sz). */
  box(x: number, y: number, z: number, sx: number, sy: number, sz: number, shadow = false) {
    const first = this.vertexCount;
    const hx = sx / 2, hy = sy / 2, hz = sz / 2;
    const faces: [Vec3Like, Vec3Like, Vec3Like][] = [
      [[1, 0, 0], [0, 0, -1], [0, 1, 0]],
      [[-1, 0, 0], [0, 0, 1], [0, 1, 0]],
      [[0, 1, 0], [1, 0, 0], [0, 0, -1]],
      [[0, -1, 0], [1, 0, 0], [0, 0, 1]],
      [[0, 0, 1], [1, 0, 0], [0, 1, 0]],
      [[0, 0, -1], [-1, 0, 0], [0, 1, 0]],
    ];
    for (const [n, u, v] of faces) {
      const base = this.vertexCount;
      for (const [su, sv] of [[-1, -1], [1, -1], [1, 1], [-1, 1]] as const) {
        this.vertex(
          x + n[0] * hx + u[0] * su * hx + v[0] * sv * hx,
          y + n[1] * hy + u[1] * su * hy + v[1] * sv * hy,
          z + n[2] * hz + u[2] * su * hz + v[2] * sv * hz,
          n[0], n[1], n[2],
        );
      }
      this.indices.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
    this.castShadow(first, shadow);
    return this;
  }

  /** Tronco de cono (o cilindro) entre a y b. */
  cylinder(a: Vec3Like, b: Vec3Like, r0: number, r1 = r0, sides = 12, caps = true, shadow = false) {
    const first = this.vertexCount;
    const axis = new Vector3(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
    const length = axis.length();
    if (length < 1e-6) return this;
    axis.divideScalar(length);
    const q = new Quaternion().setFromUnitVectors(yAxis, axis);
    const m = new Matrix4().makeRotationFromQuaternion(q).setPosition(a[0], a[1], a[2]);
    this.push(m);
    const slope = (r0 - r1) / length;
    const ny = slope / Math.hypot(1, slope);
    const nr = 1 / Math.hypot(1, slope);
    const base = this.vertexCount;
    for (let i = 0; i <= sides; i++) {
      const angle = (i / sides) * Math.PI * 2;
      const c = Math.cos(angle), s = Math.sin(angle);
      this.vertex(c * r0, 0, s * r0, c * nr, ny, s * nr);
      this.vertex(c * r1, length, s * r1, c * nr, ny, s * nr);
    }
    for (let i = 0; i < sides; i++) {
      const p = base + i * 2;
      this.indices.push(p, p + 1, p + 3, p, p + 3, p + 2);
    }
    if (caps) {
      for (const [y, r, sign] of [[0, r0, -1], [length, r1, 1]] as const) {
        if (r <= 1e-5) continue;
        const center = this.vertex(0, y, 0, 0, sign, 0);
        for (let i = 0; i <= sides; i++) {
          const angle = (i / sides) * Math.PI * 2;
          this.vertex(Math.cos(angle) * r, y, Math.sin(angle) * r, 0, sign, 0);
        }
        for (let i = 0; i < sides; i++) {
          if (sign > 0) this.indices.push(center, center + i + 2, center + i + 1);
          else this.indices.push(center, center + i + 1, center + i + 2);
        }
      }
    }
    this.pop();
    this.castShadow(first, shadow);
    return this;
  }

  /** Esfera (o casquete) centrada en c. theta mide desde el polo superior. */
  sphere(c: Vec3Like, r: number, widthSegments = 16, heightSegments = 10, thetaStart = 0, thetaLength = Math.PI, shadow = false, scaleY = 1) {
    const first = this.vertexCount;
    const base = this.vertexCount;
    for (let iy = 0; iy <= heightSegments; iy++) {
      const theta = thetaStart + (iy / heightSegments) * thetaLength;
      const st = Math.sin(theta), ct = Math.cos(theta);
      for (let ix = 0; ix <= widthSegments; ix++) {
        const phi = (ix / widthSegments) * Math.PI * 2;
        const nx = -Math.cos(phi) * st, ny = ct, nz = Math.sin(phi) * st;
        this.vertex(c[0] + nx * r, c[1] + ny * r * scaleY, c[2] + nz * r, nx, ny / Math.max(scaleY, 0.05), nz);
      }
    }
    const row = widthSegments + 1;
    for (let iy = 0; iy < heightSegments; iy++) {
      for (let ix = 0; ix < widthSegments; ix++) {
        const a = base + iy * row + ix;
        const b = a + row;
        this.indices.push(a, b, a + 1, b, b + 1, a + 1);
      }
    }
    this.castShadow(first, shadow);
    return this;
  }

  /** Sólido de revolución alrededor del eje Y que pasa por c. profile = [[radio, y], …]. */
  lathe(c: Vec3Like, profile: readonly (readonly [number, number])[], sides = 16, shadow = false) {
    const first = this.vertexCount;
    const base = this.vertexCount;
    const count = profile.length;
    for (let j = 0; j < count; j++) {
      const [r, y] = profile[j]!;
      const prev = profile[Math.max(0, j - 1)]!;
      const next = profile[Math.min(count - 1, j + 1)]!;
      const dr = next[0] - prev[0], dy = next[1] - prev[1];
      const len = Math.hypot(dr, dy) || 1;
      const nr = dy / len, ny = -dr / len;
      for (let i = 0; i <= sides; i++) {
        const angle = (i / sides) * Math.PI * 2;
        const cs = Math.cos(angle), sn = Math.sin(angle);
        this.vertex(c[0] + cs * r, c[1] + y, c[2] + sn * r, cs * nr, ny, sn * nr);
      }
    }
    const row = sides + 1;
    for (let j = 0; j < count - 1; j++) {
      for (let i = 0; i < sides; i++) {
        const a = base + j * row + i;
        const b = a + row;
        this.indices.push(a, b, a + 1, b, b + 1, a + 1);
      }
    }
    this.castShadow(first, shadow);
    return this;
  }

  /** Toro horizontal (anillo de plataforma, viga de coronación…). */
  torus(c: Vec3Like, radius: number, tube: number, radialSegments = 6, tubularSegments = 24) {
    const base = this.vertexCount;
    for (let j = 0; j <= radialSegments; j++) {
      const v = (j / radialSegments) * Math.PI * 2;
      for (let i = 0; i <= tubularSegments; i++) {
        const u = (i / tubularSegments) * Math.PI * 2;
        const cx = Math.cos(u), sx = Math.sin(u);
        const nx = Math.cos(v) * cx, ny = Math.sin(v), nz = Math.cos(v) * sx;
        this.vertex(
          c[0] + (radius + tube * Math.cos(v)) * cx,
          c[1] + tube * Math.sin(v),
          c[2] + (radius + tube * Math.cos(v)) * sx,
          nx, ny, nz,
        );
      }
    }
    const row = tubularSegments + 1;
    for (let j = 0; j < radialSegments; j++) {
      for (let i = 0; i < tubularSegments; i++) {
        const a = base + j * row + i;
        const b = a + row;
        this.indices.push(a, b, a + 1, b, b + 1, a + 1);
      }
    }
    return this;
  }

  /** Prisma vertical de planta poligonal convexa o estrellada (orden antihorario visto desde arriba). */
  prism(points: readonly (readonly [number, number])[], y0: number, y1: number, shadow = false) {
    const first = this.vertexCount;
    const n = points.length;
    for (let i = 0; i < n; i++) {
      const [ax, az] = points[i]!;
      const [bx, bz] = points[(i + 1) % n]!;
      const ex = bx - ax, ez = bz - az;
      const len = Math.hypot(ex, ez) || 1;
      const nx = -ez / len, nz = ex / len;
      const base = this.vertexCount;
      this.vertex(ax, y0, az, nx, 0, nz);
      this.vertex(bx, y0, bz, nx, 0, nz);
      this.vertex(bx, y1, bz, nx, 0, nz);
      this.vertex(ax, y1, az, nx, 0, nz);
      this.indices.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
    let cx = 0, cz = 0;
    for (const [x, z] of points) { cx += x / n; cz += z / n; }
    const center = this.vertex(cx, y1, cz, 0, 1, 0);
    for (const [x, z] of points) this.vertex(x, y1, z, 0, 1, 0);
    for (let i = 0; i < n; i++) this.indices.push(center, center + 1 + i, center + 1 + ((i + 1) % n));
    this.castShadow(first, shadow);
    return this;
  }

  /**
    Superficie de filas de puntos (casco, lona, ladera): une cada fila con la siguiente y
    promedia las normales. `closed` cierra cada fila sobre sí misma.
  */
  strip(rows: readonly (readonly Vec3Like[])[], closed = false, flip = false, colorAt?: (p: Vec3Like) => readonly [number, number, number]) {
    const keep = this.rgb;
    const nRows = rows.length;
    const nCols = rows[0]?.length ?? 0;
    if (nRows < 2 || nCols < 2) return this;
    const at = (r: number, c: number) => rows[Math.max(0, Math.min(nRows - 1, r))]![closed ? (c + nCols) % nCols : Math.max(0, Math.min(nCols - 1, c))]!;
    const base = this.vertexCount;
    const a = new Vector3(), b = new Vector3(), n = new Vector3();
    for (let r = 0; r < nRows; r++) {
      for (let c = 0; c < nCols; c++) {
        const p = at(r, c);
        const pr0 = at(r - 1, c), pr1 = at(r + 1, c), pc0 = at(r, c - 1), pc1 = at(r, c + 1);
        a.set(pr1[0] - pr0[0], pr1[1] - pr0[1], pr1[2] - pr0[2]);
        b.set(pc1[0] - pc0[0], pc1[1] - pc0[1], pc1[2] - pc0[2]);
        n.crossVectors(b, a);
        if (flip) n.negate();
        if (n.lengthSq() < 1e-12) n.set(0, 1, 0);
        n.normalize();
        if (colorAt) { const c = colorAt(p); this.rgb = [c[0], c[1], c[2]]; }
        this.vertex(p[0], p[1], p[2], n.x, n.y, n.z);
      }
    }
    this.rgb = keep;
    const cols = closed ? nCols : nCols - 1;
    for (let r = 0; r < nRows - 1; r++) {
      for (let c = 0; c < cols; c++) {
        const c1 = (c + 1) % nCols;
        const i00 = base + r * nCols + c, i01 = base + r * nCols + c1;
        const i10 = base + (r + 1) * nCols + c, i11 = base + (r + 1) * nCols + c1;
        if (flip) this.indices.push(i00, i10, i01, i01, i10, i11);
        else this.indices.push(i00, i01, i10, i01, i11, i10);
      }
    }
    return this;
  }

  /** Polígono plano (convexo) en abanico desde su centroide, con normal n. */
  fan(points: readonly Vec3Like[], n: Vec3Like) {
    const count = points.length;
    if (count < 3) return this;
    let cx = 0, cy = 0, cz = 0;
    for (const p of points) { cx += p[0] / count; cy += p[1] / count; cz += p[2] / count; }
    // Normal de Newell: si el contorno gira al revés que n, se invierte el abanico.
    let nx = 0, ny = 0, nz = 0;
    for (let i = 0; i < count; i++) {
      const a = points[i]!, b = points[(i + 1) % count]!;
      nx += (a[1] - b[1]) * (a[2] + b[2]);
      ny += (a[2] - b[2]) * (a[0] + b[0]);
      nz += (a[0] - b[0]) * (a[1] + b[1]);
    }
    const reverse = nx * n[0] + ny * n[1] + nz * n[2] < 0;
    const center = this.vertex(cx, cy, cz, n[0], n[1], n[2]);
    for (const p of points) this.vertex(p[0], p[1], p[2], n[0], n[1], n[2]);
    for (let i = 0; i < count; i++) {
      const a = center + 1 + i, b = center + 1 + ((i + 1) % count);
      if (reverse) this.indices.push(center, b, a); else this.indices.push(center, a, b);
    }
    return this;
  }

  /** Cuadrilátero de dos caras (cartel, banda pintada) con normal n. */
  quad(a: Vec3Like, b: Vec3Like, c: Vec3Like, d: Vec3Like) {
    const e1 = new Vector3(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
    const e2 = new Vector3(d[0] - a[0], d[1] - a[1], d[2] - a[2]);
    const n = e1.cross(e2).normalize();
    const base = this.vertexCount;
    for (const p of [a, b, c, d]) this.vertex(p[0], p[1], p[2], n.x, n.y, n.z);
    this.indices.push(base, base + 1, base + 2, base, base + 2, base + 3);
    return this;
  }

  /** Celosía (mástil, antorcha, grúa) como aristas finas entre cuatro montantes. */
  lattice(bottom: Vec3Like, top: Vec3Like, w0: number, w1: number, bays: number, member: number) {
    const corners = (y: number, w: number) => [[-w, -w], [w, -w], [w, w], [-w, w]].map(
      ([dx, dz]) => [bottom[0] + (top[0] - bottom[0]) * y + dx!, bottom[1] + (top[1] - bottom[1]) * y, bottom[2] + (top[2] - bottom[2]) * y + dz!] as const,
    );
    for (let k = 0; k < bays; k++) {
      const t0 = k / bays, t1 = (k + 1) / bays;
      const lo = corners(t0, w0 + (w1 - w0) * t0);
      const hi = corners(t1, w0 + (w1 - w0) * t1);
      for (let i = 0; i < 4; i++) {
        this.cylinder(lo[i]!, hi[i]!, member, member, 4, false);
        this.cylinder(lo[i]!, hi[(i + 1) % 4]!, member * 0.6, member * 0.6, 3, false);
        this.cylinder(hi[i]!, hi[(i + 1) % 4]!, member * 0.6, member * 0.6, 3, false);
      }
    }
    return this;
  }

  /** Copia otra construcción (ya transformada) dentro de esta. */
  merge(other: MeshBuilder) {
    const offset = this.vertexCount;
    for (const value of other.positions) this.positions.push(value);
    for (const value of other.normals) this.normals.push(value);
    for (const value of other.colors) this.colors.push(value);
    for (const value of other.surfaces) this.surfaces.push(value);
    for (const index of other.indices) this.indices.push(index + offset);
    for (const value of other.shadow) this.shadow.push(value);
    return this;
  }

  toGeometry(): BufferGeometry {
    const geometry = new BufferGeometry();
    geometry.setAttribute("position", new BufferAttribute(new Float32Array(this.positions), 3));
    geometry.setAttribute("normal", new BufferAttribute(new Float32Array(this.normals), 3));
    geometry.setAttribute("color", new BufferAttribute(new Float32Array(this.colors), 3));
    geometry.setAttribute("surface", new BufferAttribute(new Float32Array(this.surfaces), 2));
    const count = this.vertexCount;
    geometry.setIndex(new BufferAttribute(count > 65535 ? new Uint32Array(this.indices) : new Uint16Array(this.indices), 1));
    geometry.computeBoundingSphere();
    return geometry;
  }

  shadowGeometry(): BufferGeometry | null {
    if (!this.shadow.length) return null;
    const geometry = new BufferGeometry();
    geometry.setAttribute("position", new BufferAttribute(new Float32Array(this.shadow), 3));
    geometry.computeBoundingSphere();
    return geometry;
  }
}

/** Envolvente convexa 2D (cadena monótona de Andrew), en sentido antihorario. */
export function convexHull(points: readonly (readonly [number, number])[]): [number, number][] {
  const sorted = [...points].map(p => [p[0], p[1]] as [number, number])
    .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (sorted.length < 3) return sorted;
  const cross = (o: [number, number], a: [number, number], b: [number, number]) =>
    (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lower: [number, number][] = [];
  for (const p of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2]!, lower[lower.length - 1]!, p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper: [number, number][] = [];
  for (let i = sorted.length - 1; i >= 0; i--) {
    const p = sorted[i]!;
    while (upper.length >= 2 && cross(upper[upper.length - 2]!, upper[upper.length - 1]!, p) <= 0) upper.pop();
    upper.push(p);
  }
  upper.pop();
  lower.pop();
  return lower.concat(upper);
}

/** Malla radial: anillos con separación geométrica, densa en el centro y hasta `outer`. */
export function radialGrid(inner: number, outer: number, segments: number, stretch = 1): BufferGeometry {
  const radii = [0, inner];
  const growth = 1 + ((Math.PI * 2) / segments) * stretch;
  while (radii[radii.length - 1]! < outer) radii.push(Math.min(outer, radii[radii.length - 1]! * growth));
  const positions: number[] = [0, 0, 0];
  for (let r = 1; r < radii.length; r++) {
    for (let i = 0; i < segments; i++) {
      const angle = (i / segments) * Math.PI * 2 + (r % 2) * (Math.PI / segments);
      positions.push(Math.cos(angle) * radii[r]!, 0, Math.sin(angle) * radii[r]!);
    }
  }
  const indices: number[] = [];
  for (let i = 0; i < segments; i++) indices.push(0, 1 + ((i + 1) % segments), 1 + i);
  for (let r = 1; r < radii.length - 1; r++) {
    const a0 = 1 + (r - 1) * segments;
    const b0 = 1 + r * segments;
    const odd = r % 2 === 1;
    for (let i = 0; i < segments; i++) {
      const a = a0 + i, a1 = a0 + ((i + 1) % segments);
      const b = b0 + i, b1 = b0 + ((i + 1) % segments);
      // El anillo exterior va girado medio paso: triángulos casi equiláteros.
      if (odd) indices.push(a, b1, b, a, a1, b1);
      else indices.push(a, a1, b, a1, b1, b);
    }
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(positions), 3));
  const normals = new Float32Array(positions.length);
  for (let i = 1; i < normals.length; i += 3) normals[i] = 1;
  geometry.setAttribute("normal", new BufferAttribute(normals, 3));
  geometry.setIndex(new BufferAttribute(positions.length / 3 > 65535 ? new Uint32Array(indices) : new Uint16Array(indices), 1));
  geometry.boundingSphere = null;
  return geometry;
}
