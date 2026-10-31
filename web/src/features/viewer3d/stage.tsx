"use client";

import {
  CameraControls,
  ContactShadows,
  Environment,
  Html as DreiHtml,
  Lightformer,
} from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  EffectComposer,
  Selection,
  SelectiveBloom,
  SMAA,
  SSAO,
  Vignette,
} from "@react-three/postprocessing";
import { Camera, Maximize, Minus, Plus, RotateCcw, Pause, Play } from "lucide-react";
import { useReducedMotion } from "motion/react";
import {
  Component,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useImperativeHandle,
  useRef,
  useMemo,
  useState,
  useSyncExternalStore,
  type ComponentProps,
  type ReactNode,
  type Ref,
  type RefObject,
} from "react";
import {
  AgXToneMapping,
  Box3,
  CanvasTexture,
  Matrix4,
  OrthographicCamera,
  RepeatWrapping,
  SRGBColorSpace,
  Vector3,
  type DirectionalLight,
} from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { BRAND } from "@/lib/brand";
import type { Bounds, Vec3 } from "@/workers/ifc-protocol";
import styles from "./viewer.module.css";
import type { CameraLink } from "./camera-link";

export type View = "iso" | "front" | "top" | "plan";
export type CameraHandle = {
  view(v: View): void;
  fit(bounds?: Bounds, normal?: Vec3): void;
  zoom(factor: number): void;
  capture(): void;
};
export type PerformanceSample = {
  fps: number;
  p95Ms: number;
  frames: number;
  renderer: string;
  drawCalls: number;
  triangles: number;
  dpr: number;
};
export const asBox = (bounds: Bounds) =>
  new Box3(new Vector3(...bounds.min), new Vector3(...bounds.max));
const OverlayContext = createContext<RefObject<HTMLDivElement | null> | null>(
  null,
);

const OrbitContext = createContext({ enabled: true, pause: () => {} });
export const ORBIT_SECONDS = 60;

export function SceneLabel(props: ComponentProps<typeof DreiHtml>) {
  const portal = useContext(OverlayContext);
  return (
    <DreiHtml
      {...props}
      portal={portal as RefObject<HTMLElement> | undefined}
    />
  );
}

export function CameraRig({
  bounds,
  view = "iso",
  handle,
  onUserControl,
  measureKey,
  onMeasure,
  interactive = true,
  orbit = true,
  orbitCenter,
  link,
}: {
  bounds: Bounds;
  view?: View;
  handle: Ref<CameraHandle>;
  onUserControl?(): void;
  measureKey?: number;
  onMeasure?(sample: PerformanceSample): void;
  interactive?: boolean;
  orbit?: boolean;
  orbitCenter?: Vec3;
  link?: CameraLink;
}) {
  const controls = useRef<CameraControls>(null);
  const rotation = useContext(OrbitContext);
  const holding = useRef(false);
  const resumeAt = useRef(0);
  const orbitEnabled = orbit && rotation.enabled;
  const holdOrbit = () => { resumeAt.current = performance.now() + 6000; };
  const { camera, gl, scene, invalidate, size: viewport } = useThree();
  const reduce = useReducedMotion();
  const canvasNode = useRef<HTMLCanvasElement | null>(null);
  useEffect(() => {
    canvasNode.current = gl.domElement;
  }, [gl]);
  const channel = useRef(Symbol("camera"));
  const received = useRef(false);
  useEffect(
    () =>
      link?.subscribe(channel.current, (pose) => {
        received.current = true;
        void controls.current?.setLookAt(...pose.eye, ...pose.target, false);
        void controls.current?.zoomTo(pose.zoom, false);
        invalidate();
      }),
    [link, invalidate],
  );
  const lastPose = useRef(0);
  const publishPose = () => {
    const now = performance.now();
    if (now - lastPose.current > 100) {
      canvasNode.current?.setAttribute(
        "data-camera-zoom",
        String((camera as OrthographicCamera).zoom),
      );
      canvasNode.current?.setAttribute("data-camera-position", camera.position.toArray().join(","));
      canvasNode.current?.setAttribute("data-camera-target", controls.current?.getTarget(new Vector3()).toArray().join(",") ?? "");
      lastPose.current = now;
    }
    if (!link) return;
    if (received.current) {
      received.current = false;
      return;
    }
    const target = controls.current?.getTarget(new Vector3());
    if (target)
      link.publish(channel.current, {
        eye: camera.position.toArray() as Vec3,
        target: target.toArray() as Vec3,
        zoom: (camera as OrthographicCamera).zoom,
      });
  };
  const focusBounds = useRef<Bounds | null>(null),
    focusNormal = useRef<Vec3 | undefined>(undefined);
  const sample = useRef({
    key: 0,
    started: 0,
    previous: 0,
    deltas: [] as number[],
  });
  const frame = (box: Box3, eye: Vector3, smooth: boolean) => {
    const center = box.getCenter(new Vector3());
    const transform = new Matrix4()
      .lookAt(eye, center, camera.up)
      .setPosition(eye)
      .invert();
    const projected = box
      .clone()
      .applyMatrix4(transform)
      .getSize(new Vector3());
    const zoom =
      Math.min(
        viewport.width / Math.max(projected.x, 0.1),
        viewport.height / Math.max(projected.y, 0.1),
      ) / 1.4;
    void controls.current?.setLookAt(
      eye.x,
      eye.y,
      eye.z,
      center.x,
      center.y,
      center.z,
      smooth && !reduce,
    );
    void controls.current?.zoomTo(
      Math.min(650, Math.max(5, zoom)),
      smooth && !reduce,
    );
    if (orbitCenter && !smooth && !focusBounds.current) {
      // El centro físico prevalece sobre el espacio reservado para rótulos y recortes.
      controls.current?.update(0);
      controls.current?.setOrbitPoint(...orbitCenter);
      controls.current?.update(0);
      lastPose.current = 0;
      publishPose();
    }
    invalidate();
  };
  const show = (next: View, smooth: boolean) => {
    const box = asBox(bounds),
      center = box.getCenter(new Vector3()),
      size = box.getSize(new Vector3());
    const distance = Math.max(size.x, size.y, size.z, 1) * 2;
    const offsets: Record<View, Vec3> = {
      iso: [distance, distance * 0.65, distance],
      front: [0, 0, distance],
      plan: [0, 0, distance],
      top: [0, distance, 0.001],
    };
    // Proyectar los límites conserva la isometría y aprovecha el tamaño real del panel.
    frame(box, center.add(new Vector3(...offsets[next])), smooth);
  };
  const fitCurrent = (target: Bounds, smooth: boolean) => {
    const box = asBox(target),
      center = box.getCenter(new Vector3());
    const direction = focusNormal.current
      ? new Vector3(...focusNormal.current).normalize().negate()
      : camera.getWorldDirection(new Vector3());
    frame(
      box,
      center.addScaledVector(
        direction,
        -Math.max(10, box.getSize(new Vector3()).length() * 2),
      ),
      smooth,
    );
  };
  const boundsKey = [...bounds.min, ...bounds.max].join(":");
  const configured = useRef({
    view,
    boundsKey,
    width: viewport.width,
    height: viewport.height,
    initialized: false,
  });
  useEffect(() => {
    const previous = configured.current;
    if (previous.initialized && previous.view !== view) rotation.pause();
    if (
      !previous.initialized ||
      previous.view !== view ||
      previous.boundsKey !== boundsKey
    ) {
      focusBounds.current = null;
      focusNormal.current = undefined;
      show(view, false);
    } else if (
      previous.width !== viewport.width ||
      previous.height !== viewport.height
    ) {
      fitCurrent(focusBounds.current ?? bounds, false);
    }
    configured.current = {
      view,
      boundsKey,
      width: viewport.width,
      height: viewport.height,
      initialized: true,
    };
    // Una nueva vista tiene prioridad sobre el resize; un resize conserva el foco del cambio.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, boundsKey, viewport.width, viewport.height]);
  useImperativeHandle(handle, () => ({
    view: (next) => {
      rotation.pause();
      focusBounds.current = null;
      focusNormal.current = undefined;
      show(next, true);
    },
    fit: (target, normal) => {
      holdOrbit();
      focusBounds.current = target ?? bounds;
      focusNormal.current = normal;
      void controls.current?.fitToBox(asBox(focusBounds.current), !reduce, {
        paddingLeft: 0.25,
        paddingRight: 0.25,
        paddingTop: 0.25,
        paddingBottom: 0.25,
      });
      if (normal) {
        const center = asBox(focusBounds.current).getCenter(new Vector3());
        const eye = center
          .clone()
          .addScaledVector(new Vector3(...normal).normalize(), 10);
        void controls.current?.setLookAt(
          eye.x,
          eye.y,
          eye.z,
          center.x,
          center.y,
          center.z,
          !reduce,
        );
      }
      invalidate();
    },
    zoom: (factor) => {
      holdOrbit();
      void controls.current?.zoomTo(
        (camera as OrthographicCamera).zoom * factor,
        !reduce,
      );
      invalidate();
    },
    capture: () => {
      gl.render(scene, camera);
      gl.domElement.toBlob((blob) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob),
          link = document.createElement("a");
        link.href = url;
        link.download = "trazia-ifc-sintetico.png";
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      });
    },
  }));
  useEffect(() => { invalidate(); }, [orbitEnabled, reduce, invalidate]);
  useFrame((_, delta) => {
    if (orbitEnabled && reduce === false) {
      if (!holding.current && performance.now() >= resumeAt.current) {
        void controls.current?.rotate(Math.min(delta, 0.05) * Math.PI * 2 / ORBIT_SECONDS, 0, false);
      }
      invalidate();
    }
    const drawCalls = gl.info.render.calls,
      triangles = gl.info.render.triangles;
    gl.info.reset();
    if (!measureKey || measureKey === sample.current.key) return;
    const now = performance.now(),
      s = sample.current;
    if (!s.started) {
      s.started = now;
      s.previous = now;
    }
    const elapsed = now - s.started;
    if (elapsed > 300) s.deltas.push(now - s.previous);
    s.previous = now;
    if (elapsed < 5300) {

      invalidate();
    } else {
      const deltas = [...s.deltas].sort((a, b) => a - b);
      const average =
        s.deltas.reduce((a, b) => a + b, 0) / Math.max(1, s.deltas.length);
      const context = gl.getContext(),
        debug = context.getExtension("WEBGL_debug_renderer_info");
      onMeasure?.({
        fps: 1000 / average,
        p95Ms: deltas[Math.floor(deltas.length * 0.95)] ?? 0,
        frames: s.deltas.length,
        renderer: String(
          context.getParameter(
            debug?.UNMASKED_RENDERER_WEBGL ?? context.RENDERER,
          ),
        ),
        drawCalls,
        triangles,
        dpr: gl.getPixelRatio(),
      });
      sample.current = { key: measureKey, started: 0, previous: 0, deltas: [] };
    }
  });
  useEffect(() => {
    if (measureKey) invalidate();
  }, [measureKey, invalidate]);
  return (
    <CameraControls
      ref={controls}
      enabled={interactive}
      makeDefault
      smoothTime={reduce ? 0 : 0.4}
      draggingSmoothTime={0.1}
      minZoom={5}
      maxZoom={650}
      maxPolarAngle={Math.PI * 0.98}
      regress
      onUpdate={publishPose}
      onControl={holdOrbit}
      onControlEnd={() => { holding.current = false; holdOrbit(); }}
      onControlStart={() => {
        holding.current = true;
        controls.current?.stop();
        onUserControl?.();
      }}
    />
  );
}

function AdaptiveResolution() {
  const { size, setDpr } = useThree();
  const quality = useThree((state) => state.performance.current);
  useEffect(() => {
    // Presupuesto de píxeles: el coste del posprocesado no crece sin límite al maximizar.
    const budget = Math.sqrt(1_000_000 / Math.max(1, size.width * size.height));
    setDpr(Math.min(window.devicePixelRatio, 1.6, budget) * quality);
  }, [size.width, size.height, quality, setDpr]);
  return null;
}

/** Fondo del modo claro: papel gris muy claro con una retícula de puntos, como un cuaderno. */
export const LIGHT_PAPER = "#f1f3f6";
const LIGHT_DOT = "rgba(15, 23, 42, 0.18)";
const DOT_SPACING_PX = 22;

function subscribeTheme(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
  return () => observer.disconnect();
}

/** Si la página está en modo claro. Lee `data-theme` de <html>: sirve también dentro del lienzo. */
export function useLightPage(): boolean {
  return useSyncExternalStore(
    subscribeTheme,
    () => document.documentElement.dataset.theme === "light",
    () => false,
  );
}

/** Retícula de puntos como fondo de la escena, con separación fija en píxeles de pantalla. */
function dotTexture(): CanvasTexture {
  const cell = 64;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = cell;
  const context = canvas.getContext("2d");
  if (context) {
    context.fillStyle = LIGHT_PAPER;
    context.fillRect(0, 0, cell, cell);
    context.fillStyle = LIGHT_DOT;
    context.beginPath();
    context.arc(cell / 2, cell / 2, cell * 0.055, 0, Math.PI * 2);
    context.fill();
  }
  const dots = new CanvasTexture(canvas);
  dots.colorSpace = SRGBColorSpace; // sRGB: three no le aplica el mapeo de tonos
  dots.wrapS = dots.wrapT = RepeatWrapping;
  return dots;
}

function DotBackdrop() {
  const get = useThree((state) => state.get);
  const width = useThree((state) => state.size.width);
  const height = useThree((state) => state.size.height);
  const invalidate = useThree((state) => state.invalidate);
  const dots = useRef<CanvasTexture | null>(null);
  useEffect(() => {
    const texture = dotTexture();
    const { scene } = get();
    dots.current = texture;
    scene.background = texture;
    invalidate();
    return () => {
      // Al volver al modo oscuro, <color attach> ya puede haber puesto su fondo.
      if (scene.background === texture) scene.background = null;
      texture.dispose();
      dots.current = null;
    };
  }, [get, invalidate]);
  useEffect(() => {
    dots.current?.repeat.set(width / DOT_SPACING_PX, height / DOT_SPACING_PX);
    invalidate();
  }, [width, height, invalidate]);
  return null;
}

export function Studio({ effects = true }: { effects?: boolean }) {
  const room = useMemo(() => new RoomEnvironment(), []);
  const key = useRef<DirectionalLight>(null),
    rim = useRef<DirectionalLight>(null);
  const light = useLightPage();
  useEffect(() => () => room.dispose(), [room]);
  return (
    <>
      {light ? <DotBackdrop /> : <color attach="background" args={[BRAND.black]} />}
      <ambientLight intensity={0.4} color={BRAND.text} />
      <directionalLight
        ref={key}
        position={[5, 9, 7]}
        intensity={2}
        color={BRAND.text}
      />
      <directionalLight
        ref={rim}
        position={[-6, 5, -3]}
        intensity={1}
        color={BRAND.skyPale}
      />
      <Environment resolution={128} frames={1} environmentIntensity={0.65}>
        <primitive object={room} dispose={null} />
        <Lightformer
          form="ring"
          position={[-4, 5, 3]}
          rotation={[0, 0.7, 0]}
          scale={4}
          intensity={2}
          color={BRAND.text}
        />
        <Lightformer
          position={[4, 6, -4]}
          rotation={[0, -0.6, 0]}
          scale={[3, 10, 1]}
          intensity={3}
          color={BRAND.text}
        />
        <Lightformer
          position={[-5, 4, 4]}
          rotation={[0, Math.PI, 0]}
          scale={[2, 8, 1]}
          intensity={2}
          color={BRAND.skyPale}
        />
        <Lightformer
          position={[0, 9, 0]}
          rotation={[Math.PI / 2, 0, 0]}
          scale={[6, 6, 1]}
          intensity={2}
          color={BRAND.text}
        />
      </Environment>
      <ContactShadows
        position={[0, -0.025, 0]}
        opacity={0.45}
        scale={24}
        blur={2.5}
        far={15}
        frames={1}
        resolution={256}
        color={BRAND.black}
      />
      <AdaptiveResolution />
      {effects ? (
        <EffectComposer
          enableNormalPass
          multisampling={0}
          resolutionScale={0.5}
        >
          <SSAO
            resolutionScale={0.5}
            depthAwareUpsampling
            samples={8}
            rings={3}
            intensity={0.8}
            radius={0.12}
            luminanceInfluence={0.7}
          />
          <SelectiveBloom
            lights={[key, rim]}
            selectionLayer={11}
            intensity={0.55}
            luminanceThreshold={1}
            mipmapBlur
            ignoreBackground
          />
          <SMAA />
          <Vignette offset={0.3} darkness={light ? 0.12 : 0.55} />
        </EffectComposer>
      ) : null}
    </>
  );
}

class RenderBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div role="alert" className={styles.status}>
        No se pudo iniciar WebGL. Activa la aceleración gráfica o abre el visor
        en otro navegador.
      </div>
    ) : (
      this.props.children
    );
  }
}

export function SceneCanvas({
  children,
  label,
  rotating: controlledRotating,
  onRotationChange,
}: {
  children: ReactNode;
  label: string;
  rotating?: boolean;
  onRotationChange?(value: boolean): void;
}) {
  const portal = useRef<HTMLDivElement>(null),
    root = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(true);
  const [localRotating, setLocalRotating] = useState(true);
  const rotating = controlledRotating ?? localRotating;
  const setRotating = useCallback((value: boolean) => {
    setLocalRotating(value);
    onRotationChange?.(value);
  }, [onRotationChange]);
  const reduce = useReducedMotion();
  const rotation = useMemo(() => ({ enabled: active && rotating, pause: () => setRotating(false) }), [active, rotating, setRotating]);
  useEffect(() => {
    let visible = true;
    const update = () => setActive(visible && !document.hidden);
    const observer = new IntersectionObserver((entries) => {
      visible = entries[0]?.isIntersecting ?? false;
      update();
    });
    if (root.current) observer.observe(root.current);
    document.addEventListener("visibilitychange", update);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", update);
    };
  }, []);
  return (
    <div
      ref={root}
      style={{ position: "relative", height: "100%", width: "100%" }}
    >
      <RenderBoundary>
        <Canvas
          className={styles.canvas}
          orthographic
          frameloop={active ? "demand" : "never"}
          dpr={[1, 1.6]}
          camera={{ position: [12, 9, 12], zoom: 50, near: 0.01, far: 1000 }}
          performance={{ min: 0.65 }}
          gl={{ antialias: false, alpha: false, localClippingEnabled: true }}
          onCreated={({ gl }) => {
            gl.info.autoReset = false;
            gl.toneMapping = AgXToneMapping;
            gl.toneMappingExposure = 1.1;
          }}
          aria-label={label}
        >
          <Selection>
            <OrbitContext.Provider value={rotation}>
              <OverlayContext.Provider value={portal}>
                {children}
              </OverlayContext.Provider>
            </OrbitContext.Provider>
          </Selection>
        </Canvas>
        <div ref={portal} className={styles.labels} />
        <button type="button" className={`${styles.button} ${styles.orbit}`} disabled={!!reduce}
          aria-label={rotating && !reduce ? "Pausar giro de cámara 360°" : "Activar giro de cámara 360°"}
          aria-pressed={rotating && !reduce}
          title={reduce ? "Giro desactivado por movimiento reducido" : "Una vuelta por minuto · pausa al arrastrar"}
          onPointerDown={event => event.stopPropagation()}
          onPointerUp={event => event.stopPropagation()}
          onClick={event => { event.stopPropagation(); setRotating(!rotating); }}>
          {rotating && !reduce ? <Pause /> : <Play />} 360°
        </button>
      </RenderBoundary>
    </div>
  );
}

export function CameraTools({
  handle,
  container,
  onReset,
}: {
  handle: RefObject<CameraHandle | null>;
  container: RefObject<HTMLDivElement | null>;
  onReset?(): void;
}) {
  return (
    <div className={styles.tools} role="group" aria-label="Controles de cámara">
      <button
        className={styles.button}
        title="Restablecer vista"
        aria-label="Restablecer vista"
        onClick={() => (onReset ? onReset() : handle.current?.view("iso"))}
      >
        <RotateCcw />
      </button>
      <button
        className={styles.button}
        title="Acercar"
        aria-label="Acercar"
        onClick={() => handle.current?.zoom(1.25)}
      >
        <Plus />
      </button>
      <button
        className={styles.button}
        title="Alejar"
        aria-label="Alejar"
        onClick={() => handle.current?.zoom(0.8)}
      >
        <Minus />
      </button>
      <button
        className={styles.button}
        title="Capturar PNG"
        aria-label="Capturar PNG"
        onClick={() => handle.current?.capture()}
      >
        <Camera />
      </button>
      <button
        className={styles.button}
        title="Pantalla completa"
        aria-label="Pantalla completa"
        onClick={() => {
          if (document.fullscreenElement) void document.exitFullscreen();
          else void container.current?.requestFullscreen();
        }}
      >
        <Maximize />
      </button>
    </div>
  );
}

export function Legend() {
  return (
    <details className={styles.legend}>
      <summary>Estados del modelo</summary>
      <ul>
        <li>
          <span className={`${styles.swatch} ${styles.approved}`} /> Aprobado
        </li>
        <li>
          <span className={`${styles.swatch} ${styles.draft}`} /> DRAFT
        </li>
        <li>
          <span className={`${styles.swatch} ${styles.assumed}`} /> Supuesto
        </li>
        <li>
          <span className={`${styles.swatch} ${styles.changed}`} /> Cambiado Δ
        </li>
        <li>
          <span className={`${styles.swatch} ${styles.conflict}`} /> Conflicto
        </li>
      </ul>
    </details>
  );
}

export function LoadingState({
  error,
  label = "Leyendo geometría IFC en segundo plano",
}: {
  error?: string | null;
  label?: string;
}) {
  return (
    <div className={styles.status} role={error ? "alert" : "status"}>
      {!error ? <div className={styles.skeleton} aria-hidden="true" /> : null}
      <span>{error ?? label}</span>
    </div>
  );
}
