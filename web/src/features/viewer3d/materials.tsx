"use client";

import { animated, type SpringValue } from "@react-spring/three";
import type { ThreeElements } from "@react-three/fiber";
import { useEffect, useMemo, useRef, type ComponentType, type Ref } from "react";
import type { MeshBasicMaterial, MeshPhysicalMaterial } from "three";
import { BRAND } from "@/lib/brand";
import { brushedTextures, retainBrushedTextures } from "./brushed-textures";

type PhysicalProps = Pick<ThreeElements["meshPhysicalMaterial"],
  "metalness" | "roughness" | "clearcoat" | "clearcoatRoughness" | "normalMap" |
  "roughnessMap" | "normalScale" | "anisotropy" | "transparent" | "depthWrite" |
  "depthTest" | "wireframe" | "clippingPlanes" | "side" | "emissive" |
  "emissiveIntensity" | "toneMapped"> & {
  color?: string | SpringValue<string>;
  opacity?: number | SpringValue<number>;
};
// Limita la API animada a propiedades de superficie; evita expandir recursivamente toda Texture.
const AnimatedPhysical = animated.meshPhysicalMaterial as unknown as ComponentType<PhysicalProps & { ref?: Ref<MeshPhysicalMaterial> }>;

// Las geometrías se comparten entre instancias; cada material conserva su propio ciclo de vida.
export function SteelMaterial(props: PhysicalProps) {
  const ref = useRef<MeshPhysicalMaterial>(null);
  const maps = useMemo(() => brushedTextures(), []);
  useEffect(retainBrushedTextures, []);
  useEffect(() => { const material = ref.current; return () => material?.dispose(); }, []);
  return <AnimatedPhysical color={BRAND.steel} metalness={.85} roughness={.34}
    clearcoat={.2} clearcoatRoughness={.28} normalScale={[.09, .16]} {...maps} {...props} ref={ref} />;
}

export function PaintedSteel(props: PhysicalProps) {
  return <SteelMaterial color={BRAND.paint} metalness={.5} roughness={.55} clearcoat={.12} {...props} />;
}

export function MachinedFace(props: PhysicalProps) {
  return <SteelMaterial color={BRAND.steel} metalness={.93} roughness={.2}
    anisotropy={.75} clearcoat={.25} normalScale={[.04, .12]} {...props} />;
}

export function BoltMaterial(props: PhysicalProps) {
  return <SteelMaterial color={BRAND.steelDark} metalness={.9} roughness={.28}
    normalScale={[.03, .03]} {...props} />;
}

export function BasicMaterial(props: ThreeElements["meshBasicMaterial"]) {
  const ref = useRef<MeshBasicMaterial>(null);
  useEffect(() => { const material = ref.current; return () => material?.dispose(); }, []);
  return <meshBasicMaterial {...props} ref={ref} />;
}
