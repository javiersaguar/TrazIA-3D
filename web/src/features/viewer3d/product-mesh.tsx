"use client";

import { Edges } from "@react-three/drei";
import { animated, config, useSpring } from "@react-spring/three";
import type { ThreeEvent } from "@react-three/fiber";
import { useReducedMotion } from "motion/react";
import { BackSide, type Plane } from "three";
import { acceleratedRaycast } from "three-mesh-bvh";
import type { Vec3 } from "@/workers/ifc-protocol";
import type { PreparedProduct } from "./model-resource";
import { BasicMaterial, SteelMaterial } from "./materials";

export type ElementState = "draft" | "approved" | "assumed" | "changed" | "conflict";
export const STATE_COLORS: Record<ElementState, string> = {
  draft: "#a1b4c4", approved: "#5cc08f", assumed: "#86aee8", changed: "#f5a35c", conflict: "#f07468",
};

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
  const activeColor = selected ? "#b8d6ff" : hovered ? "#93b7e6" : tint;
  const click = (event: ThreeEvent<MouseEvent>) => { event.stopPropagation(); onSelect?.(product.semanticId); };
  const over = (event: ThreeEvent<PointerEvent>) => { event.stopPropagation(); onHover?.(product.semanticId); };
  const focus = (event: ThreeEvent<MouseEvent>) => { event.stopPropagation(); onFocus?.(product.semanticId); };
  return <animated.group position-x={spring.px} position-y={spring.py} position-z={spring.pz}
    scale-x={spring.sx} scale-y={spring.sy} scale-z={spring.sz} dispose={null}>
    {product.geometries.map((geometry, i) => <mesh key={i} geometry={geometry} raycast={acceleratedRaycast}
      onClick={click} onPointerOver={over} onPointerOut={() => onHover?.(null)} onDoubleClick={focus}>
      <SteelMaterial color={activeColor} metalness={wireframe ? 0 : .55} roughness={.45}
        transparent opacity={spring.opacity} depthWrite={mode !== "xray" && opacity >= .99}
        wireframe={wireframe || state === "assumed"} clippingPlanes={planes ?? []} />
      {selected || hovered ? <Edges threshold={20} color={selected ? "#b8d6ff" : "#86aee8"} lineWidth={1.2} /> : null}
    </mesh>)}
    {selected ? product.geometries.map((geometry, i) => <mesh key={`outline-${i}`} geometry={geometry} scale={1.018} raycast={() => null}>
      <BasicMaterial side={BackSide} color="#9fc7ff" transparent opacity={.8} depthWrite={false} clippingPlanes={planes ?? []} />
    </mesh>) : null}
    {product.semanticId.startsWith("nozzle:") && onSelect && !wireframe && opacity > .05 ?
      <mesh onClick={click} onPointerOver={over} onPointerOut={() => onHover?.(null)} onDoubleClick={focus}>
        <sphereGeometry args={[Math.max(.2, (product.bounds.max[1] - product.bounds.min[1]) * .8), 10, 8]} />
        <BasicMaterial transparent opacity={0} colorWrite={false} depthWrite={false} />
      </mesh> : null}
  </animated.group>;
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
