"use client";

import type { ProcessEnvironmentId } from "./types";

const skies = { ocean: "#779fb7", coast: "#a1bfc8", desert: "#c0afa0", industrial: "#8698a1" };
const vertexShader = `
  varying vec2 ground;
  void main() {
    ground = (modelMatrix * vec4(position, 1.0)).xz;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
const fragmentShader = `
  uniform vec3 base;
  uniform vec3 highlight;
  uniform float water;
  varying vec2 ground;
  void main() {
    vec2 p = ground;
    float noise = fract(sin(dot(floor(p * 13.0), vec2(127.1, 311.7))) * 43758.5453);
    float broad = sin(p.x * 0.18 + sin(p.y * 0.19) * 2.7) * 0.5 + 0.5;
    float wave = sin(p.y * 2.85 + p.x * 0.52 + sin(p.x * 0.75 + p.y * .35) * 1.7);
    float ripples = smoothstep(0.25, 0.92, wave) * smoothstep(.13, .88, broad);
    float micro = 0.5 + 0.5 * sin(p.x * 5.9 + p.y * 4.3 + broad * 7.0);
    float sheen = water > .5 ? .11 * broad + .11 * ripples + .03 * micro : .15 * broad + .14 * noise;
    float farFog = smoothstep(90.0, 220.0, length(p));
    gl_FragColor = vec4(mix(base, highlight, sheen + farFog * 0.57), 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

const materials = {
  water: { base: { value: [.009,.064,.103] }, highlight: { value: [.075,.25,.36] }, water: { value: 1 } },
  sand: { base: { value: [.37,.235,.111] }, highlight: { value: [.70,.51,.29] }, water: { value: 0 } },
  gravel: { base: { value: [.105,.129,.139] }, highlight: { value: [.25,.28,.29] }, water: { value: 0 } },
};

function Ground({ kind, x = 0, elevation = -0.24, width = 450 }: {
  kind: keyof typeof materials; x?: number; elevation?: number; width?: number;
}) {
  return <mesh position={[x, elevation, 0]} rotation={[-Math.PI / 2, 0, 0]}>
    <planeGeometry args={[width, 450]} />
    <shaderMaterial vertexShader={vertexShader} fragmentShader={fragmentShader} uniforms={materials[kind]} />
  </mesh>;
}

const dunes = [
  [-67,-43,43,4.6,15], [-14,-60,55,6,20], [49,-48,34,5.5,12],
  [75,-31,31,3.9,16], [-68,21,23,3.1,42], [84,36,41,5.1,24],
] as const;
const buildings = [
  [-54,-46,15,8,20], [-35,-55,14,6,13], [4,-55,25,10,14], [28,-45,15,6,20], [52,-37,17,8,18],
] as const;

export function ProcessEnvironment({ id }: { id: ProcessEnvironmentId }) {
  return <>
    <color attach="background" args={[skies[id]]} />
    {id === "coast" ? <>
      <Ground kind="water" x={-115} width={180} elevation={-0.48} />
      <Ground kind="gravel" x={100} width={250} />
      <mesh position={[-25.3, -0.32, 0]}>
        <boxGeometry args={[0.65, 0.48, 145]} />
        <meshStandardMaterial color="#687683" roughness={0.92} />
      </mesh>
    </> : <Ground kind={id === "ocean" ? "water" : id === "desert" ? "sand" : "gravel"} />}
    <mesh receiveShadow position={[0, id === "coast" ? -.22 : -.23, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[170, 130]} />
      <shadowMaterial opacity={0.32} depthWrite={false} />
    </mesh>
    {id === "desert" ? dunes.map(([x,z,w,h,d]) => <mesh key={x} position={[x,-1.8,z]} scale={[w,h,d]} rotation={[0,0.23,0]}>
      <sphereGeometry args={[1, 22, 9]} />
      <meshStandardMaterial color="#b18755" roughness={1} />
    </mesh>) : null}
    {id === "industrial" ? buildings.map(([x,z,w,h,d]) => <group key={x} position={[x,0,z]}>
      <mesh position={[0,h/2,0]}>
        <boxGeometry args={[w,h,d]} />
        <meshStandardMaterial color="#57666d" roughness={0.94} />
      </mesh>
      <mesh position={[0,h+.26,0]}>
        <boxGeometry args={[w+.45,.52,d+.45]} />
        <meshStandardMaterial color="#839098" roughness={0.87} />
      </mesh>
      <mesh position={[w*.37,h*.99,0]}>
        <cylinderGeometry args={[.53,.83,h*1.35,12]} />
        <meshStandardMaterial color="#73838c" roughness={.8} />
      </mesh>
    </group>) : null}
  </>;
}
