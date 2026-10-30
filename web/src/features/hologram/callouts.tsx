"use client";

import {
  Billboard,
  Line,
  PerspectiveCamera,
  RenderTexture,
} from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import { useLayoutEffect, useRef, type ReactNode } from "react";
import { type PerspectiveCamera as Camera, type Group, Vector3 } from "three";
import { BRAND } from "@/lib/brand";
import { SceneLabel } from "../viewer3d/stage";

export type DetailAnchor = {
  name: string;
  point: Vector3;
  distance: number;
  normal?: [number, number, number];
};

function DetailCamera({ anchor }: { anchor: DetailAnchor }) {
  const camera = useRef<Camera>(null);
  useLayoutEffect(() => {
    camera.current?.lookAt(anchor.point);
    camera.current?.updateProjectionMatrix();
  }, [anchor]);
  const eye = anchor.point
    .clone()
    .addScaledVector(
      new Vector3(...(anchor.normal ?? [0, 0.08, 1])).normalize(),
      anchor.distance,
    );
  return (
    <PerspectiveCamera
      ref={camera}
      makeDefault
      fov={35}
      aspect={1}
      near={0.01}
      far={100}
      position={eye}
    />
  );
}

function EnvironmentLink({ scene }: { scene: import("three").Scene }) {
  useFrame(({ scene: target }) => {
    target.environment = scene.environment;
  });
  return null;
}

export function DetailCallouts({
  anchors,
  offset,
  column,
  height,
  children,
  reduce,
}: {
  anchors: DetailAnchor[];
  offset: number;
  column: number;
  height: number;
  children: ReactNode;
  reduce: boolean;
}) {
  const scene = useThree((s) => s.scene),
    invalidate = useThree((s) => s.invalidate);
  const group = useRef<Group>(null),
    enter = useRef(0);
  useFrame((_, delta) => {
    enter.current = reduce ? 1 : Math.min(1, enter.current + delta / 0.24);
    group.current?.scale.setScalar(0.96 + enter.current * 0.04);
    if (enter.current < 1) invalidate();
  });
  return (
    <group ref={group}>
      {anchors.map((anchor, index) => {
        const center: [number, number, number] = [
          column,
          height * (0.82 - index * 0.3),
          0,
        ];
        const source = anchor.point.clone().add(new Vector3(offset, 0, 0));
        return (
          <group key={anchor.name}>
            <Line
              points={[source, [column - 0.65, center[1], 0]]}
              color={BRAND.revision}
              lineWidth={1}
              transparent
              opacity={0.7}
            />
            <Billboard position={center}>
              <mesh>
                <circleGeometry args={[0.62, 64]} />
                <meshBasicMaterial>
                  <RenderTexture
                    attach="map"
                    width={256}
                    height={256}
                    frames={2}
                  >
                    <color attach="background" args={[BRAND.black]} />
                    <DetailCamera anchor={anchor} />
                    <EnvironmentLink scene={scene} />
                    <ambientLight intensity={0.5} color={BRAND.text} />
                    <directionalLight
                      intensity={3}
                      position={[4, 8, 6]}
                      color={BRAND.text}
                    />
                    {children}
                  </RenderTexture>
                </meshBasicMaterial>
              </mesh>
              <mesh position={[0, 0, 0.006]}>
                <torusGeometry args={[0.64, 0.013, 8, 64]} />
                <meshBasicMaterial color={BRAND.revision} toneMapped={false} />
              </mesh>
            </Billboard>
            <SceneLabel
              position={[column, center[1] - 0.8, 0]}
              center
              style={{
                pointerEvents: "none",
                color: BRAND.textMuted,
                fontSize: 10,
                whiteSpace: "nowrap",
              }}
            >
              {anchor.name}
            </SceneLabel>
          </group>
        );
      })}
    </group>
  );
}
