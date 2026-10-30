"use client";

import { BRAND } from "@/lib/brand";

import { useFrame, useThree } from "@react-three/fiber";
import { Pause, Play, RotateCcw, SkipForward } from "lucide-react";
import { cubicBezier, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState, type RefObject } from "react";
import { CanvasTexture, Group, Mesh, MeshStandardMaterial, SRGBColorSpace } from "three";
import type { Bounds } from "@/workers/ifc-protocol";
import { useIfcModel, usePreparedModel, type PreparedProduct } from "./model-resource";
import { CameraRig, CameraTools, Legend, LoadingState, SceneCanvas, Studio, type CameraHandle } from "./stage";
import styles from "./viewer.module.css";
import { SteelMaterial } from "./materials";

type Evidence = { bbox: [number, number, number, number]; label: string };
class Timeline {
  progress = 0;
  playing = false;
  advance(delta: number, reduced: boolean) { this.progress = reduced ? 1 : Math.min(1, this.progress + Math.min(delta, .064) / 5); }
  pause() { this.playing = false; }
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

function LiftScene({ products, drawing, timeline, onPhase, onFinish, reduced, playing }: {
  products: PreparedProduct[]; drawing: { texture: CanvasTexture; aspect: number; evidence: Evidence[] };
  timeline: RefObject<Timeline>; onPhase(phase: number): void; onFinish(): void; reduced: boolean; playing: boolean;
}) {
  const model = useRef<Group>(null), steel = useRef<Group>(null), wire = useRef<Group>(null), lights = useRef<Group>(null);
  const phase = useRef(-1), { invalidate } = useThree();
  const paper = useRef<Mesh>(null);
  useEffect(() => { invalidate(); }, [playing, reduced, invalidate]);
  useFrame((_, delta) => {
    const t = timeline.current;
    if (reduced && t.progress < 1) { t.advance(0, true); t.pause(); onFinish(); }
    if (t.playing) t.advance(delta, reduced);
    const progress = t.progress, q = ease(Math.max(0, (progress - .28) / .72));
    if (model.current) {
      model.current.rotation.x = -(1 - q) * Math.PI / 2;
      model.current.position.set(-3.3 * (1 - q), .04, 2.6 * (1 - q));
      model.current.scale.set(.78 + .22 * q, .65 + .35 * q, .025 + .975 * q);
    }
    steel.current?.traverse(object => { if (object instanceof Mesh) { const material = object.material as MeshStandardMaterial; material.opacity = q; material.depthWrite = q > .99; } });
    wire.current?.traverse(object => { if (object instanceof Mesh) { const material = object.material as MeshStandardMaterial; material.opacity = (1 - q) * .85; } });
    lights.current?.children.forEach((object, index) => {
      const material = (object as Mesh).material as MeshStandardMaterial;
      const active = progress < .32 && index === Math.min(drawing.evidence.length - 1, Math.floor(progress / .32 * drawing.evidence.length));
      material.opacity = active ? .55 : progress < .32 && index < progress / .32 * drawing.evidence.length ? .15 : .02;
    });
    if (paper.current) (paper.current.material as MeshStandardMaterial).opacity = 1 - q * .72;
    const nextPhase = progress < .28 ? 0 : progress < .82 ? 1 : 2;
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

export function Signature() {
  const load = useIfcModel("/demo/ifc/rev_a.ifc"), products = usePreparedModel(load.model);
  const { drawing, error } = useDrawing();
  const container = useRef<HTMLDivElement>(null), camera = useRef<CameraHandle>(null);
  const timeline = useRef(new Timeline());
  const [playing, setPlaying] = useState(false), [phase, setPhase] = useState(0);
  const [version, setVersion] = useState(0), reduced = useReducedMotion();
  const ready = !!load.model && !!drawing;
  const titles = ["El plano conserva la evidencia", "La geometría del IFC se levanta", "Modelo DRAFT listo para revisar"];
  const descriptions = ["Las cinco cotas se localizan en su región real del PDF.",
    "Las mallas del IFC pasan de alambre a acero. La secuencia es ilustrativa.",
    "La aprobación continúa en el espacio de revisión; esta secuencia no valida el equipo."];
  const pause = () => { timeline.current.playing = false; setPlaying(false); };
  return <div className={styles.frame} ref={container} data-testid="signature" data-phase={ready ? "ready" : "loading"}>
    {ready ? <SceneCanvas label="Secuencia sintética: evidencia del plano y geometría del IFC">
      <Studio effects={false} />
      <CameraRig bounds={SIGNATURE_BOUNDS} handle={camera} onUserControl={pause} />
      <LiftScene key={version} products={products} drawing={drawing} timeline={timeline} onPhase={setPhase} onFinish={() => setPlaying(false)} reduced={!!reduced} playing={playing} />
    </SceneCanvas> : <LoadingState error={error ?? load.error} label="Leyendo el PDF y el IFC sintéticos" />}
    <CameraTools handle={camera} container={container} />
    <div className={styles.badge}>Prototipo · datos sintéticos · 5 s</div>
    <div className={styles.narration}>
      <button className={styles.button} disabled={!ready} aria-label={playing ? "Pausar firma" : "Reproducir firma"} onClick={() => {
        if (reduced) { timeline.current.progress = 1; timeline.current.playing = false; setPhase(2); setVersion(v => v + 1); return; }
        if (timeline.current.progress >= 1) timeline.current.progress = 0;
        timeline.current.playing = !timeline.current.playing; setPlaying(timeline.current.playing);
      }}>{playing ? <Pause /> : <Play />}</button>
      <p><strong>{titles[phase]}</strong>{descriptions[phase]}</p>
      <button className={styles.button} disabled={!ready} aria-label="Saltar la secuencia" onClick={() => {
        pause(); timeline.current.progress = 1; setPhase(2); setVersion(v => v + 1);
      }}><SkipForward /></button>
      <button className={styles.button} disabled={!ready} aria-label="Restablecer secuencia" onClick={() => {
        pause(); timeline.current.progress = 0; setPhase(0); setVersion(v => v + 1);
      }}><RotateCcw /></button>
    </div>
    <Legend />
  </div>;
}
