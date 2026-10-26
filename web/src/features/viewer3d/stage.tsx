"use client";

import { AdaptiveDpr, CameraControls, Environment, Html as DreiHtml, Lightformer } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { EffectComposer, SSAO } from "@react-three/postprocessing";
import { Camera, Maximize, Minus, Plus, RotateCcw } from "lucide-react";
import { useReducedMotion } from "motion/react";
import { useTheme } from "next-themes";
import { Component, createContext, useContext, useEffect, useImperativeHandle, useRef, type ComponentProps, type ReactNode, type Ref, type RefObject } from "react";
import { Box3, OrthographicCamera, Sphere, Vector3 } from "three";
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

export function CameraRig({ bounds, view = "iso", handle, onUserControl, measureKey, onMeasure }: {
  bounds: Bounds; view?: View; handle: Ref<CameraHandle>; onUserControl?(): void;
  measureKey?: number; onMeasure?(sample: PerformanceSample): void;
}) {
  const controls = useRef<CameraControls>(null);
  const { camera, gl, scene, invalidate } = useThree();
  const reduce = useReducedMotion();
  const sample = useRef({ key: 0, started: 0, previous: 0, deltas: [] as number[] });
  const show = (next: View, smooth: boolean) => {
    const box = asBox(bounds), center = box.getCenter(new Vector3()), size = box.getSize(new Vector3());
    const distance = Math.max(size.x, size.y, size.z, 1) * 2;
    const offsets: Record<View, Vec3> = { iso: [distance, distance * .65, distance],
      front: [0, 0, distance], plan: [0, 0, distance], top: [0, distance, .001] };
    const offset = offsets[next];
    void controls.current?.setLookAt(center.x + offset[0], center.y + offset[1], center.z + offset[2],
      center.x, center.y, center.z, smooth && !reduce);
    // fitToBox ajusta la cámara al eje más cercano; la esfera conserva la isometría elegida.
    const sphere = box.getBoundingSphere(new Sphere()); sphere.radius *= 1.2;
    void controls.current?.fitToSphere(sphere, smooth && !reduce);
    invalidate();
  };
  useEffect(() => {
    show(view, false);
    // La vista cambia solo por una orden explícita, nunca por selección de campos con teclado.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, bounds]);
  useImperativeHandle(handle, () => ({
    view: next => show(next, true),
    fit: target => { const sphere = asBox(target ?? bounds).getBoundingSphere(new Sphere()); sphere.radius *= 1.2;
      void controls.current?.fitToSphere(sphere, !reduce); invalidate(); },
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
  return <CameraControls ref={controls} makeDefault smoothTime={reduce ? 0 : .4} draggingSmoothTime={.1}
    minZoom={5} maxZoom={650} maxPolarAngle={Math.PI * .98} regress
    onControlStart={() => { controls.current?.stop(); onUserControl?.(); }} />;
}

export function Studio({ effects = true }: { effects?: boolean }) {
  const { resolvedTheme } = useTheme();
  return <>
    <color attach="background" args={[resolvedTheme === "light" ? "#edf2f8" : "#101720"]} />
    <ambientLight intensity={.65} />
    <directionalLight position={[5, 10, 7]} intensity={2.3} color="#f4f7ff" />
    <directionalLight position={[-6, 4, -3]} intensity={1.4} color="#8daed7" />
    <Environment resolution={64} frames={1}>
      <Lightformer position={[4, 6, -4]} scale={[6, 10, 1]} intensity={3} />
      <Lightformer position={[-5, 4, 4]} rotation={[0, Math.PI, 0]} scale={[5, 8, 1]} intensity={2} />
      <Lightformer position={[0, 9, 0]} rotation={[Math.PI / 2, 0, 0]} scale={[7, 7, 1]} intensity={2} />
    </Environment>
    <AdaptiveDpr pixelated />
    {effects ? <EffectComposer enableNormalPass multisampling={0}>
      <SSAO samples={8} rings={3} intensity={1.1} radius={.1} luminanceInfluence={.7} />
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
  const portal = useRef<HTMLDivElement>(null);
  return <RenderBoundary><Canvas className={styles.canvas} orthographic frameloop="demand" dpr={[1, 1.6]}
    camera={{ position: [12, 9, 12], zoom: 50, near: .01, far: 1000 }} performance={{ min: .65 }}
    gl={{ antialias: true, alpha: false, localClippingEnabled: true }}
    onCreated={({ gl }) => { gl.info.autoReset = false; }} aria-label={label}>
    <OverlayContext.Provider value={portal}>{children}</OverlayContext.Provider>
  </Canvas><div ref={portal} className={styles.labels} /></RenderBoundary>;
}

export function CameraTools({ handle, container }: { handle: RefObject<CameraHandle | null>; container: RefObject<HTMLDivElement | null> }) {
  return <div className={styles.tools} role="group" aria-label="Controles de cámara">
    <button className={styles.button} title="Restablecer vista" aria-label="Restablecer vista" onClick={() => handle.current?.view("iso")}><RotateCcw /></button>
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
