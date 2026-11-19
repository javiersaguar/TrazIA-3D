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
import { Camera, Maximize, Minimize, Minus, Plus, RotateCcw, Pause, Play } from "lucide-react";
import { useReducedMotion } from "motion/react";
import {
  Component,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
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
  PerspectiveCamera,
  RepeatWrapping,
  SRGBColorSpace,
  Sphere,
  Vector3,
  type Camera as ThreeCamera,
  type DirectionalLight,
} from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { toggleFullscreen, useFullscreenKey, useFullscreenScope, useIsFullscreen } from "@/components/shell/fullscreen";
import { BRAND } from "@/lib/brand";
import type { Bounds, Vec3 } from "@/workers/ifc-protocol";
import styles from "./viewer.module.css";
import type { CameraLink, CameraPose } from "./camera-link";
import { fitDistance, overviewFraming, type Lens, type OverviewOptions } from "./framing";
import { validPose } from "./saved-views";
import { capturePng } from "./capture";
import { toast } from "sonner";

export type View = "iso" | "front" | "top" | "plan";
export type Projection = "perspective" | "orthographic";
/** Campo de visión vertical de la cámara en perspectiva de los escenarios, en grados. */
export const PERSPECTIVE_FOV = 35;
/**
 * Vista general en perspectiva: tres cuartos y el horizonte cerca del borde superior. Con 35° de
 * campo vertical, el horizonte solo entra si la cámara se inclina menos de 17,5°; con el ojo a 21°
 * sobre el centro la planta llena el cuadro casi como una vista centrada a 24° (ver framing.test).
 */
const OVERVIEW: OverviewOptions = { azimuth: 40, elevation: 21, horizon: 0.93, margin: 1.05 };
/** Si dejar ver el horizonte aleja la cámara más que esto, la vista general se centra sin él. */
const HORIZON_COST = 1.3;
/** Encuadre calculado fuera (framing.ts): ojo, objetivo, zoom ortográfico y límites del foco. */
export type Shot = { eye: Vec3; target: Vec3; zoom?: number; focus?: Bounds };
export type CameraHandle = {
  view(v: View): void;
  fit(bounds?: Bounds, normal?: Vec3): void;
  zoom(factor: number): void;
  capture(): void;
  pose?(): CameraPose;
  restore?(pose: CameraPose): void;
  snapshot?(): Promise<{ blob: Blob; pose: CameraPose; up: Vec3; viewportHeight: number }>;
  /** Lente de la cámara actual, para calcular un encuadre. */
  lens?(): Lens;
  /** Ojo y punto de órbita actuales. */
  current?(): { eye: Vec3; target: Vec3 };
  /** Transición suave al encuadre; el objetivo pasa a ser el punto de órbita. Resuelve al llegar. */
  lookAt?(shot: Shot, smooth?: boolean): Promise<void>;
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

const PixelBudgetContext = createContext(1_000_000);
const OrbitContext = createContext({ active: true, enabled: true, pause: () => {} });

export function useSceneActivity() {
  return useContext(OrbitContext).active;
}
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

/** Cámara en perspectiva que sustituye a la ortográfica del lienzo mientras está montada. */
function PerspectiveDefault({ fov }: { fov: number }) {
  const set = useThree((state) => state.set),
    get = useThree((state) => state.get);
  const lens = useRef<PerspectiveCamera | null>(null);
  const initialFov = useRef(fov);
  useLayoutEffect(() => {
    const { camera: previous, size } = get();
    const camera = new PerspectiveCamera(initialFov.current, size.width / Math.max(1, size.height), 0.2, 5000);
    camera.position.copy(previous.position);
    camera.quaternion.copy(previous.quaternion);
    camera.updateProjectionMatrix();
    lens.current = camera;
    set({ camera });
    return () => {
      lens.current = null;
      set({ camera: previous });
    };
  }, [get, set]);
  useLayoutEffect(() => {
    if (lens.current && lens.current.fov !== fov) {
      lens.current.fov = fov;
      lens.current.updateProjectionMatrix();
    }
  }, [fov]);
  return null;
}

const isPerspective = (camera: ThreeCamera): camera is PerspectiveCamera =>
  (camera as PerspectiveCamera).isPerspectiveCamera === true;
const tanHalf = (fov: number) => Math.tan((fov * Math.PI) / 360);
const boxCorners = (box: Box3) => {
  const result: Vector3[] = [];
  for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) {
    result.push(new Vector3(x, y, z));
  }
  return result;
};
type Pending = { kind: "view"; view: View; smooth: boolean } | { kind: "refit" };

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
  framing = 1.4,
  link,
  projection = "orthographic",
  fov = PERSPECTIVE_FOV,
  groundY,
  onRest,
  onProjection,
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
  framing?: number;
  link?: CameraLink;
  /** Perspectiva solo en los escenarios; las vistas técnicas y el resto de pantallas siguen ortográficas. */
  projection?: Projection;
  /** Campo de visión vertical en perspectiva, en grados. */
  fov?: number;
  /** Cota del suelo o del agua: la vista general en perspectiva no encuadra lo que queda por debajo. */
  groundY?: number;
  /** La cámara se ha detenido después de que el usuario la moviera. */
  onRest?(): void;
  /** Proyección de la cámara activa, al montar y cada vez que cambia (ya con la pose trasladada). */
  onProjection?(projection: Projection): void;
}) {
  const controls = useRef<CameraControls>(null);
  const rotation = useContext(OrbitContext);
  const holding = useRef(false);
  const resumeAt = useRef(0);
  const orbitEnabled = orbit && rotation.enabled;
  const holdOrbit = () => { resumeAt.current = performance.now() + 6000; };
  const { camera, gl, scene, invalidate, size: viewport } = useThree();
  const reduce = useReducedMotion();
  const wantsPerspective = projection === "perspective";
  const perspective = isPerspective(camera);
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
  /** Zoom ortográfico equivalente: en perspectiva, la altura visible a la distancia del objetivo. */
  const equivalentZoom = () => {
    if (!isPerspective(camera)) return (camera as OrthographicCamera).zoom;
    const target = controls.current?.getTarget(new Vector3());
    const distance = target ? camera.position.distanceTo(target) : 1;
    return viewport.height / Math.max(1e-6, 2 * distance * tanHalf(camera.fov));
  };
  const lastPose = useRef(0);
  const publishPose = () => {
    const now = performance.now();
    if (now - lastPose.current > 100) {
      canvasNode.current?.setAttribute("data-camera-zoom", String(equivalentZoom()));
      canvasNode.current?.setAttribute("data-camera-projection", isPerspective(camera) ? "perspective" : "orthographic");
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
  const publishNow = () => {
    lastPose.current = 0;
    publishPose();
  };
  const focusBounds = useRef<Bounds | null>(null),
    focusNormal = useRef<Vec3 | undefined>(undefined);
  // Encuadre calculado fuera (lookAt): sobrevive a un cambio de límites del modelo (revisión A → B).
  const framed = useRef(false);
  // El usuario ha movido la cámara desde la última vista o encuadre: un resize no la recoloca.
  const userMoved = useRef(false);
  const controlling = useRef(false);
  const pending = useRef<Pending | null>(null);
  const sample = useRef({
    key: 0,
    started: 0,
    previous: 0,
    deltas: [] as number[],
  });
  const lens = (): Lens =>
    isPerspective(camera)
      ? { kind: "perspective", fov: camera.fov, aspect: viewport.width / Math.max(1, viewport.height) }
      : { kind: "orthographic", width: viewport.width, height: viewport.height };
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
      ) / framing;
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
    if (!smooth || reduce) controls.current?.update(0);
    if (orbitCenter && !smooth && !focusBounds.current) {
      // El centro físico prevalece sobre el espacio reservado para rótulos y recortes.
      controls.current?.update(0);
      controls.current?.setOrbitPoint(...orbitCenter);
      controls.current?.update(0);
      publishNow();
    }
    if (reduce) publishNow();
    invalidate();
  };
  /** Vista general en perspectiva: tres cuartos, elevada, la planta llenando el cuadro y algo de cielo. */
  const overview = (smooth: boolean) => {
    const box = asBox(bounds);
    if (groundY !== undefined && box.max.y > groundY + 1) box.min.y = Math.max(box.min.y, groundY);
    const center = box.getCenter(new Vector3());
    const perspectiveLens = { kind: "perspective" as const, fov, aspect: viewport.width / Math.max(1, viewport.height) };
    const points = boxCorners(box);
    const centered = overviewFraming(points, center, perspectiveLens, { ...OVERVIEW, horizon: undefined });
    const withHorizon = overviewFraming(points, center, perspectiveLens, OVERVIEW);
    const shot = withHorizon && (!centered || withHorizon.distance <= centered.distance * HORIZON_COST) ? withHorizon : centered;
    if (!shot) return false;
    const move = smooth && !reduce;
    void controls.current?.setLookAt(...(shot.eye.toArray() as Vec3), ...(shot.target.toArray() as Vec3), move);
    if (!move) {
      controls.current?.update(0);
      publishNow();
    }
    invalidate();
    return true;
  };
  const show = (next: View, smooth: boolean) => {
    if (isPerspective(camera) && next === "iso" && overview(smooth)) return;
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
  /** Reajuste tras un cambio de tamaño del visor. */
  const refit = (currentView: View) => {
    if (!isPerspective(camera)) {
      fitCurrent(focusBounds.current ?? bounds, false);
      return;
    }
    // En perspectiva el aspecto se actualiza solo; se recoloca si nadie ha movido la cámara.
    if (userMoved.current) return;
    if (!focusBounds.current) {
      show(currentView, false);
      return;
    }
    const box = asBox(focusBounds.current),
      center = box.getCenter(new Vector3());
    const direction = camera.position.clone().sub(controls.current?.getTarget(new Vector3()) ?? center).normalize();
    const { distance } = fitDistance(box, direction, lens(), 1.3);
    const eye = center.clone().addScaledVector(direction, distance);
    void controls.current?.setLookAt(eye.x, eye.y, eye.z, center.x, center.y, center.z, false);
    controls.current?.update(0);
    publishNow();
    invalidate();
  };
  const run = (request: Pending) => {
    if (request.kind === "refit") refit(configured.current.view);
    else {
      focusBounds.current = null;
      focusNormal.current = undefined;
      framed.current = false;
      userMoved.current = false;
      show(request.view, request.smooth);
    }
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
    let request: Pending | null = null;
    if (
      !previous.initialized ||
      previous.view !== view ||
      (previous.boundsKey !== boundsKey && !framed.current)
    ) {
      request = { kind: "view", view, smooth: previous.initialized && previous.view !== view };
    } else if (
      previous.width !== viewport.width ||
      previous.height !== viewport.height
    ) {
      request = { kind: "refit" };
    }
    configured.current = {
      view,
      boundsKey,
      width: viewport.width,
      height: viewport.height,
      initialized: true,
    };
    // Con un cambio de proyección pendiente, la vista se aplica a la cámara nueva.
    if (request) {
      if (wantsPerspective !== perspective) pending.current = request;
      else run(request);
    }
    // Una nueva vista tiene prioridad sobre el resize; un resize conserva el foco del cambio.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, boundsKey, viewport.width, viewport.height]);
  // Cambio de proyección: la cámara nueva hereda dirección y objetivo con la misma altura visible.
  const seenCamera = useRef<ThreeCamera>(camera);
  const seenControls = useRef<CameraControls | null>(null);
  useEffect(() => {
    const previous = seenCamera.current,
      previousControls = seenControls.current,
      next = controls.current;
    seenCamera.current = camera;
    seenControls.current = next;
    if (previous === camera || !next) {
      onProjection?.(isPerspective(camera) ? "perspective" : "orthographic");
      return;
    }
    const target = previousControls?.getTarget(new Vector3()) ?? asBox(bounds).getCenter(new Vector3());
    const offset = previous.position.clone().sub(target);
    const direction = offset.lengthSq() > 1e-8 ? offset.normalize() : new Vector3(0.6, 0.5, 0.6).normalize();
    const height = Math.max(1, viewport.height);
    const visible = isPerspective(previous)
      ? 2 * previous.position.distanceTo(target) * tanHalf(previous.fov)
      : height / Math.max(1e-6, (previous as OrthographicCamera).zoom);
    if (isPerspective(camera)) {
      const eye = target.clone().addScaledVector(direction, visible / (2 * tanHalf(camera.fov)));
      void next.setLookAt(eye.x, eye.y, eye.z, target.x, target.y, target.z, false);
    } else {
      // El ojo ortográfico se aleja lo bastante para que el plano cercano no recorte la planta.
      const radius = asBox(bounds).getBoundingSphere(new Sphere()).radius;
      const eye = target.clone().addScaledVector(direction, Math.max(20, radius * 2.5));
      void next.setLookAt(eye.x, eye.y, eye.z, target.x, target.y, target.z, false);
      void next.zoomTo(Math.min(650, Math.max(5, height / Math.max(visible, 1e-3))), false);
    }
    next.update(0);
    const request = pending.current;
    pending.current = null;
    if (request) run(request);
    publishNow();
    invalidate();
    onProjection?.(isPerspective(camera) ? "perspective" : "orthographic");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [camera]);
  const poseNow = (): CameraPose => ({
    eye: camera.position.toArray() as Vec3,
    target: (controls.current?.getTarget(new Vector3()) ?? new Vector3()).toArray() as Vec3,
    zoom: equivalentZoom(),
    projection: isPerspective(camera) ? "perspective" : "orthographic",
  });
  useImperativeHandle(handle, () => ({
    snapshot: async () => {
      gl.render(scene, camera);
      const pose = poseNow();
      const up = new Vector3(0, 1, 0).applyQuaternion(camera.quaternion).toArray() as Vec3;
      return { blob: await capturePng(gl.domElement), pose, up, viewportHeight: viewport.height };
    },
    pose: poseNow,
    restore: (pose) => {
      if (!validPose(pose)) return;
      rotation.pause(); controls.current?.stop();
      framed.current = false;
      focusBounds.current = null;
      userMoved.current = true;
      if (isPerspective(camera)) {
        // La distancia sale del zoom equivalente: sirve igual para vistas guardadas en ortográfica.
        const target = new Vector3(...pose.target);
        const direction = new Vector3(...pose.eye).sub(target).normalize();
        const eye = target.clone().addScaledVector(direction, viewport.height / (2 * pose.zoom * tanHalf(camera.fov)));
        void controls.current?.setLookAt(eye.x, eye.y, eye.z, ...pose.target, !reduce);
      } else {
        void controls.current?.setLookAt(...pose.eye, ...pose.target, !reduce);
        void controls.current?.zoomTo(pose.zoom, !reduce);
      }
      invalidate();
    },
    view: (next) => {
      rotation.pause();
      if (wantsPerspective !== perspective) {
        pending.current = { kind: "view", view: next, smooth: true };
        return;
      }
      run({ kind: "view", view: next, smooth: true });
    },
    fit: (target, normal) => {
      holdOrbit();
      framed.current = false;
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
    lens,
    current: () => ({
      eye: camera.position.toArray() as Vec3,
      target: (controls.current?.getTarget(new Vector3()) ?? new Vector3()).toArray() as Vec3,
    }),
    lookAt: (shot, smooth = true) => {
      holdOrbit();
      controls.current?.stop();
      framed.current = !!shot.focus;
      focusBounds.current = shot.focus ?? null;
      focusNormal.current = undefined;
      userMoved.current = false;
      const move = smooth && !reduce;
      const arrived = [controls.current?.setLookAt(...shot.eye, ...shot.target, move)];
      if (shot.zoom !== undefined && !isPerspective(camera)) {
        arrived.push(controls.current?.zoomTo(Math.min(650, Math.max(5, shot.zoom)), move));
      }
      if (!move) {
        controls.current?.update(0);
        publishNow();
      }
      invalidate();
      return Promise.all(arrived).then(() => {
        publishNow();
      });
    },
    zoom: (factor) => {
      holdOrbit();
      if (isPerspective(camera)) {
        // En perspectiva acercar es avanzar (dolly) hacia el objetivo.
        const distance = controls.current?.distance ?? 1;
        void controls.current?.dollyTo(distance / factor, !reduce);
      } else {
        void controls.current?.zoomTo(
          (camera as OrthographicCamera).zoom * factor,
          !reduce,
        );
      }
      invalidate();
    },
    capture: () => {
      gl.render(scene, camera);
      void capturePng(gl.domElement).then((blob) => {
        const url = URL.createObjectURL(blob),
          link = document.createElement("a");
        link.href = url;
        link.download = "trazia-ifc.png";
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }).catch(error => toast.error(error instanceof Error ? error.message : "No se pudo capturar el visor"));
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
  const radius = useMemo(() => asBox(bounds).getBoundingSphere(new Sphere()).radius, [bounds]);
  return (
    <>
      {wantsPerspective ? <PerspectiveDefault fov={fov} /> : null}
      <CameraControls
        ref={controls}
        enabled={interactive}
        makeDefault
        smoothTime={reduce ? 0 : 0.25}
        draggingSmoothTime={0.1}
        minZoom={5}
        maxZoom={650}
        minDistance={perspective ? 0.6 : Number.EPSILON}
        maxDistance={perspective ? Math.max(80, radius * 7) : Infinity}
        dollyToCursor={perspective}
        // En perspectiva la cámara no baja del horizonte: debajo solo hay agua o terreno.
        maxPolarAngle={perspective ? Math.PI * 0.475 : Math.PI * 0.98}
        regress
        onUpdate={publishPose}
        onControl={holdOrbit}
        onControlEnd={() => { holding.current = false; holdOrbit(); }}
        onControlStart={() => {
          holding.current = true;
          controlling.current = true;
          userMoved.current = true;
          controls.current?.stop();
          onUserControl?.();
        }}
        onRest={() => {
          if (!controlling.current) return;
          controlling.current = false;
          publishNow();
          onRest?.();
        }}
      />
    </>
  );
}

export function AdaptiveResolution() {
  const { size, setDpr } = useThree();
  const pixelBudget = useContext(PixelBudgetContext);
  const quality = useThree((state) => state.performance.current);
  useEffect(() => {
    // Presupuesto de píxeles: el coste del posprocesado no crece sin límite al maximizar.
    const budget = Math.sqrt(pixelBudget / Math.max(1, size.width * size.height));
    setDpr(Math.min(window.devicePixelRatio, 1.6, budget) * quality);
  }, [size.width, size.height, quality, setDpr, pixelBudget]);
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

export function Studio({ effects = true, stage = true }: { effects?: boolean; stage?: boolean }) {
  const room = useMemo(() => new RoomEnvironment(), []);
  const key = useRef<DirectionalLight>(null),
    rim = useRef<DirectionalLight>(null);
  const light = useLightPage();
  useEffect(() => () => room.dispose(), [room]);
  return (
    <>
      {stage ? (light ? <DotBackdrop /> : <color attach="background" args={[BRAND.black]} />) : null}
      <ambientLight intensity={0.4} color={BRAND.text} />
      <directionalLight
        ref={key}
        position={stage ? [5, 9, 7] : [38, 75, 40]}
        castShadow={!stage}
        shadow-mapSize={[1024, 1024]}
        shadow-camera-left={-48}
        shadow-camera-right={48}
        shadow-camera-top={42}
        shadow-camera-bottom={-42}
        shadow-camera-far={155}
        shadow-normalBias={0.055}
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
      {stage ? <ContactShadows
        position={[0, -0.025, 0]}
        opacity={0.45}
        scale={24}
        blur={2.5}
        far={15}
        frames={1}
        resolution={256}
        color={BRAND.black}
      /> : null}
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
  rotationControl = true,
  pixelBudget = 1_000_000,
  initialRotating = true,
  shadows = false,
  onPointerMissed,
}: {
  pixelBudget?: number;
  children: ReactNode;
  label: string;
  rotationControl?: boolean;
  rotating?: boolean;
  initialRotating?: boolean;
  shadows?: boolean;
  onRotationChange?(value: boolean): void;
  /** Clic (sin arrastre) que no ha tocado ningún objeto con eventos. */
  onPointerMissed?(event: MouseEvent): void;
}) {
  const portal = useRef<HTMLDivElement>(null),
    root = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(true);
  const [localRotating, setLocalRotating] = useState(initialRotating);
  const rotating = controlledRotating ?? localRotating;
  const setRotating = useCallback((value: boolean) => {
    setLocalRotating(value);
    onRotationChange?.(value);
  }, [onRotationChange]);
  const reduce = useReducedMotion();
  const rotation = useMemo(() => ({ active, enabled: active && rotating, pause: () => setRotating(false) }), [active, rotating, setRotating]);
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
      data-scene-active={active}
      data-pixel-budget={pixelBudget}
      style={{ position: "relative", height: "100%", width: "100%" }}
    >
      <RenderBoundary>
        <Canvas
          className={styles.canvas}
          shadows={shadows ? "percentage" : false}
          orthographic
          frameloop={active ? "demand" : "never"}
          dpr={[1, 1.6]}
          camera={{ position: [12, 9, 12], zoom: 50, near: 0.01, far: 1000 }}
          performance={{ min: 0.65 }}
          gl={{ antialias: shadows, alpha: false, localClippingEnabled: true }}
          onCreated={({ gl }) => {
            gl.info.autoReset = false;
            gl.toneMapping = AgXToneMapping;
            gl.toneMappingExposure = 1.1;
          }}
          onPointerMissed={onPointerMissed}
          aria-label={label}
        >
          <Selection>
            <PixelBudgetContext.Provider value={pixelBudget}>
            <OrbitContext.Provider value={rotation}>
              <OverlayContext.Provider value={portal}>
                {children}
              </OverlayContext.Provider>
            </OrbitContext.Provider>
            </PixelBudgetContext.Provider>
          </Selection>
        </Canvas>
        <div ref={portal} className={styles.labels} />
        {rotationControl ? <button type="button" className={`${styles.button} ${styles.orbit}`} disabled={!!reduce}
          aria-label={rotating && !reduce ? "Pausar giro de cámara 360°" : "Activar giro de cámara 360°"}
          aria-pressed={rotating && !reduce}
          title={reduce ? "Giro desactivado por movimiento reducido" : "Una vuelta por minuto · pausa al arrastrar"}
          onPointerDown={event => event.stopPropagation()}
          onPointerUp={event => event.stopPropagation()}
          onClick={event => { event.stopPropagation(); setRotating(!rotating); }}>
          {rotating && !reduce ? <Pause /> : <Play />} 360°
        </button> : null}
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
  // Dentro de un marco (FullscreenFrame, presentación de Cambios) se amplía el marco entero
  const scope = useFullscreenScope();
  const own = useIsFullscreen(container);
  useFullscreenKey(container, undefined, !scope);
  const fullscreen = scope ? scope.active : own;
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
        title={fullscreen ? "Salir de pantalla completa (F o Esc)" : "Pantalla completa (F)"}
        aria-label={fullscreen ? "Salir de pantalla completa" : "Pantalla completa"}
        aria-pressed={fullscreen}
        onClick={() => (scope ? scope.toggle() : toggleFullscreen(container.current))}
      >
        {fullscreen ? <Minimize /> : <Maximize />}
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
