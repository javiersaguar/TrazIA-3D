import {
  BufferAttribute,
  DoubleSide,
  InstancedBufferAttribute,
  InstancedBufferGeometry,
  Mesh,
  ShaderMaterial,
} from "three";
import type { AtmosphereUniforms } from "./atmosphere";
import { linear } from "./builder";
import { ATMOSPHERE_GLSL } from "./glsl";
import { mulberry32, picker } from "./random";

/*
  Gaviotas: una malla instanciada (un draw call). Cuerpo fusiforme y alas en dos tramos con el
  perfil en "M" de las gaviotas; el aleteo y el planeo se calculan en el vértice con el tiempo
  común: cada ave alterna rachas de aleteo con planeos largos, describe óvalos que se abren y se
  cierran y se inclina hacia dentro del giro.
*/

/** Geometría de una gaviota de 1,3 m de envergadura: x hacia delante, y arriba, z a la izquierda. */
export function gullGeometry() {
  const positions: number[] = [];
  const normals: number[] = [];
  const colors: number[] = [];
  const wings: number[] = [];
  const indices: number[] = [];
  const white = linear("#f3f3ef");
  const grey = linear("#8f999f");
  const black = linear("#1d1f21");
  const beak = linear("#d9a521");
  const vertex = (p: [number, number, number], n: [number, number, number], c: readonly number[], wing: number) => {
    positions.push(...p);
    normals.push(...n);
    colors.push(c[0]!, c[1]!, c[2]!);
    wings.push(wing);
    return positions.length / 3 - 1;
  };
  // Cuerpo: secciones hexagonales de la cola a la cabeza.
  const sections: [number, number, number][] = [[-0.3, 0.012, 0.01], [-0.18, 0.04, 0.035], [-0.02, 0.055, 0.05], [0.12, 0.05, 0.045], [0.2, 0.035, 0.033], [0.26, 0.02, 0.02]];
  const sides = 6;
  const bodyStart = positions.length / 3;
  for (const [x, ry, rz] of sections) {
    for (let i = 0; i < sides; i++) {
      const a = (i / sides) * Math.PI * 2;
      const n: [number, number, number] = [0, Math.cos(a), Math.sin(a)];
      vertex([x, Math.cos(a) * ry, Math.sin(a) * rz], n, white, 0);
    }
  }
  for (let s = 0; s < sections.length - 1; s++) {
    for (let i = 0; i < sides; i++) {
      const a = bodyStart + s * sides + i, b = bodyStart + s * sides + ((i + 1) % sides);
      const c = a + sides, d = b + sides;
      indices.push(a, c, b, b, c, d);
    }
  }
  // Pico.
  const tip = vertex([0.33, -0.004, 0], [1, 0, 0], beak, 0);
  const last = bodyStart + (sections.length - 1) * sides;
  for (let i = 0; i < sides; i++) indices.push(last + i, tip, last + ((i + 1) % sides));
  // Cola en abanico.
  const tail = [vertex([-0.26, 0.01, 0.05], [0, 1, 0], white, 0), vertex([-0.38, 0.0, 0.07], [0, 1, 0], white, 0),
    vertex([-0.38, 0.0, -0.07], [0, 1, 0], white, 0), vertex([-0.26, 0.01, -0.05], [0, 1, 0], white, 0)];
  indices.push(tail[0]!, tail[1]!, tail[2]!, tail[0]!, tail[2]!, tail[3]!);
  // Alas: raíz, codo y punta, con cuerda que se estrecha y flecha hacia atrás.
  for (const side of [1, -1]) {
    const root = 0.04, elbow = 0.32, end = 0.66;
    const inner = [
      vertex([0.11, 0.02, root * side], [0, 1, 0], grey, 1),
      vertex([-0.09, 0.02, root * side], [0, 1, 0], grey, 1),
      vertex([0.09, 0.03, elbow * side], [0, 1, 0], grey, 1),
      vertex([-0.11, 0.03, elbow * side], [0, 1, 0], grey, 1),
    ];
    const outer = [
      vertex([0.09, 0.03, elbow * side], [0, 1, 0], grey, 2),
      vertex([-0.11, 0.03, elbow * side], [0, 1, 0], grey, 2),
      vertex([0.0, 0.02, (end - 0.12) * side], [0, 1, 0], black, 2),
      vertex([-0.13, 0.02, (end - 0.12) * side], [0, 1, 0], black, 2),
      vertex([-0.12, 0.01, end * side], [0, 1, 0], black, 2),
    ];
    const tri = (a: number, b: number, c: number) => side > 0 ? indices.push(a, b, c) : indices.push(a, c, b);
    tri(inner[0]!, inner[2]!, inner[1]!);
    tri(inner[1]!, inner[2]!, inner[3]!);
    tri(outer[0]!, outer[2]!, outer[1]!);
    tri(outer[1]!, outer[2]!, outer[3]!);
    tri(outer[2]!, outer[4]!, outer[3]!);
  }
  return { positions, normals, colors, wings, indices };
}

const VERTEX = /* glsl */ `
${ATMOSPHERE_GLSL}
attribute vec3 color;
attribute float wing;
attribute vec4 aPath;
attribute vec4 aMotion;
varying vec3 vColor;
varying vec3 vNormal;
varying vec3 vWorld;
void main() {
  float t = uEnvTime;
  float seed = aMotion.w;
  float ang = aMotion.y + aMotion.x * t;
  float radius = aPath.z * (1.0 + 0.2 * sin(t * 0.11 + seed * 6.0));
  vec3 center = vec3(aPath.x + cos(ang) * radius, aPath.w + 3.5 * sin(t * 0.19 + seed * 4.0), aPath.y + sin(ang) * radius * 0.78);
  vec3 forward = normalize(vec3(-sin(ang), 0.12 * cos(t * 0.19 + seed * 4.0), cos(ang) * 0.78) * sign(aMotion.x));
  float bank = sign(aMotion.x) * (0.28 + 0.1 * sin(t * 0.3 + seed));
  vec3 up0 = vec3(0.0, 1.0, 0.0);
  vec3 left0 = normalize(cross(up0, forward));
  vec3 up = normalize(up0 * cos(bank) + left0 * sin(bank));
  vec3 left = normalize(cross(up, forward));
  // Rachas de aleteo entre planeos.
  float gate = smoothstep(0.55, 0.85, sin(t * 0.33 + seed * 11.0) * 0.5 + 0.5);
  float flap = sin(t * aMotion.z + seed * 20.0) * gate * 0.6;
  vec3 p = position;
  vec3 n = normal;
  float side = sign(p.z);
  float root = 0.04, elbow = 0.32;
  if (wing > 0.5) {
    // Ala izquierda (z > 0) y derecha simétricas: giro sobre el eje x en la raíz y en el codo.
    float a1 = 0.12 + flap;
    float r = abs(p.z) - root;
    if (wing < 1.5) {
      p = vec3(p.x, p.y + r * sin(a1), side * (root + r * cos(a1)));
      n = vec3(0.0, cos(a1), -side * sin(a1));
    } else {
      float a = a1 - 0.28 + flap * 0.6;
      float re = elbow - root;
      float r2 = abs(p.z) - elbow;
      p = vec3(p.x, p.y + re * sin(a1) + r2 * sin(a), side * (root + re * cos(a1) + r2 * cos(a)));
      n = vec3(0.0, cos(a), -side * sin(a));
    }
  }
  float scale = 1.0 + 0.15 * fract(seed * 7.13);
  vec3 world = center + (forward * p.x + up * p.y + left * p.z) * scale;
  vWorld = world;
  vNormal = normalize(forward * n.x + up * n.y + left * n.z);
  vColor = color;
  gl_Position = projectionMatrix * viewMatrix * vec4(world, 1.0);
}
`;

const FRAGMENT = /* glsl */ `
${ATMOSPHERE_GLSL}
varying vec3 vColor;
varying vec3 vNormal;
varying vec3 vWorld;
void main() {
  vec3 n = normalize(vNormal);
  vec3 albedo = vColor;
  if (!gl_FrontFacing) { n = -n; albedo = mix(albedo, vec3(0.86, 0.87, 0.86), 0.75); }
  float ndl = max(dot(n, uEnvSunDir), 0.0);
  vec3 color = albedo * (uEnvSunLight * ndl * 0.32 + envAmbient(n) * 0.75);
  gl_FragColor = vec4(envFog(color, vWorld), 1.0);
}
`;

export type FlockOptions = {
  count: number;
  seed: number;
  /** Centro (x, z) del vuelo, radio medio, cota media y dispersión de cotas. */
  center: [number, number];
  radius: [number, number];
  altitude: [number, number];
};

export function createGulls(atmosphere: AtmosphereUniforms, options: FlockOptions): Mesh {
  const shape = gullGeometry();
  const geometry = new InstancedBufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(shape.positions), 3));
  geometry.setAttribute("normal", new BufferAttribute(new Float32Array(shape.normals), 3));
  geometry.setAttribute("color", new BufferAttribute(new Float32Array(shape.colors), 3));
  geometry.setAttribute("wing", new BufferAttribute(new Float32Array(shape.wings), 1));
  geometry.setIndex(shape.indices);
  const random = mulberry32(options.seed);
  const pick = picker(random);
  const paths = new Float32Array(options.count * 4);
  const motion = new Float32Array(options.count * 4);
  for (let i = 0; i < options.count; i++) {
    const offset = pick.range(0, Math.PI * 2);
    const distance = pick.range(0, options.radius[0] * 0.6);
    paths.set([
      options.center[0] + Math.cos(offset) * distance,
      options.center[1] + Math.sin(offset) * distance,
      pick.range(options.radius[0], options.radius[1]),
      pick.range(options.altitude[0], options.altitude[1]),
    ], i * 4);
    const radius = paths[i * 4 + 2]!;
    // Unos 9-12 m/s de crucero.
    const speed = pick.range(8.5, 12) / radius;
    motion.set([speed * pick.sign(), pick.range(0, Math.PI * 2), pick.range(5.5, 7.5), random()], i * 4);
  }
  geometry.setAttribute("aPath", new InstancedBufferAttribute(paths, 4));
  geometry.setAttribute("aMotion", new InstancedBufferAttribute(motion, 4));
  geometry.instanceCount = options.count;
  const material = new ShaderMaterial({
    name: "entorno-gaviotas",
    uniforms: { ...atmosphere },
    vertexShader: VERTEX,
    fragmentShader: FRAGMENT,
    side: DoubleSide,
  });
  const mesh = new Mesh(geometry, material);
  mesh.name = "entorno-gaviotas";
  mesh.frustumCulled = false;
  mesh.matrixAutoUpdate = false;
  return mesh;
}
