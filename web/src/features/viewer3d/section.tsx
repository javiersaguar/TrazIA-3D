"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { useReducedMotion } from "motion/react";
import { Color, DoubleSide, Group, type BufferGeometry, type Plane } from "three";
import { makeSection } from "./section-geometry";
import { BRAND } from "@/lib/brand";
import type { PreparedProduct } from "./model-resource";

const vertexShader = `varying vec2 cutCoord; void main(){vec4 world=modelMatrix*vec4(position,1.);cutCoord=world.xz;gl_Position=projectionMatrix*viewMatrix*world;}`;
const fragmentShader = `uniform vec3 dark;uniform vec3 light;varying vec2 cutCoord; void main(){float stripe=step(.8,fract((cutCoord.x+cutCoord.y)*14.));gl_FragColor=vec4(mix(dark,light,stripe),1.);}`;

export function SectionCaps({ products, height }: { products: PreparedProduct[]; height: number }) {
  const caps = useMemo(() => products.map(product => makeSection(product, height)).filter((geometry): geometry is BufferGeometry => !!geometry), [products, height]);
  useEffect(() => () => { caps.forEach(geometry => geometry.dispose()); }, [caps]);
  return <>{caps.map((geometry, index) => <mesh key={index} geometry={geometry} renderOrder={2}>
    <shaderMaterial vertexShader={vertexShader} fragmentShader={fragmentShader} side={DoubleSide}
      uniforms={{ dark: { value: new Color(BRAND.steelDark) }, light: { value: new Color(BRAND.skyPale) } }} />
  </mesh>)}</>;
}

/** Mueve solo el uniforme; el mallado de sección se calcula una vez al detener el corte. */
export function AnimatedSection({ products, height, plane }: { products: PreparedProduct[]; height: number; plane: Plane }) {
  const invalidate = useThree(s => s.invalidate), reduce = useReducedMotion();
  const caps = useRef<Group>(null);
  const [settled, setSettled] = useState(plane.constant);
  const target = useRef(height);
  useEffect(() => { target.current = height; invalidate(); }, [height, invalidate]);
  useFrame((_, dt) => {
    const distance = target.current - plane.constant;
    if (Math.abs(distance) > 0.0001) {
      plane.setComponents(0, -1, 0, reduce ? target.current : plane.constant + distance * (1 - Math.exp(-26 * Math.min(dt, .05))));
      if (caps.current) caps.current.visible = false;
      invalidate();
    } else {
      plane.setComponents(0, -1, 0, target.current);
      if (caps.current && !caps.current.visible) {
        setSettled(target.current); caps.current.visible = true; invalidate();
      }
    }
  });
  return <group ref={caps}><SectionCaps products={products} height={settled} /></group>;
}
