"use client";

import { useEffect, useMemo } from "react";
import { BufferAttribute, BufferGeometry, Color, ShaderMaterial } from "three";
import { BRAND } from "@/lib/brand";
import { randomSequence } from "../showcase3d/surface-sampling";

export function createFlow(from: number, to: number, height: number) {
  const geometry = new BufferGeometry(), random = randomSequence(81), data = new Float32Array(1000 * 3);
  for (let i = 0; i < data.length; i += 3) { data[i] = random(); data[i + 1] = random() - .5; data[i + 2] = random() - .5; }
  geometry.setAttribute("position", new BufferAttribute(data, 3));
  const material = new ShaderMaterial({ transparent: true, depthWrite: false,
    uniforms: { uTime: { value: 0 }, uProgress: { value: 0 }, uColor: { value: new Color(BRAND.skyLight) } },
    vertexShader: `uniform float uTime; varying float vAlpha;
      void main() {
        float t = fract(position.x + uTime * .35);
        vec3 p = vec3(mix(${from.toFixed(4)}, ${to.toFixed(4)}, t), ${height.toFixed(4)} + position.y * sin(t * 3.14159) * 1.3, position.z * .5);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.);
        gl_PointSize = 2.; vAlpha = sin(t * 3.14159);
      }`,
    fragmentShader: `uniform vec3 uColor; uniform float uProgress; varying float vAlpha;
      void main() { gl_FragColor = vec4(uColor, vAlpha * sin(uProgress * 3.14159) * .7); }`,
  });
  return { geometry, material };
}

export function ParticleFlow({ from, to, height, register }: {
  from: number; to: number; height: number; register(material: ShaderMaterial | null): void;
}) {
  const flow = useMemo(() => createFlow(from, to, height), [from, to, height]);
  useEffect(() => { register(flow.material); return () => { register(null); flow.geometry.dispose(); flow.material.dispose(); }; }, [flow, register]);
  return <points geometry={flow.geometry} material={flow.material} frustumCulled={false} dispose={null} />;
}
