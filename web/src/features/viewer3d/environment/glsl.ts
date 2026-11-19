/*
  Trozos GLSL comunes a todos los entornos.

  - Ruido con hash entero: igual en GPU y CPU (random.ts), sin `fract(sin(x) * 43758)`, que da
    valores distintos según la precisión de cada tarjeta.
  - Atmósfera: cielo, calima del horizonte y niebla radial desde el centro de la planta. La
    niebla depende de la distancia en planta al centro, no de la profundidad de la cámara: la
    planta queda nítida y lo lejano se funde con el horizonte igual en perspectiva y en
    ortográfica. Cerca del plano lejano de la cámara todo se funde también con la calima, para
    que el recorte de la cámara nunca deje un borde.

  Los uniformes `uEnv*` se comparten por referencia entre todos los materiales del entorno: se
  actualiza el tiempo una vez por fotograma y lo ven todos.
*/

export const NOISE_GLSL = /* glsl */ `
uint envHash(uint x) {
  x ^= x >> 16u; x *= 0x7feb352du; x ^= x >> 15u; x *= 0x846ca68bu; x ^= x >> 16u;
  return x;
}
float envHash2(ivec2 p) {
  return float(envHash(uint(p.x) * 0x9e3779b1u ^ envHash(uint(p.y) + 0x632be5abu))) * (1.0 / 4294967295.0);
}
float envHash1(float n) { return float(envHash(uint(int(n)) + 0x2545f491u)) * (1.0 / 4294967295.0); }
/* Ruido de valor quíntico en [0, 1]. */
float envValueNoise(vec2 p) {
  ivec2 i = ivec2(floor(p));
  vec2 f = fract(p);
  vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
  float a = envHash2(i);
  float b = envHash2(i + ivec2(1, 0));
  float c = envHash2(i + ivec2(0, 1));
  float d = envHash2(i + ivec2(1, 1));
  return a + (b - a) * u.x + (c - a) * u.y + (a - b - c + d) * u.x * u.y;
}
/* Ruido de valor con derivadas analíticas: (valor, d/dx, d/dy), valor en [-1, 1]. */
vec3 envNoised(vec2 p) {
  ivec2 i = ivec2(floor(p));
  vec2 f = fract(p);
  vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
  vec2 du = 30.0 * f * f * (f * (f - 2.0) + 1.0);
  float a = envHash2(i);
  float b = envHash2(i + ivec2(1, 0));
  float c = envHash2(i + ivec2(0, 1));
  float d = envHash2(i + ivec2(1, 1));
  float k1 = b - a, k2 = c - a, k4 = a - b - c + d;
  float v = a + k1 * u.x + k2 * u.y + k4 * u.x * u.y;
  vec2 g = du * vec2(k1 + k4 * u.y, k2 + k4 * u.x);
  return vec3(v * 2.0 - 1.0, g * 2.0);
}
const mat2 ENV_ROT = mat2(0.80, 0.60, -0.60, 0.80);
float envFbm(vec2 p) {
  float sum = 0.0, amp = 0.5;
  for (int i = 0; i < 5; i++) {
    sum += amp * envValueNoise(p);
    p = ENV_ROT * p * 2.03 + 17.1;
    amp *= 0.5;
  }
  return sum / 0.96875;
}
float envFbm3(vec2 p) {
  float sum = 0.0, amp = 0.5;
  for (int i = 0; i < 3; i++) {
    sum += amp * envValueNoise(p);
    p = ENV_ROT * p * 2.07 + 11.3;
    amp *= 0.5;
  }
  return sum / 0.875;
}
`;

export const ATMOSPHERE_GLSL = /* glsl */ `
uniform vec3 uEnvSunDir;
uniform vec3 uEnvSunColor;
uniform vec3 uEnvSunLight;
uniform vec3 uEnvSkyLight;
uniform vec3 uEnvBounce;
uniform vec3 uEnvZenith;
uniform vec3 uEnvHorizon;
uniform vec3 uEnvHaze;
uniform vec3 uEnvGround;
uniform vec3 uEnvSite;
uniform vec4 uEnvFog;
uniform vec4 uEnvCloud;
uniform vec3 uEnvCloudTint;
uniform float uEnvCloudStreak;
uniform float uEnvGlow;
uniform float uEnvTime;
uniform vec3 uEnvWind;
uniform float uEnvFar;
/* 1 mientras el entorno se anima; 0 con el movimiento parado. */
uniform float uEnvMotion;

/* Eje de la cámara en el mundo (hacia donde mira). */
vec3 envForward() {
  return -vec3(viewMatrix[0][2], viewMatrix[1][2], viewMatrix[2][2]);
}

/* Hacia dónde mira la cámara desde un punto: en ortográfica es su eje, en perspectiva el rayo. */
vec3 envViewRay(vec3 world) {
  return isOrthographic ? envForward() : normalize(world - cameraPosition);
}

/* Calima del horizonte: más clara hacia el sol. */
vec3 envHaze(vec3 dir) {
  vec2 h = normalize(dir.xz + vec2(1e-5, 0.0));
  vec2 s = normalize(uEnvSunDir.xz + vec2(1e-5, 0.0));
  float toward = dot(h, s) * 0.5 + 0.5;
  return uEnvHaze * (0.9 + 0.18 * toward) + uEnvSunColor * uEnvGlow * 0.07 * pow(toward, 8.0);
}

/* Radiancia del cielo en una dirección unitaria. disc = 1 pinta el disco solar. */
vec3 envSky(vec3 dir, float disc) {
  float up = clamp(dir.y, 0.0, 1.0);
  vec3 sky = mix(uEnvHorizon, uEnvZenith, pow(up, 0.5));
  sky = mix(sky, envHaze(dir), exp(-up * 16.0) * 0.8);
  float mu = clamp(dot(dir, uEnvSunDir), 0.0, 1.0);
  sky += uEnvSunColor * uEnvGlow * (0.03 * pow(mu, 4.0) + 0.10 * pow(mu, 32.0) + 0.6 * pow(mu, 420.0));
  sky += uEnvSunColor * disc * smoothstep(0.99996, 0.99999, mu) * 40.0;
  return mix(sky, envHaze(dir), smoothstep(0.0, -0.035, dir.y));
}

/* Luz difusa que llega a una superficie de normal n desde el cielo y el rebote del suelo. */
vec3 envAmbient(vec3 n) {
  return mix(uEnvBounce, uEnvSkyLight, n.y * 0.5 + 0.5);
}

/* Niebla radial alrededor de la planta, con algo menos de niebla en altura. */
float envFogAmount(vec3 world) {
  float d = length(world.xz - uEnvSite.xz);
  float amount = 1.0 - exp(-max(d - uEnvFog.x, 0.0) * uEnvFog.y);
  amount *= mix(1.0, exp(-max(world.y, 0.0) / uEnvFog.w), 0.35);
  amount = min(amount, uEnvFog.z);
  // Fundido con el plano lejano de la cámara: el recorte nunca deja un borde contra el cielo.
  float depth = dot(world - cameraPosition, envForward());
  return max(amount, smoothstep(uEnvFar * 0.55, uEnvFar * 0.93, depth));
}
vec3 envFog(vec3 color, vec3 world) {
  return mix(color, envHaze(envViewRay(world)), envFogAmount(world));
}
`;

/** Nubes procedurales: requiere NOISE_GLSL y ATMOSPHERE_GLSL antes. */
export const CLOUDS_GLSL = /* glsl */ `
/* Nubes en una capa a uEnvCloud.w metros: rgb y cobertura. */
vec4 envClouds(vec3 dir, vec3 eye, int octaves) {
  if (dir.y < 0.012 || uEnvCloud.x <= 0.0) return vec4(0.0);
  float t = max(uEnvCloud.w - eye.y, 50.0) / dir.y;
  vec2 p = eye.xz + dir.xz * t;
  vec2 wind = uEnvWind.xy;
  vec2 across = vec2(-wind.y, wind.x);
  // Coordenadas alineadas con el viento: los cirros se estiran a lo largo.
  vec2 q = vec2(dot(p, wind), dot(p, across)) / (850.0 * uEnvCloud.z);
  q.x *= 1.0 - 0.75 * uEnvCloudStreak;
  q.x -= uEnvTime * uEnvWind.z * 0.0016 / uEnvCloud.z;
  float n = octaves > 3 ? envFbm(q) : envFbm3(q);
  float coverage = uEnvCloud.x;
  float density = smoothstep(1.0 - coverage, 1.0 - coverage + uEnvCloud.y, n);
  vec2 sunStep = vec2(dot(uEnvSunDir.xz, wind), dot(uEnvSunDir.xz, across)) * 0.06;
  float toward = octaves > 3 ? envFbm(q + sunStep) : envFbm3(q + sunStep);
  float lit = clamp(0.55 + (n - toward) * 4.0, 0.0, 1.0);
  vec3 dark = uEnvCloudTint * mix(uEnvHorizon, uEnvZenith, 0.35) * 0.82;
  vec3 bright = uEnvCloudTint * (uEnvSunColor * 0.32 + uEnvHorizon * 0.62);
  vec3 color = mix(dark, bright, lit);
  float mu = clamp(dot(dir, uEnvSunDir), 0.0, 1.0);
  color += uEnvSunColor * pow(mu, 10.0) * (1.0 - density) * 0.9;
  float fade = smoothstep(0.012, 0.16, dir.y) * exp(-t * 0.000025);
  return vec4(color, density * fade * 0.96);
}
`;

/** Inyecta la niebla radial en materiales estándar de three (atrezo con luz PBR y sombras). */
export const FOG_VERTEX_PARS = /* glsl */ `
varying vec3 vEnvWorld;
`;
export const FOG_VERTEX = /* glsl */ `
{
  vec4 envWorld = vec4(transformed, 1.0);
  #ifdef USE_BATCHING
    envWorld = batchingMatrix * envWorld;
  #endif
  #ifdef USE_INSTANCING
    envWorld = instanceMatrix * envWorld;
  #endif
  vEnvWorld = (modelMatrix * envWorld).xyz;
}
`;
export const FOG_FRAGMENT_PARS = /* glsl */ `
varying vec3 vEnvWorld;
${ATMOSPHERE_GLSL}
`;
export const FOG_FRAGMENT = /* glsl */ `
gl_FragColor.rgb = envFog(gl_FragColor.rgb, vEnvWorld);
`;
