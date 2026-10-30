"use client";

import { BRAND } from "@/lib/brand";

import { Select } from "@react-three/postprocessing";
import { Edges } from "@react-three/drei";
import { animated, config, useSpring } from "@react-spring/three";
import { useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import { useReducedMotion } from "motion/react";
import { useEffect, useMemo, useRef } from "react";
import { BackSide, Mesh, OrthographicCamera, SphereGeometry, type Plane } from "three";
import { acceleratedRaycast } from "three-mesh-bvh";
import type { Vec3 } from "@/workers/ifc-protocol";
import type { PreparedProduct } from "./model-resource";
import { BasicMaterial, SteelMaterial } from "./materials";

export type ElementState = "draft" | "approved" | "assumed" | "changed" | "conflict";
export const STATE_COLORS: Record<ElementState, string> = {
  draft: BRAND.steel, approved: BRAND.approved, assumed: BRAND.skyLight, changed: BRAND.revision, conflict: BRAND.danger,
};

function HitTarget({ radius, onClick, onOver, onOut, onFocus }: { radius: number;
  onClick(event: ThreeEvent<MouseEvent>): void; onOver(event: ThreeEvent<PointerEvent>): void;
  onOut(): void; onFocus(event: ThreeEvent<MouseEvent>): void;
}) {
  const ref = useRef<Mesh>(null), camera = useThree(state => state.camera);
  const geometry = useMemo(() => new SphereGeometry(1, 10, 8), []);
  useEffect(() => () => geometry.dispose(), [geometry]);
  useFrame(() => { ref.current?.scale.setScalar(Math.max(radius, camera instanceof OrthographicCamera ? 12 / camera.zoom : radius)); });
  return <mesh ref={ref} geometry={geometry} scale={radius} dispose={null} onClick={onClick}
    onPointerOver={onOver} onPointerOut={onOut} onDoubleClick={onFocus}>
    <BasicMaterial transparent opacity={0} colorWrite={false} depthWrite={false} />
  </mesh>;
}

export function ProductMesh({ product, position = product.center, scale = [1, 1, 1], opacity = 1,
  selected = false, hovered = false, state = "draft", mode = "solid", planes, wireframe = false,
  immediate = false, onSelect, onHover, onFocus, color }: {
  product: PreparedProduct; position?: Vec3; scale?: Vec3; opacity?: number; selected?: boolean;
  hovered?: boolean; state?: ElementState; mode?: "solid" | "xray" | "exploded"; planes?: Plane[];
  wireframe?: boolean; immediate?: boolean; color?: string;
  onSelect?(id: string): void; onHover?(id: string | null): void; onFocus?(id: string): void;
}) {
  const reduced = useReducedMotion();
  const spring = useSpring({ px: position[0], py: position[1], pz: position[2], sx: scale[0], sy: scale[1], sz: scale[2], opacity: mode === "xray" ? opacity * .22 : opacity,
    immediate: immediate || !!reduced, config: config.default });
  const tint = color ?? STATE_COLORS[state];
  const activeColor = tint;
  const click = (event: ThreeEvent<MouseEvent>) => { event.stopPropagation(); onSelect?.(product.semanticId); };
  const over = (event: ThreeEvent<PointerEvent>) => { event.stopPropagation(); onHover?.(product.semanticId); };
  const focus = (event: ThreeEvent<MouseEvent>) => { event.stopPropagation(); onFocus?.(product.semanticId); };
  const interactive = opacity > .05 && !wireframe && !!onSelect;
  return <Select enabled={selected || hovered}><animated.group position-x={spring.px} position-y={spring.py} position-z={spring.pz}
    scale-x={spring.sx} scale-y={spring.sy} scale-z={spring.sz} dispose={null}>
    {product.geometries.map((geometry, i) => <mesh key={i} geometry={geometry} raycast={acceleratedRaycast}
      onClick={interactive ? click : undefined} onPointerOver={interactive ? over : undefined}
      onPointerOut={interactive ? () => onHover?.(null) : undefined} onDoubleClick={interactive ? focus : undefined}>
      <SteelMaterial color={activeColor} metalness={wireframe ? 0 : .85} roughness={.34} emissive={selected || hovered ? BRAND.sky : BRAND.black} emissiveIntensity={selected ? .12 : hovered ? .04 : 0}
        transparent opacity={spring.opacity} depthWrite={mode !== "xray" && opacity >= .99}
        wireframe={wireframe || state === "assumed"} clippingPlanes={planes ?? []} />
      {(selected || hovered) && opacity > .01 ? <Edges threshold={20} color={selected ? BRAND.skyPale : BRAND.skyLight} lineWidth={1.2} /> : null}
    </mesh>)}
    {selected && opacity > .01 ? product.geometries.map((geometry, i) => <mesh key={`outline-${i}`} geometry={geometry} scale={1.018} raycast={() => null}>
      <BasicMaterial side={BackSide} color={BRAND.skyPale} transparent opacity={.8} depthWrite={false} clippingPlanes={planes ?? []} />
    </mesh>) : null}
    {product.semanticId.startsWith("nozzle:") && interactive ? <HitTarget
      radius={Math.max(.15, (product.bounds.max[1] - product.bounds.min[1]) * .8)} onClick={click}
      onOver={over} onOut={() => onHover?.(null)} onFocus={focus} /> : null}
  </animated.group></Select>;
}

export function explosionOffset(product: PreparedProduct, amount: number): Vec3 {
  const id = product.semanticId;
  if (id === "head-top") return [0, amount * 1.5, 0];
  if (id === "head-bottom") return [0, -amount * .9, 0];
  if (id === "skirt") return [0, -amount * 2, 0];
  if (id.startsWith("nozzle:")) {
    const length = Math.hypot(product.center[0], product.center[2]) || 1;
    return [product.center[0] / length * amount * 1.5, 0, product.center[2] / length * amount * 1.5];
  }
  return [0, 0, 0];
}
