"use client";

import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import { BufferGeometry, Float32BufferAttribute, type Group, type ShaderMaterial } from "three";
import { useSceneActivity } from "./stage";
import type { ProcessEnvironmentId } from "./types";

type Setting = Exclude<ProcessEnvironmentId, "neutral">;
const skies = { ocean: "#93afbf", coast: "#a1bfc8", desert: "#d0b9a0", industrial: "#899ea9" };

const waterVertex = `
  uniform float time;
  uniform float swell;
  varying vec3 sea;
  varying vec2 slope;
  void main() {
    vec4 world = modelMatrix * vec4(position, 1.0);
    vec2 p = world.xz;
    vec2 a = vec2(.23, .11);
    vec2 b = vec2(-.19, .39);
    vec2 c = vec2(.64, -.25);
    float x = dot(p, a) - time * 1.42;
    float y = dot(p, b) - time * 1.68;
    float z = dot(p, c) - time * 2.14;
    float crest = sin(x);
    world.y += swell * (.63 * crest + .12 * (crest * crest - .5) + .26 * sin(y) + .11 * sin(z));
    slope = swell * (a * cos(x) * (.63 + .24 * crest) + .26 * b * cos(y) + .11 * c * cos(z));
    sea = world.xyz;
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

const waterFragment = `
  uniform float time;
  uniform float swell;
  varying vec3 sea;
  varying vec2 slope;
  void main() {
    vec2 p = sea.xz;
    float fine = sin(dot(p, vec2(3.1, 1.9)) - time * 3.3 + 1.5 * sin(p.y * .61));
    float crossWave = cos(dot(p, vec2(-2.1, 3.7)) - time * 2.9);
    float distanceFromSite = length(p);
    float ripple = 1.0 - smoothstep(38.0, 140.0, distanceFromSite);
    vec2 gradient = slope + ripple * vec2(.050 * fine, .038 * crossWave);
    vec3 normal = normalize(vec3(-gradient.x, 1.0, -gradient.y));
    vec3 sight = vec3(viewMatrix[0].z, viewMatrix[1].z, viewMatrix[2].z);
    vec3 sun = normalize(vec3(-.69, .65, -.32));
    float fresnel = pow(1.0 - max(0.0, dot(sight, normal)), 3.3);
    float light = max(0.0, dot(normal, sun));
    float glitter = pow(max(0.0, dot(normal, normalize(sun + sight))), 105.0);
    float crest = smoothstep(.63, .87, (sea.y + .38) / swell + .04 * fine);
    float chop = smoothstep(.52, .81, sin(p.x * .85 + p.y * .68 + fine * .6 - time * 1.9));
    float foam = crest * chop * ripple;
    vec3 color = mix(vec3(.005, .041, .089), vec3(.087, .22, .29), fresnel * .72);
    color += (.16 * light + .053 * ripple * fine) * vec3(.014, .18, .23);
    color += .09 * glitter * vec3(.60, .85, .91) + .29 * foam * vec3(.28, .62, .68);
    color = mix(color, vec3(.23, .37, .45), smoothstep(87.0, 218.0, distanceFromSite) * .58);
    gl_FragColor = vec4(color, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

const landVertex = `
  uniform float dune;
  varying vec3 land;
  varying vec2 gradient;
  float ridge(vec2 p, vec2 center, vec2 extent, float height) {
    vec2 d = p - center;
    d = mat2(.93, -.36, .36, .93) * d;
    return height * exp(-dot(d / extent, d / extent) * 2.1);
  }
  float heightAt(vec2 p) {
    return ridge(p, vec2(-62., -53.), vec2(49., 16.), 8.0)
      + ridge(p, vec2(7., -68.), vec2(61., 19.), 11.0)
      + ridge(p, vec2(67., -58.), vec2(38., 22.), 7.5)
      + ridge(p, vec2(86., 42.), vec2(23., 31.), 6.8)
      + ridge(p, vec2(-92., 36.), vec2(26., 25.), 5.9);
  }
  void main() {
    vec4 world = modelMatrix * vec4(position, 1.0);
    gradient = vec2(0.0);
    if (dune > .5) {
      float h = heightAt(world.xz);
      gradient = vec2(heightAt(world.xz + vec2(1., 0.)) - h, heightAt(world.xz + vec2(0., 1.)) - h);
      world.y += h;
    }
    land = world.xyz;
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

const landFragment = `
  uniform vec3 base;
  uniform vec3 highlight;
  uniform float dune;
  varying vec3 land;
  varying vec2 gradient;
  float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float variation(vec2 p) {
    vec2 cell = floor(p);
    vec2 t = smoothstep(vec2(0.), vec2(1.), fract(p));
    return mix(mix(hash(cell), hash(cell + vec2(1., 0.)), t.x),
      mix(hash(cell + vec2(0., 1.)), hash(cell + vec2(1., 1.)), t.x), t.y);
  }
  void main() {
    vec2 p = land.xz;
    float noise = mix(hash(floor(p * 12.0)), .5, smoothstep(.6, 2.5, max(fwidth(p.x), fwidth(p.y)) * 12.));
    float broad = variation(p * .083) * .75 + variation(p * .31) * .25;
    float sun = dot(normalize(vec3(-gradient.x, 1.0, -gradient.y)), normalize(vec3(-.7, .58, -.26)));
    float phase = p.y * 6.1 + p.x * 2.3 + variation(p * .43) * 4.;
    float ripple = sin(phase) * (1. - smoothstep(.64, 2., fwidth(phase)));
    float detail = .17 * noise + .28 * broad + dune * (sun * .44 + ripple * .09);
    float haze = smoothstep(70.0, 210.0, length(p)) * .24;
    gl_FragColor = vec4(mix(base, highlight, clamp(detail + haze, 0.0, 1.0)), 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

const ground = {
  sand: { base: { value: [.25, .143, .064] }, highlight: { value: [.74, .51, .27] }, dune: { value: 1 } },
  gravel: { base: { value: [.077, .091, .095] }, highlight: { value: [.27, .31, .33] }, dune: { value: 0 } },
};

function Ground({ kind, x = 0, width = 450 }: {
  kind: keyof typeof ground; x?: number; width?: number;
}) {
  const segments = kind === "sand" ? 80 : 1;
  return <mesh position={[x, -0.24, 0]} rotation={[-Math.PI / 2, 0, 0]}>
    <planeGeometry args={[width, 450, segments, segments]} />
    <shaderMaterial vertexShader={landVertex} fragmentShader={landFragment} uniforms={ground[kind]} />
  </mesh>;
}

const weeds = [
  { lane: 21, scale: 1.26, phase: .55, speed: 3.4 },
  { lane: 26, scale: .83, phase: .65, speed: 2.76 },
  { lane: -20, scale: 1.02, phase: .23, speed: 3.12 },
] as const;

function twigGeometry(seed: number) {
  let state = seed;
  const random = () => {
    state = (Math.imul(1664525, state) + 1013904223) >>> 0;
    return state / 4294967296;
  };
  const vertices: number[] = [];
  for (let i = 0; i < 38; i++) {
    const azimuth = random() * Math.PI * 2;
    const y = random() * 2 - 1;
    const radius = Math.sqrt(1 - y*y);
    const direction = [radius * Math.cos(azimuth), y, radius * Math.sin(azimuth)];
    let branch = [0, -.19, 0];
    for (const reach of [.35, .65, .88, 1]) {
      const tip = direction.map(axis => reach * axis * (.83 + .17 * random()) + (random() - .5) * .2);
      const fork = branch.map((axis, j) => axis + direction[j]! * .22 + (random() - .5) * .44);
      vertices.push(...branch, ...tip, ...branch, ...fork);
      branch = tip;
    }
  }
  return new BufferGeometry().setAttribute("position", new Float32BufferAttribute(vertices, 3));
}

function Water({ sea, harbor }: { sea: React.RefObject<ShaderMaterial | null>; harbor: boolean }) {
  const uniforms = useMemo(() => ({ time: { value: 0 }, swell: { value: harbor ? .53 : 1 } }), [harbor]);
  return <mesh position={[harbor ? -135 : 0, -.38, 0]} rotation={[-Math.PI / 2, 0, 0]}>
    <planeGeometry args={[harbor ? 220 : 448, 448, harbor ? 68 : 104, 104]} />
    <shaderMaterial ref={sea} uniforms={uniforms} vertexShader={waterVertex} fragmentShader={waterFragment} />
  </mesh>;
}

const buildings = [
  [-54,-46,15,8,20], [-35,-55,14,6,13], [4,-55,25,10,14], [28,-45,15,6,20], [52,-37,17,8,18],
] as const;

const vaporVertex = `
  uniform float time;
  varying float haze;
  void main() {
    float seed = abs(sin(position.z * 51.7 + position.x * 2.7));
    float age = fract(seed + time * (.052 + seed * .012));
    vec3 plume = position + vec3(5. * age, 8.0 * age, 1.5 * age);
    plume.x += (.15 + 1.85 * age) * sin(seed * 17.0 + time * .83);
    plume.z += (.19 + 1.45 * age) * cos(seed * 21.0 + time * .68);
    haze = sin(3.14159265 * age) * (1.0 - age * .6);
    gl_PointSize = clamp((.8 + 3.8 * age) * projectionMatrix[0][0] * 360., 2., 52.);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(plume, 1.0);
  }
`;
const vaporFragment = `
  varying float haze;
  void main() {
    float radius = length(gl_PointCoord - .5);
    gl_FragColor = vec4(.72, .82, .86, .17 * haze * (1.0 - smoothstep(.04, .5, radius)));
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;
const vaporPositions = new Float32Array([0, 2, 4].flatMap(index => {
  const [x, z, width, height] = buildings[index]!;
  return Array.from({length: 26}, (_, n) => [x + width * .37, height * 1.93, z + n * .013]).flat();
}));

function Steam({ material }: { material: React.RefObject<ShaderMaterial | null> }) {
  const uniforms = useMemo(() => ({ time: { value: 0 } }), []);
  return <points frustumCulled={false}>
    <bufferGeometry>
      <bufferAttribute attach="attributes-position" args={[vaporPositions, 3]} />
    </bufferGeometry>
    <shaderMaterial ref={material} uniforms={uniforms} vertexShader={vaporVertex}
      fragmentShader={vaporFragment} depthWrite={false} transparent />
  </points>;
}

function IndustrialBackdrop() {
  return buildings.map(([x,z,w,h,d], i) => <group key={x} position={[x,-.2,z]}>
    <mesh position={[0,h/2,0]}>
      <boxGeometry args={[w,h,d]} />
      <meshStandardMaterial color={i % 2 === 0 ? "#65777e" : "#7b8481"} roughness={0.94} />
    </mesh>
    <mesh position={[0,h+.26,0]}>
      <boxGeometry args={[w+.45,.52,d+.45]} />
      <meshStandardMaterial color="#9ba8aa" roughness={0.87} />
    </mesh>
    <mesh position={[0,h*.74,d*.501]}>
      <boxGeometry args={[w*.83,1.2,.085]} />
      <meshStandardMaterial color="#45595f" roughness={.61} />
    </mesh>
    <mesh position={[w*.37,h*1.28,0]}>
      <cylinderGeometry args={[.53,.83,h*1.3,12]} />
      <meshStandardMaterial color="#73838c" roughness={.8} />
    </mesh>
    {[1.63,1.78].map(level => <mesh position={[w*.37, h*level, 0]} key={level}>
      <cylinderGeometry args={[.57,.59,h*.065,12]} />
      <meshStandardMaterial color={level > 1.7 ? "#b48672" : "#c0b4a1"} roughness={.85} />
    </mesh>)}
  </group>);
}

export function ProcessEnvironment({ id, motion }: { id: Setting; motion: boolean }) {
  const animate = useSceneActivity() && motion;
  const invalidate = useThree(state => state.invalidate);
  const sea = useRef<ShaderMaterial>(null);
  const vapor = useRef<ShaderMaterial>(null);
  const weedGroups = useRef<(Group | null)[]>([]);
  const elapsed = useRef(0);
  const desert = id === "desert";
  const twigs = useMemo(() => desert ? weeds.map((_, i) => twigGeometry(102 + i)) : [], [desert]);

  useEffect(() => () => twigs.forEach(twig => twig.dispose()), [twigs]);
  useEffect(() => { if (animate) invalidate(); }, [animate, invalidate]);
  useFrame((state, delta) => {
    if (!animate) return;
    elapsed.current += Math.min(delta, .08);
    const t = elapsed.current;
    if (sea.current) sea.current.uniforms.time!.value = t;
    if (vapor.current) vapor.current.uniforms.time!.value = t;
    for (const [i, weed] of weeds.entries()) {
      const group = weedGroups.current[i];
      if (!group) continue;
      const distance = t * weed.speed + 1.1 * Math.sin(t * .67 + i);
      const travel = ((distance + 116 * weed.phase) % 116) - 58;
      const skip = Math.abs(Math.sin(t * 2.3 + i * 2)) ** 5;
      group.position.set(travel, -.24 + weed.scale * (.83 + .27 * skip), weed.lane + 1.3 * Math.sin(t * .22 + i));
      group.rotation.set(.17 * Math.sin(t + i), .23 * Math.sin(t * .9), -distance / weed.scale);
      group.scale.setScalar(weed.scale * Math.min(1, (58 - Math.abs(travel)) / 3));
    }
    state.invalidate();
  });

  return <>
    <color attach="background" args={[skies[id]]} />
    {id === "ocean" || id === "coast" ? <Water sea={sea} harbor={id === "coast"} /> : null}
    {id === "coast" ? <>
      <Ground kind="gravel" x={100} width={250} />
      <mesh position={[-25.3, -.32, 0]}>
        <boxGeometry args={[.85, .64, 145]} />
        <meshStandardMaterial color="#687683" roughness={.92} />
      </mesh>
    </> : id !== "ocean" ? <Ground kind={desert ? "sand" : "gravel"} /> : null}
    {id !== "ocean" ? <mesh receiveShadow position={[0, desert ? -.19 : -.22, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[170, 130]} />
      <shadowMaterial opacity={.29} depthWrite={false} />
    </mesh> : null}
    {desert ? weeds.map((weed, i) => <group key={weed.lane}
      ref={group => { weedGroups.current[i] = group; }}
      position={[116 * weed.phase - 58, -.24 + weed.scale * .85, weed.lane]} scale={weed.scale}>
      <lineSegments geometry={twigs[i]} dispose={null}>
        <lineBasicMaterial color="#754827" />
      </lineSegments>
    </group>) : null}
    {id === "industrial" ? <><IndustrialBackdrop /><Steam material={vapor} /></> : null}
  </>;
}
