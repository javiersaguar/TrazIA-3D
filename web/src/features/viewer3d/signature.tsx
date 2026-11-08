"use client";

import { BRAND } from "@/lib/brand";

import { useFrame, useThree } from "@react-three/fiber";
import { Pause, Play, RotateCcw, SkipForward } from "lucide-react";
import { cubicBezier, useReducedMotion, type MotionValue } from "motion/react";
import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";
import { CanvasTexture, Group, Mesh, MeshStandardMaterial, SRGBColorSpace } from "three";
import type { Bounds } from "@/workers/ifc-protocol";
import { useIfcModel, usePreparedModel, type PreparedProduct } from "./model-resource";
import { CameraRig, CameraTools, Legend, LoadingState, SceneCanvas, Studio, type CameraHandle } from "./stage";
import styles from "./viewer.module.css";
import { SteelMaterial } from "./materials";
import { SIGNATURE_PHASES } from "./signature-phases";

type Evidence = { bbox: [number, number, number, number]; label: string };
class Timeline {
  progress = 0;
  playing = false;
  advance(delta: number, reduced: boolean) { this.progress = reduced ? 1 : Math.min(1, this.progress + Math.min(delta, .064) / 5); }
  pause() { this.playing = false; }
  seek(value: number, reduced: boolean) { this.progress = reduced ? 1 : Math.min(1, Math.max(0, value)); }
}
const ease = cubicBezier(.65, 0, .35, 1);
const SIGNATURE_BOUNDS: Bounds = { min: [-6.5, -.1, -4.8], max: [6.5, 8.2, 4.8] };


function useDrawing() {
  const [drawing, setDrawing] = useState<{ texture: CanvasTexture; aspect: number; evidence: Evidence[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true, texture: CanvasTexture | undefined;
    let cleanup: (() => void) | undefined;
    const load = async () => {
      const [pdfjs, response] = await Promise.all([import("pdfjs-dist"), fetch("/demo/json/vessel_rev_a.json")]);
      if (!response.ok) throw new Error("No se pudo leer la evidencia de la revisión A");
      const json = await response.json();
      pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
      const task = pdfjs.getDocument({ url: "/demo/docs/GAD_V-101_revA.pdf" });
      cleanup = () => { void task.destroy(); texture?.dispose(); };
      const document = await task.promise;
      if (!live) { cleanup(); return; }
      const page = await document.getPage(1), viewport = page.getViewport({ scale: 1.25 });
      const canvas = window.document.createElement("canvas");
      canvas.width = viewport.width; canvas.height = viewport.height;
      await page.render({ canvas, viewport }).promise;
      texture = new CanvasTexture(canvas); texture.colorSpace = SRGBColorSpace;
      const evidence: Evidence[] = [];
      for (const key of ["diameter", "height", "head_depth", "skirt_height", "skirt_thickness"]) {
        const field = json.equipment?.[key];
        if (field?.source?.bbox && field.source.page === 1) evidence.push({ bbox: field.source.bbox, label: key });
      }
      if (live) setDrawing({ texture, aspect: viewport.width / viewport.height, evidence });
      else cleanup();
    };
    void load().catch(problem => { if (live) setError(String(problem.message)); });
    return () => { live = false; cleanup?.(); };
  }, []);
  return { drawing, error };
}

function LiftScene({ products, drawing, timeline, onPhase, onFinish, reduced, playing, progress: scroll }: {
  products: PreparedProduct[]; drawing: { texture: CanvasTexture; aspect: number; evidence: Evidence[] };
  timeline: RefObject<Timeline>; onPhase(phase: number): void; onFinish(): void; reduced: boolean; playing: boolean;
  progress?: MotionValue<number>;
}) {
  const model = useRef<Group>(null), steel = useRef<Group>(null), wire = useRef<Group>(null), lights = useRef<Group>(null);
  const phase = useRef(-1), { invalidate } = useThree();
  const paper = useRef<Mesh>(null);
  const materials = useRef<{steel:MeshStandardMaterial[]; wire:MeshStandardMaterial[]}>({steel:[],wire:[]});
  const lastProgress = useRef(-1);
  useLayoutEffect(() => {
    const collect = (group: Group | null) => {
      const list: MeshStandardMaterial[] = [];
      group?.traverse(object => { if (object instanceof Mesh) list.push(object.material as MeshStandardMaterial); });
      return list;
    };
    materials.current = {steel:collect(steel.current),wire:collect(wire.current)};
    lastProgress.current = -1;
  }, [products]);
  useEffect(() => { invalidate(); }, [playing, reduced, invalidate]);
  // Con «progress», el scroll de la página es el avance de la secuencia: cada cambio pide un fotograma
  useEffect(() => scroll?.on("change", () => invalidate()), [scroll, invalidate]);
  useFrame((_, delta) => {
    const t = timeline.current;
    if (reduced && t.progress < 1) { t.advance(0, true); t.pause(); onFinish(); }
    if (scroll) t.seek(scroll.get(), reduced);
    else if (t.playing) t.advance(delta, reduced);
    const progress = t.progress, q = ease(Math.max(0, (progress - .28) / .72));
    if (progress !== lastProgress.current) {
    lastProgress.current = progress;
    if (model.current) {
      model.current.rotation.x = -(1 - q) * Math.PI / 2;
      model.current.position.set(-3.3 * (1 - q), .04, 2.6 * (1 - q));
      model.current.scale.set(.78 + .22 * q, .65 + .35 * q, .025 + .975 * q);
    }
    for (const material of materials.current.steel) material.setValues({opacity:q,depthWrite:q>.99});
    for (const material of materials.current.wire) material.setValues({opacity:(1-q)*.85});
    lights.current?.children.forEach((object, index) => {
      const material = (object as Mesh).material as MeshStandardMaterial;
      const active = progress < .32 && index === Math.min(drawing.evidence.length - 1, Math.floor(progress / .32 * drawing.evidence.length));
      material.opacity = active ? .55 : progress < .32 && index < progress / .32 * drawing.evidence.length ? .15 : .02;
    });
    if (paper.current) (paper.current.material as MeshStandardMaterial).opacity = 1 - q * .72;
    }
    const nextPhase = progress < SIGNATURE_PHASES[1].at ? 0 : progress < SIGNATURE_PHASES[2].at ? 1 : 2;
    if (phase.current !== nextPhase) { phase.current = nextPhase; onPhase(nextPhase); }
    if (t.playing && progress >= 1) { t.pause(); onFinish(); }
    if (t.playing) invalidate();
  });
  const height = 12 / drawing.aspect;
  const meshes = (wireframe: boolean) => products.flatMap(product => product.geometries.map((geometry, index) =>
    <mesh key={`${product.globalId}:${index}`} geometry={geometry} position={product.center} dispose={null}>
      <SteelMaterial color={wireframe ? BRAND.skyLight : BRAND.steel} wireframe={wireframe} transparent
        opacity={wireframe ? .85 : 0} metalness={wireframe ? 0 : .6} roughness={.32} depthWrite={!wireframe} />
    </mesh>));
  return <>
    <mesh ref={paper} rotation-x={-Math.PI / 2} position={[0, -.02, 0]}>
      <planeGeometry args={[12, height]} /><meshStandardMaterial map={drawing.texture} roughness={1} transparent />
    </mesh>
    <group ref={lights}>{drawing.evidence.map((evidence, index) => {
      const [x0, y0, x1, y1] = evidence.bbox;
      return <mesh key={index} rotation-x={-Math.PI / 2} position={[(x0 + x1 - 1) * 6, -.005, (y0 + y1 - 1) * height / 2]}>
        <planeGeometry args={[(x1 - x0) * 12 + .08, (y1 - y0) * height + .05]} />
        <meshBasicMaterial color={BRAND.skyLight} transparent opacity={0} depthWrite={false} />
      </mesh>;
    })}</group>
    <group ref={model}><group ref={wire}>{meshes(true)}</group><group ref={steel}>{meshes(false)}</group></group>
  </>;
}

/** Sin «progress» se reproduce con sus botones; con él, avanza con el scroll y sin controles propios. */
export function Signature({ progress, pixelBudget }: { progress?: MotionValue<number>; pixelBudget?: number } = {}) {
  const scroll = !!progress;
  const load = useIfcModel("/demo/ifc/rev_a.ifc"), products = usePreparedModel(load.model);
  const { drawing, error } = useDrawing();
  const container = useRef<HTMLDivElement>(null), camera = useRef<CameraHandle>(null);
  const timeline = useRef(new Timeline());
  const [playing, setPlaying] = useState(false), [phase, setPhase] = useState(0);
  const [version, setVersion] = useState(0), reduced = useReducedMotion();
  const ready = !!load.model && !!drawing;
  const pause = () => { timeline.current.playing = false; setPlaying(false); };
  return <div className={styles.frame} ref={container} data-testid="signature" data-phase={ready ? "ready" : "loading"} data-step={phase}>
    {ready ? <SceneCanvas pixelBudget={pixelBudget} label="Secuencia sintética: evidencia del plano y geometría del IFC" rotationControl={!scroll}>
      <Studio effects={false} />
      <CameraRig bounds={SIGNATURE_BOUNDS} handle={camera} onUserControl={pause} interactive={!scroll} orbit={!scroll} />
      <LiftScene key={version} products={products} drawing={drawing} timeline={timeline} onPhase={setPhase} onFinish={() => setPlaying(false)} reduced={!!reduced} playing={playing} progress={progress} />
    </SceneCanvas> : <LoadingState error={error ?? load.error} label="Leyendo el PDF y el IFC sintéticos" />}
    {scroll ? <div className={styles.badge} data-scroll>Prototipo · datos sintéticos</div> : <>
    <CameraTools handle={camera} container={container} />
    <div className={styles.badge}>Prototipo · datos sintéticos · 5 s</div>
    <div className={styles.narration}>
      <button className={styles.button} disabled={!ready} aria-label={playing ? "Pausar firma" : "Reproducir firma"} onClick={() => {
        if (reduced) { timeline.current.progress = 1; timeline.current.playing = false; setPhase(2); setVersion(v => v + 1); return; }
        if (timeline.current.progress >= 1) timeline.current.progress = 0;
        timeline.current.playing = !timeline.current.playing; setPlaying(timeline.current.playing);
      }}>{playing ? <Pause /> : <Play />}</button>
      <p><strong>{(SIGNATURE_PHASES[phase] ?? SIGNATURE_PHASES[0]).title}</strong>{(SIGNATURE_PHASES[phase] ?? SIGNATURE_PHASES[0]).text}</p>
      <button className={styles.button} disabled={!ready} aria-label="Saltar la secuencia" onClick={() => {
        pause(); timeline.current.progress = 1; setPhase(2); setVersion(v => v + 1);
      }}><SkipForward /></button>
      <button className={styles.button} disabled={!ready} aria-label="Restablecer secuencia" onClick={() => {
        pause(); timeline.current.progress = 0; setPhase(0); setVersion(v => v + 1);
      }}><RotateCcw /></button>
    </div>
    <Legend />
    </>}
  </div>;
}
