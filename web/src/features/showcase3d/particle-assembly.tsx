"use client";

import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import { BufferAttribute, BufferGeometry, Color, ShaderMaterial, type Group } from "three";
import { BRAND } from "@/lib/brand";
import { AssemblyMeshes } from "./assembly-meshes";
import type { EquipmentGeometry } from "./equipment-geometry";
import { sampleSurface, scatterSurface } from "./surface-sampling";

const vertexShader = `
  attribute vec3 aFrom; uniform float uProgress; uniform float uPixelRatio;
  varying float vAlpha;
  void main() {
    float t = smoothstep(0., 1., uProgress);
    vec3 p = mix(aFrom, position, t);
    p.x += sin(position.y * 3. + t * 6.283) * sin(t * 3.14159) * .2;
    vec4 mv = modelViewMatrix * vec4(p, 1.);
    gl_Position = projectionMatrix * mv;
    gl_PointSize = 1.7 * uPixelRatio;
    vAlpha = .35 + t * .65;
  }`;
const fragmentShader = `
  uniform vec3 uColor; varying float vAlpha;
  void main() {
    float d = length(gl_PointCoord - .5);
    if (d > .5) discard;
    gl_FragColor = vec4(uColor, (1. - smoothstep(.1, .5, d)) * vAlpha);
  }`;

export function ParticleAssembly({ model, reduce }: { model: EquipmentGeometry; reduce: boolean }) {
  const invalidate = useThree(s => s.invalidate), gl = useThree(s => s.gl);
  const physical = useRef<Group>(null);
  const geometry = useMemo(() => new BufferGeometry(), []);
  const material = useMemo(() => new ShaderMaterial({
    vertexShader, fragmentShader, transparent: true, depthWrite: false,
    uniforms: { uColor: { value: new Color(BRAND.skyLight) }, uProgress: { value: 0 }, uPixelRatio: { value: 1 } },
  }), []);
  const state = useRef({ from: new Float32Array(), to: new Float32Array(), progress: 0, started: 0, intro: true });
  const lastModel = useRef<EquipmentGeometry | null>(null);
  useEffect(() => {
    if (lastModel.current === model) { if (reduce) state.current.progress = 1; invalidate(); return; }
    lastModel.current = model;
    const to = sampleSurface(model), previous = state.current;
    const from = previous.to.length === to.length ? new Float32Array(to.length) : scatterSurface(to);
    if (previous.to.length === to.length) {
      const t = previous.progress * previous.progress * (3 - 2 * previous.progress);
      for (let i = 0; i < from.length; i++) {
        from[i] = previous.from[i]! * (1 - t) + previous.to[i]! * t;
        if (i % 3 === 0) from[i] = from[i]! + Math.sin(previous.to[i + 1]! * 3 + t * 6.283) * Math.sin(t * 3.14159) * .2;
      }
    }
    geometry.setAttribute("position", new BufferAttribute(to, 3));
    geometry.setAttribute("aFrom", new BufferAttribute(from, 3));
    geometry.computeBoundingSphere();
    state.current = { from, to, progress: reduce ? 1 : 0, started: performance.now(), intro: previous.to.length === 0 };
    invalidate();
  }, [model, reduce, geometry, invalidate]);
  useEffect(() => () => { geometry.dispose(); material.dispose(); }, [geometry, material]);
  const points = useRef<import("three").Points>(null);
  useFrame((_, delta) => {
    const s = state.current;
    if (!s.to.length) { if (physical.current) physical.current.visible = false; if (points.current) points.current.visible = false; return; }
    s.progress = reduce ? 1 : Math.min(1, s.progress + Math.min(delta, .05) / (s.intro ? 1.25 : .65));
    const current = points.current?.material as ShaderMaterial | undefined;
    if (current) { current.uniforms.uProgress!.value = s.progress; current.uniforms.uPixelRatio!.value = gl.getPixelRatio(); }
    if (physical.current) physical.current.visible = s.progress >= .995;
    if (points.current) points.current.visible = s.progress < 1;
    if (s.progress < 1) invalidate();
  });
  return <>
    <points ref={points} geometry={geometry} material={material} frustumCulled={false} dispose={null} />
    <AssemblyMeshes key={model.kind} model={model} groupRef={physical} />
  </>;
}
