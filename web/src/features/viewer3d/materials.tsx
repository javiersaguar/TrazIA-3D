"use client";

import { animated } from "@react-spring/three";
import type { ThreeElements } from "@react-three/fiber";
import { useEffect, useRef, type ComponentProps } from "react";
import type { MeshBasicMaterial, MeshStandardMaterial } from "three";

// Las geometrías se comparten entre instancias; cada material conserva su propio ciclo de vida.
export function SteelMaterial(props: ComponentProps<typeof animated.meshStandardMaterial>) {
  const ref = useRef<MeshStandardMaterial>(null);
  useEffect(() => { const material = ref.current; return () => material?.dispose(); }, []);
  return <animated.meshStandardMaterial {...props} ref={ref} />;
}

export function BasicMaterial(props: ThreeElements["meshBasicMaterial"]) {
  const ref = useRef<MeshBasicMaterial>(null);
  useEffect(() => { const material = ref.current; return () => material?.dispose(); }, []);
  return <meshBasicMaterial {...props} ref={ref} />;
}
