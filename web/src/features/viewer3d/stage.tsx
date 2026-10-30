"use client";

import { CameraControls, ContactShadows, Environment, Html as DreiHtml, Lightformer } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { EffectComposer, Selection, SelectiveBloom, SMAA, SSAO, Vignette } from "@react-three/postprocessing";
import { Camera, Maximize, Minus, Plus, RotateCcw } from "lucide-react";
import { useReducedMotion } from "motion/react";
import { Component, createContext, useContext, useEffect, useImperativeHandle, useRef, useMemo, useState, type ComponentProps, type ReactNode, type Ref, type RefObject } from "react";
import { AgXToneMapping, Box3, Matrix4, OrthographicCamera, Vector3, type DirectionalLight } from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { BRAND } from "@/lib/brand";
import type { Bounds, Vec3 } from "@/workers/ifc-protocol";
import styles from "./viewer.module.css";

export type View = "iso" | "front" | "top" | "plan";
export type CameraHandle = { view(v: View): void; fit(bounds?: Bounds): void; zoom(factor: number): void; capture(): void };
export type PerformanceSample = { fps: number; p95Ms: number; frames: number; renderer: string; drawCalls: number; triangles: number; dpr: number };
export const asBox = (bounds: Bounds) => new Box3(new Vector3(...bounds.min), new Vector3(...bounds.max));
const OverlayContext = createContext<RefObject<HTMLDivElement | null> | null>(null);

export function SceneLabel(props: ComponentProps<typeof DreiHtml>) {
  const portal = useContext(OverlayContext);
  return <DreiHtml {...props} portal={portal as RefObject<HTMLElement> | undefined} />;
}

export function CameraRig({ bounds, view = "iso", handle, onUserControl, measureKey, onMeasure, interactive = true }: {
  bounds: Bounds; view?: View; handle: Ref<CameraHandle>; onUserControl?(): void;
  measureKey?: number; onMeasure?(sample: PerformanceSample): void; interactive?: boolean;
}) {
  const controls = useRef<CameraControls>(null);
  const { camera, gl, scene, invalidate, size: viewport } = useThree();
  const reduce = useReducedMotion();
  const sample = useRef({ key: 0, started: 0, previous: 0, deltas: [] as number[] });
  const frame = (box: Box3, eye: Vector3, smooth: boolean) => {
    const center = box.getCenter(new Vector3());
    const transform = new Matrix4().lookAt(eye, center, camera.up).setPosition(eye).invert();
    const projected = box.clone().applyMatrix4(transform).getSize(new Vector3());
    const zoom = Math.min(viewport.width / Math.max(projected.x, .1), viewport.height / Math.max(projected.y, .1)) / 1.4;
    void controls.current?.setLookAt(eye.x, eye.y, eye.z, center.x, center.y, center.z, smooth && !reduce);
    void controls.current?.zoomTo(Math.min(650, Math.max(5, zoom)), smooth && !reduce);
    invalidate();
  };
  const show = (next: View, smooth: boolean) => {
    const box = asBox(bounds), center = box.getCenter(new Vector3()), size = box.getSize(new Vector3());
    const distance = Math.max(size.x, size.y, size.z, 1) * 2;
    const offsets: Record<View, Vec3> = { iso: [distance, distance * .65, distance],
      front: [0, 0, distance], plan: [0, 0, distance], top: [0, distance, .001] };
    // Proyectar los límites conserva la isometría y aprovecha el tamaño real del panel.
    frame(box, center.add(new Vector3(...offsets[next])), smooth);
  };
  useEffect(() => {
    show(view, false);
    // La vista cambia solo por una orden explícita, nunca por selección de campos con teclado.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, bounds, viewport.width, viewport.height]);
  useImperativeHandle(handle, () => ({
    view: next => show(next, true),
    fit: target => { const box = asBox(target ?? bounds), center = box.getCenter(new Vector3());
      const direction = camera.getWorldDirection(new Vector3());
      frame(box, center.addScaledVector(direction, -Math.max(10, box.getSize(new Vector3()).length() * 2)), true); },
    zoom: factor => { void controls.current?.zoomTo((camera as OrthographicCamera).zoom * factor, !reduce); invalidate(); },
    capture: () => {
      gl.render(scene, camera);
      gl.domElement.toBlob(blob => {
        if (!blob) return;
        const url = URL.createObjectURL(blob), link = document.createElement("a");
        link.href = url; link.download = "trazia-ifc-sintetico.png"; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      });
    },
  }));
  useFrame((_, delta) => {
    const drawCalls = gl.info.render.calls, triangles = gl.info.render.triangles;
    gl.info.reset();
    if (!measureKey || measureKey === sample.current.key) return;
    const now = performance.now(), s = sample.current;
    if (!s.started) { s.started = now; s.previous = now; }
    const elapsed = now - s.started;
    if (elapsed > 300) s.deltas.push(now - s.previous);
    s.previous = now;
    if (elapsed < 5300) {
      if (!reduce) void controls.current?.rotate(delta * .35, 0, false);
      invalidate();
    } else {
      const deltas = [...s.deltas].sort((a, b) => a - b);
      const average = s.deltas.reduce((a, b) => a + b, 0) / Math.max(1, s.deltas.length);
      const context = gl.getContext(), debug = context.getExtension("WEBGL_debug_renderer_info");
      onMeasure?.({ fps: 1000 / average, p95Ms: deltas[Math.floor(deltas.length * .95)] ?? 0,
        frames: s.deltas.length, renderer: String(context.getParameter(debug?.UNMASKED_RENDERER_WEBGL ?? context.RENDERER)),
        drawCalls, triangles, dpr: gl.getPixelRatio() });
      sample.current = { key: measureKey, started: 0, previous: 0, deltas: [] };
    }
  });
  useEffect(() => { if (measureKey) invalidate(); }, [measureKey, invalidate]);
  return <CameraControls ref={controls} enabled={interactive} makeDefault smoothTime={reduce ? 0 : .4} draggingSmoothTime={.1}
    minZoom={5} maxZoom={650} maxPolarAngle={Math.PI * .98} regress
    onControlStart={() => { controls.current?.stop(); onUserControl?.(); }} />;
}

function AdaptiveResolution() {
  const { size, setDpr } = useThree();
  const quality = useThree(state => state.performance.current);
  useEffect(() => {
    // Presupuesto de píxeles: el coste del posprocesado no crece sin límite al maximizar.
    const budget = Math.sqrt(1_000_000 / Math.max(1, size.width * size.height));
    setDpr(Math.min(window.devicePixelRatio, 1.6, budget) * quality);
  }, [size.width, size.height, quality, setDpr]);
  return null;
}

export function Studio({ effects = true }: { effects?: boolean }) {
  const room = useMemo(() => new RoomEnvironment(), []);
  const key = useRef<DirectionalLight>(null), rim = useRef<DirectionalLight>(null);
  useEffect(() => () => room.dispose(), [room]);
  return <>
    <color attach="background" args={[BRAND.black]} />
    <ambientLight intensity={.4} color={BRAND.text} />
    <directionalLight ref={key} position={[5, 9, 7]} intensity={2} color={BRAND.text} />
    <directionalLight ref={rim} position={[-6, 5, -3]} intensity={1} color={BRAND.skyPale} />
    <Environment resolution={128} frames={1} environmentIntensity={.65}>
      <primitive object={room} dispose={null} />
      <Lightformer form="ring" position={[-4, 5, 3]} rotation={[0, .7, 0]} scale={4} intensity={2} color={BRAND.text} />
      <Lightformer position={[4, 6, -4]} rotation={[0, -.6, 0]} scale={[3, 10, 1]} intensity={3} color={BRAND.text} />
      <Lightformer position={[-5, 4, 4]} rotation={[0, Math.PI, 0]} scale={[2, 8, 1]} intensity={2} color={BRAND.skyPale} />
      <Lightformer position={[0, 9, 0]} rotation={[Math.PI / 2, 0, 0]} scale={[6, 6, 1]} intensity={2} color={BRAND.text} />
    </Environment>
    <ContactShadows position={[0, -.025, 0]} opacity={.45} scale={24} blur={2.5} far={15} frames={1} resolution={256} color={BRAND.black} />
    <AdaptiveResolution />
    {effects ? <EffectComposer enableNormalPass multisampling={0} resolutionScale={.5}>
      <SSAO resolutionScale={.5} depthAwareUpsampling samples={8} rings={3} intensity={.8} radius={.12} luminanceInfluence={.7} />
      <SelectiveBloom lights={[key, rim]} selectionLayer={11} intensity={.55} luminanceThreshold={1} mipmapBlur ignoreBackground />
      <SMAA />
      <Vignette offset={.3} darkness={.55} />
    </EffectComposer> : null}
  </>;
}

class RenderBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <div role="alert" className={styles.status}>No se pudo iniciar WebGL. Activa la aceleración gráfica o abre el visor en otro navegador.</div> : this.props.children;
  }
}

export function SceneCanvas({ children, label }: { children: ReactNode; label: string }) {
  const portal = useRef<HTMLDivElement>(null), root = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(true);
  useEffect(() => {
    let visible = true;
    const update = () => setActive(visible && !document.hidden);
    const observer = new IntersectionObserver(entries => { visible = entries[0]?.isIntersecting ?? false; update(); });
    if (root.current) observer.observe(root.current);
    document.addEventListener("visibilitychange", update);
    return () => { observer.disconnect(); document.removeEventListener("visibilitychange", update); };
  }, []);
  return <div ref={root} style={{ position: "relative", height: "100%", width: "100%" }}><RenderBoundary>
    <Canvas className={styles.canvas} orthographic frameloop={active ? "demand" : "never"} dpr={[1, 1.6]}
      camera={{ position: [12, 9, 12], zoom: 50, near: .01, far: 1000 }} performance={{ min: .65 }}
      gl={{ antialias: false, alpha: false, localClippingEnabled: true }}
      onCreated={({ gl }) => { gl.info.autoReset = false; gl.toneMapping = AgXToneMapping; gl.toneMappingExposure = 1.1; }} aria-label={label}>
      <Selection><OverlayContext.Provider value={portal}>{children}</OverlayContext.Provider></Selection>
    </Canvas><div ref={portal} className={styles.labels} />
  </RenderBoundary></div>;
}

export function CameraTools({ handle, container, onReset }: { handle: RefObject<CameraHandle | null>; container: RefObject<HTMLDivElement | null>; onReset?(): void }) {
  return <div className={styles.tools} role="group" aria-label="Controles de cámara">
    <button className={styles.button} title="Restablecer vista" aria-label="Restablecer vista" onClick={() => onReset ? onReset() : handle.current?.view("iso")}><RotateCcw /></button>
    <button className={styles.button} title="Acercar" aria-label="Acercar" onClick={() => handle.current?.zoom(1.25)}><Plus /></button>
    <button className={styles.button} title="Alejar" aria-label="Alejar" onClick={() => handle.current?.zoom(.8)}><Minus /></button>
    <button className={styles.button} title="Capturar PNG" aria-label="Capturar PNG" onClick={() => handle.current?.capture()}><Camera /></button>
    <button className={styles.button} title="Pantalla completa" aria-label="Pantalla completa" onClick={() => {
      if (document.fullscreenElement) void document.exitFullscreen();
      else void container.current?.requestFullscreen();
    }}><Maximize /></button>
  </div>;
}

export function Legend() {
  return <details className={styles.legend}><summary>Estados del modelo</summary><ul>
    <li><span className={`${styles.swatch} ${styles.approved}`} /> Aprobado</li>
    <li><span className={`${styles.swatch} ${styles.draft}`} /> DRAFT</li>
    <li><span className={`${styles.swatch} ${styles.assumed}`} /> Supuesto</li>
    <li><span className={`${styles.swatch} ${styles.changed}`} /> Cambiado Δ</li>
    <li><span className={`${styles.swatch} ${styles.conflict}`} /> Conflicto</li>
  </ul></details>;
}

export function LoadingState({ error, label = "Leyendo geometría IFC en segundo plano" }: { error?: string | null; label?: string }) {
  return <div className={styles.status} role={error ? "alert" : "status"}>
    {!error ? <div className={styles.skeleton} aria-hidden="true" /> : null}
    <span>{error ?? label}</span>
  </div>;
}
