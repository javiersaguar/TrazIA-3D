"use client";

import { useEffect, useLayoutEffect, useRef, type Ref } from "react";
import { type Group, type InstancedMesh, type Material } from "three";
import { BoltMaterial, MachinedFace, PaintedSteel, SteelMaterial } from "../viewer3d/materials";
import type { EquipmentGeometry, Finish } from "./equipment-geometry";

function FinishMaterial({ finish }: { finish: Finish }) {
  if (finish === "paint") return <PaintedSteel />;
  if (finish === "machined") return <MachinedFace />;
  if (finish === "bolts") return <BoltMaterial />;
  return <SteelMaterial />;
}

export function AssemblyMeshes({ model, material, groupRef }: {
  model: EquipmentGeometry; material?: Material; groupRef?: Ref<Group>;
}) {
  const bolts = useRef<InstancedMesh>(null);
  useLayoutEffect(() => {
    if (!bolts.current) return;
    model.bolts.forEach((matrix, i) => bolts.current!.setMatrixAt(i, matrix));
    bolts.current.instanceMatrix.needsUpdate = true;
    bolts.current.computeBoundingSphere();
  }, [model]);
  useEffect(() => { const mesh = bolts.current; return () => mesh?.dispose(); }, [model]);
  return <group ref={groupRef} dispose={null}>
    {model.batches.map(batch => <mesh key={batch.finish} geometry={batch.geometry} material={material} castShadow receiveShadow>
      {!material ? <FinishMaterial finish={batch.finish} /> : null}
    </mesh>)}
    <instancedMesh ref={bolts} args={[model.boltGeometry, undefined, model.bolts.length]} material={material} castShadow>
      {!material ? <BoltMaterial /> : null}
    </instancedMesh>
  </group>;
}
