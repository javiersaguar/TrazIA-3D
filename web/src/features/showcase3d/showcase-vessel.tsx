"use client";

import Image from "next/image";
import { useFrame, useThree } from "@react-three/fiber";
import { useReducedMotion } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { CameraRig, SceneCanvas, Studio, type CameraHandle, type PerformanceSample } from "../viewer3d/stage";
import { AssemblyMeshes } from "./assembly-meshes";
import { equipmentGeometry, retainEquipment, type EquipmentKind } from "./equipment-geometry";
import { createHologram } from "../hologram/materials";
import { ParticleAssembly } from "./particle-assembly";
import styles from "./showcase.module.css";

export type { EquipmentKind } from "./equipment-geometry";
export const EQUIPMENT_KINDS: EquipmentKind[] = ["vertical", "horizontal", "column", "exchanger", "tank"];
export const EQUIPMENT_LABELS: Record<EquipmentKind, string> = {
  vertical: "Recipiente vertical", horizontal: "Recipiente horizontal", column: "Columna",
  exchanger: "Intercambiador", tank: "Tanque atmosférico",
};
export type ShowcaseVesselProps = {
  kind?: EquipmentKind; mode?: "particles" | "hologram" | "real"; interactive?: boolean;
  onKindChange?(kind: EquipmentKind): void; hud?: boolean; className?: string;
  measureKey?: number; onMeasure?(sample: PerformanceSample): void;
};
export type EquipmentThumbProps = { kind: EquipmentKind; size?: number };

function Bearing({ onChange }: { onChange(value: string): void }) {
  const previous = useRef(-1), elapsed = useRef(0);
  useFrame(({ camera }, delta) => {
    elapsed.current += delta;
    if (elapsed.current < .12) return;
    elapsed.current = 0;
    const bearing = Math.round((Math.atan2(camera.position.x, camera.position.z) * 180 / Math.PI + 360) % 360);
    if (bearing !== previous.current) onChange( `N ${String(bearing).padStart(3, "0")}°`);
    previous.current = bearing;
  });
  return null;
}

function EquipmentScene({ kind, mode, interactive, onBearing, measureKey, onMeasure }: {
  kind: EquipmentKind; mode: "particles" | "hologram" | "real"; interactive: boolean;
  onBearing(value: string): void; measureKey?: number; onMeasure?(sample: PerformanceSample): void;
}) {
  const model = useMemo(() => equipmentGeometry(kind), [kind]);
  useEffect(() => retainEquipment(kind), [kind]);
  const reduce = useReducedMotion();
  const camera = useRef<CameraHandle>(null);
  const bounds = useMemo(() => ({ min: model.bounds.min.toArray() as [number,number,number], max: model.bounds.max.toArray() as [number,number,number] }), [model]);
  const hologram = useMemo(() => createHologram(model.bounds.min.y, model.bounds.max.y), [model]);
  const shader = useRef<typeof hologram | null>(null), invalidate = useThree(s => s.invalidate);
  useEffect(() => { shader.current = hologram; }, [hologram]);
  useFrame((_, delta) => {
    const material = shader.current;
    if (mode !== "hologram" || !material) return;
    material.uniforms.uTime!.value = reduce ? 0 : Number(material.uniforms.uTime!.value) + Math.min(delta, .05);
    if (!reduce) invalidate();
  });
  useEffect(() => () => hologram.dispose(), [hologram]);
  return <>
    <Studio />
    <CameraRig bounds={bounds} handle={camera} interactive={interactive} measureKey={measureKey} onMeasure={onMeasure} />
    <Bearing onChange={onBearing} />
    {mode === "particles" ? <ParticleAssembly model={model} reduce={!!reduce} /> :
      <AssemblyMeshes key={kind} model={model} material={mode === "hologram" ? hologram : undefined} />}
  </>;
}

export function ShowcaseVessel({ kind, mode = "real", interactive = true, onKindChange, hud = true, className, measureKey, onMeasure }: ShowcaseVesselProps) {
  const [localKind, setKind] = useState<EquipmentKind>("vertical");
  const current = kind ?? localKind;
  const bearing = useRef<HTMLSpanElement>(null), pointer = useRef({ x: 0, y: 0 });
  const select = (next: EquipmentKind) => { setKind(next); onKindChange?.(next); };
  return <div className={cn(styles.root, className)} data-equipment-kind={current} data-mode={mode}>
    <div className={styles.canvas} onPointerDown={e => { pointer.current = { x: e.clientX, y: e.clientY }; }}
      onPointerUp={e => {
        if (interactive && Math.hypot(e.clientX - pointer.current.x, e.clientY - pointer.current.y) < 4) select(EQUIPMENT_KINDS[(EQUIPMENT_KINDS.indexOf(current) + 1) % EQUIPMENT_KINDS.length]!);
      }}>
      <SceneCanvas label={`${EQUIPMENT_LABELS[current]} ilustrativo, no procede de un IFC`}>
        <EquipmentScene kind={current} mode={mode} interactive={interactive} onBearing={value => { if (bearing.current) bearing.current.textContent = value; }} measureKey={measureKey} onMeasure={onMeasure} />
      </SceneCanvas>
    </div>
    <div className={styles.hud}>
      {hud ? <div className={styles.row}><span ref={bearing}>N 045°</span><span>Modelo paramétrico</span></div> : <span />}
      <div className={styles.bottom}>
        {hud ? <><strong className={styles.name}>{EQUIPMENT_LABELS[current]}</strong>
          {interactive ? <span>Arrastra para girar · Clic para cambiar equipo</span> : null}
          {interactive ? <div className={styles.controls}>{EQUIPMENT_KINDS.map(item => <button key={item} className={styles.control}
            aria-pressed={item === current} aria-label={`Mostrar ${EQUIPMENT_LABELS[item]}`} onClick={() => select(item)}>{EQUIPMENT_LABELS[item]}</button>)}</div> : null}</> : null}
        <span className={styles.notice}>Ilustrativo · no procede del IFC</span>
      </div>
    </div>
  </div>;
}

export function EquipmentThumb({ kind, size = 96 }: EquipmentThumbProps) {
  const [image, setImage] = useState<{ kind: EquipmentKind; src: string } | null>(null);
  const root = useRef<HTMLElement>(null);
  useEffect(() => {
    let live = true;
    const observer = new IntersectionObserver(entries => {
      if (!entries[0]?.isIntersecting) return;
      observer.disconnect();
      void import("./thumbnail-renderer").then(m => m.equipmentThumbnail(kind)).then(src => {
        if (live) setImage({ kind, src });
      }).catch(() => {});
    });
    if (root.current) observer.observe(root.current);
    return () => { live = false; observer.disconnect(); };
  }, [kind]);
  return <figure ref={root} className={styles.thumb} style={{ width: size, height: size }} title="Ilustrativo · no procede del IFC">
    {image?.kind === kind ? <Image src={image.src} width={size} height={size} unoptimized alt={`${EQUIPMENT_LABELS[kind]} ilustrativo`} /> : null}
    <figcaption>Ilustrativo</figcaption>
  </figure>;
}
