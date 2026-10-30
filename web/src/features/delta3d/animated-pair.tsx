"use client";

import { Edges } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import {
  BufferGeometry,
  Float32BufferAttribute,
  Group,
  MeshPhysicalMaterial,
  Points,
  ShaderMaterial,
  Color,
} from "three";
import { MeshSurfaceSampler } from "three/addons/math/MeshSurfaceSampler.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { Mesh, Vector3 } from "three";
import { BRAND } from "@/lib/brand";
import { createRevealSurface } from "../hologram/materials";
import {
  brushedTextures,
  retainBrushedTextures,
} from "../viewer3d/brushed-textures";
import type { PreparedProduct } from "../viewer3d/model-resource";
import { morphState, segmentProgress, timelineAt, type Pair } from "./morph";

export type TimelineSnapshot = {
  value: number;
  playing: boolean;
  speed: number;
};

function Dissolve({
  product,
  read,
  index,
  count,
}: {
  product: PreparedProduct;
  read(): TimelineSnapshot;
  index: number;
  count: number;
}) {
  const points = useRef<Points>(null);
  const assets = useMemo(() => {
    const copies = product.geometries.map((g) =>
      g.index ? g.toNonIndexed() : g.clone(),
    );
    const merged = mergeGeometries(copies);
    copies.forEach((g) => g.dispose());
    const sampleMesh = new Mesh(merged),
      sampler = new MeshSurfaceSampler(sampleMesh).build();
    const positions = new Float32Array(768 * 3),
      p = new Vector3();
    for (let i = 0; i < 768; i++) {
      sampler.sample(p);
      p.toArray(positions, i * 3);
    }
    merged.dispose();
    [sampleMesh.material].flat().forEach((m) => m.dispose());
    const geometry = new BufferGeometry();
    geometry.setAttribute("position", new Float32BufferAttribute(positions, 3));
    const material = new ShaderMaterial({
      transparent: true,
      depthWrite: false,
      uniforms: {
        uT: { value: 0 },
        uColor: { value: new Color(BRAND.danger) },
      },
      vertexShader: `uniform float uT; varying float vAlpha; void main() {
        vec3 p = position + normalize(position + vec3(.17,.31,.23)) * uT * 1.4;
        p.y += uT * uT; vAlpha = sin(uT * 3.14159) * (1.-uT);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(p,1.); gl_PointSize = 2.; }`,
      fragmentShader: `uniform vec3 uColor; varying float vAlpha; void main() {
        if (length(gl_PointCoord-.5)>.5) discard; gl_FragColor=vec4(uColor,vAlpha);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
    });
    return { geometry, material };
  }, [product]);
  useEffect(
    () => () => {
      assets.geometry.dispose();
      assets.material.dispose();
    },
    [assets],
  );
  useFrame(() => {
    const t = segmentProgress(read().value, index, count),
      mesh = points.current;
    if (mesh) {
      mesh.visible = t > 0 && t < 1;
      (mesh.material as ShaderMaterial).uniforms.uT!.value = t;
    }
  });
  return (
    <points
      ref={points}
      geometry={assets.geometry}
      material={assets.material}
      position={product.center}
      dispose={null}
    />
  );
}

export function AnimatedPair({
  pair,
  index,
  count,
  changed,
  selected,
  hovered,
  read,
  onSelect,
  onHover,
}: {
  pair: Pair<PreparedProduct>;
  index: number;
  count: number;
  changed: boolean;
  selected: boolean;
  hovered: boolean;
  read(): TimelineSnapshot;
  onSelect(id: string): void;
  onHover(id: string | null): void;
}) {
  const source = useRef<Group>(null),
    target = useRef<Group>(null),
    ring = useRef<Mesh>(null);
  const product = (pair.after ?? pair.before)!;
  const assets = useMemo(
    () => ({
      source: new MeshPhysicalMaterial({
        color: BRAND.steel,
        metalness: 0.85,
        roughness: 0.34,
        clearcoat: 0.2,
        transparent: true,
        ...brushedTextures(),
      }),
      target: createRevealSurface(product.bounds.min[1], product.bounds.max[1]),
    }),
    [product],
  );
  const owned = useRef<typeof assets | null>(null);
  useEffect(() => {
    owned.current = assets;
    const release = retainBrushedTextures();
    return () => {
      assets.source.dispose();
      assets.target.material.dispose();
      release();
    };
  }, [assets]);
  useFrame(() => {
    const resource = owned.current;
    if (!resource) return;
    const progress = read().value,
      t = changed ? segmentProgress(progress, index, count) : progress;
    const state = morphState(pair, t),
      active =
        timelineAt(progress, count).index === index &&
        progress > 0 &&
        progress < 1;
    const pulse = active
      ? Math.sin(timelineAt(progress, count).phase * Math.PI) ** 2
      : 0;
    const bounce =
      1 +
      (active ? Math.sin(t * Math.PI) * Math.sin(t * Math.PI * 3) * 0.018 : 0);
    if (source.current) {
      source.current.visible = state.sourceOpacity > 0.001;
      source.current.position.set(...state.position);
      source.current.scale.set(...state.scale).multiplyScalar(bounce);
    }
    if (target.current)
      target.current.visible = pair.before
        ? state.targetOpacity > 0.001
        : t > 0;
    resource.source.opacity = state.sourceOpacity;
    resource.source.depthWrite = state.sourceOpacity > 0.99;
    resource.source.color.set(
      changed && t > 0.8 ? BRAND.revision : BRAND.steel,
    );
    resource.source.emissive.set(
      active || hovered || selected ? BRAND.revision : BRAND.black,
    );
    resource.source.emissiveIntensity =
      pulse * 0.35 + (hovered ? 0.1 : selected ? 0.04 : 0);
    resource.target.uniforms.uReveal.value = pair.before ? 1 : t;
    resource.target.material.opacity = pair.before ? state.targetOpacity : 1;
    resource.target.material.transparent = pair.before !== null;
    resource.target.material.color.set(changed ? BRAND.revision : BRAND.steel);
    if (ring.current) {
      ring.current.visible = active && t > 0 && t < 1;
      ring.current.position.y =
        product.bounds.min[1] +
        (product.bounds.max[1] - product.bounds.min[1]) * t;
    }
  });
  const click = () => onSelect(product.semanticId);
  const radius =
    Math.max(
      product.bounds.max[0] - product.bounds.min[0],
      product.bounds.max[2] - product.bounds.min[2],
    ) * 0.6;
  return (
    <group
      dispose={null}
      onPointerOver={(e) => {
        e.stopPropagation();
        onHover(product.semanticId);
      }}
      onPointerOut={() => onHover(null)}
    >
      {pair.before ? (
        <group
          ref={source}
          position={pair.before.center}
          onClick={(e) => {
            e.stopPropagation();
            click();
          }}
        >
          {pair.before.geometries.map((g, i) => (
            <mesh key={i} geometry={g} material={assets.source}>
              {selected || hovered ? (
                <Edges color={BRAND.revision} threshold={20} />
              ) : null}
            </mesh>
          ))}
        </group>
      ) : null}
      {pair.after ? (
        <group
          ref={target}
          position={pair.after.center}
          onClick={(e) => {
            e.stopPropagation();
            click();
          }}
        >
          {pair.after.geometries.map((g, i) => (
            <mesh key={i} geometry={g} material={assets.target.material}>
              {selected || hovered ? (
                <Edges color={BRAND.revision} threshold={20} />
              ) : null}
            </mesh>
          ))}
        </group>
      ) : pair.before ? (
        <Dissolve
          product={pair.before}
          index={index}
          count={count}
          read={read}
        />
      ) : null}
      {changed ? (
        <mesh
          ref={ring}
          position={[product.center[0], product.center[1], product.center[2]]}
          rotation={[Math.PI / 2, 0, 0]}
        >
          <torusGeometry args={[Math.max(0.1, radius), 0.013, 6, 64]} />
          <meshBasicMaterial
            color={BRAND.revision}
            transparent
            opacity={0.85}
            depthWrite={false}
          />
        </mesh>
      ) : null}
    </group>
  );
}
