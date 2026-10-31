"use client";

import { Grid, Line } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import { Eye, LocateFixed, Pause, Play, SkipForward } from "lucide-react";
import { useReducedMotion } from "motion/react";
import {
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type Ref,
} from "react";
import type { Bounds } from "@/workers/ifc-protocol";
import { BRAND } from "@/lib/brand";
import { useSelection } from "@/stores/selection";
import { CameraLink } from "../viewer3d/camera-link";
import {
  useIfcModel,
  usePreparedModel,
  type PreparedProduct,
} from "../viewer3d/model-resource";
import { ProductMesh } from "../viewer3d/product-mesh";
import {
  CameraRig,
  CameraTools,
  LoadingState,
  SceneCanvas,
  SceneLabel,
  Studio,
  type CameraHandle,
} from "../viewer3d/stage";
import type { RevisionMorphProps } from "../viewer3d/types";
import { parentElementId } from "../viewer3d/semantic";
import { AnimatedPair, type TimelineSnapshot } from "./animated-pair";
import {
  changeSteps,
  clampProgress,
  dimensionText,
  pairByGlobalId,
  segmentProgress,
  SEGMENT_SECONDS,
  timelineAt,
  type ChangeStep,
} from "./morph";
import styles from "../viewer3d/viewer.module.css";
import deltaStyles from "./timeline.module.css";

type Playback = { seek(value: number): void; play(): void; pause(): void };
type Props = RevisionMorphProps & {
  showNarration?: boolean;
  playing?: boolean;
  speed?: number;
  split?: boolean;
  onStep?(id: string, index: number): void;
  onPlayingChange?(value: boolean): void;
};

function Dimension({
  step,
  product,
  read,
  index,
  count,
}: {
  step: ChangeStep;
  product: PreparedProduct;
  read(): TimelineSnapshot;
  index: number;
  count: number;
}) {
  const label = useRef<HTMLSpanElement>(null),
    group = useRef<import("three").Group>(null);
  const position = [
    product.bounds.max[0] + 0.65,
    product.center[1],
    product.bounds.max[2] + 0.3,
  ] as [number, number, number];
  useFrame(() => {
    const value = read().value,
      active = timelineAt(value, count).index === index;
    if (group.current) group.current.visible = active;
    if (label.current) {
      label.current.style.display = active ? "block" : "none";
      label.current.textContent = dimensionText(
        step,
        segmentProgress(value, index, count),
      );
    }
  });
  return (
    <group ref={group}>
      <Line
        points={[product.center, position]}
        color={BRAND.revision}
        dashed
        dashSize={0.07}
        gapSize={0.05}
      />
      <SceneLabel
        position={position}
        center
        zIndexRange={[8, 0]}
        style={{ pointerEvents: "none" }}
      >
        <span ref={label} className={styles.delta}>
          Δ {step.label}
        </span>
      </SceneLabel>
    </group>
  );
}

function TimelineScene({
  a,
  b,
  bounds,
  steps,
  progress,
  playing,
  speed,
  ghost,
  follow,
  selectedId,
  hoveredId,
  onlyChanged,
  playback,
  camera,
  onTick,
  onStep,
  onStop,
  onSelect,
  onHover,
}: {
  a: PreparedProduct[];
  b: PreparedProduct[];
  bounds: Bounds;
  steps: ChangeStep[];
  progress?: number;
  playing: boolean;
  speed: number;
  ghost: boolean;
  follow: boolean;
  selectedId: string | null;
  hoveredId: string | null;
  onlyChanged: boolean;
  playback: Ref<Playback>;
  camera: Ref<CameraHandle>;
  onTick(value: number): void;
  onStep(index: number): void;
  onStop(): void;
  onSelect(id: string): void;
  onHover(id: string | null): void;
}) {
  const invalidate = useThree((s) => s.invalidate),
    reduced = useReducedMotion();
  const rig = useRef<CameraHandle>(null);
  const state = useRef<TimelineSnapshot>({
    value: progress ?? 0,
    playing,
    speed,
  });
  const last = useRef(-1),
    report = useRef(-1);
  const read = useCallback(() => state.current, []);
  const pairs = useMemo(() => pairByGlobalId(a, b), [a, b]);
  const count = Math.max(1, steps.length);
  const focusProduct = useCallback((product: PreparedProduct) => {
    const horizontal = Math.hypot(product.center[0], product.center[2]);
    const normal = parentElementId(product.semanticId).startsWith("nozzle:")
      ? ((horizontal > 0.01
          ? [product.center[0] / horizontal, 0, product.center[2] / horizontal]
          : [0, 1, 0]) as [number, number, number])
      : undefined;
    rig.current?.fit(product.bounds, normal);
  }, []);
  useEffect(() => {
    state.current.speed = speed;
  }, [speed]);
  useEffect(() => {
    state.current.playing = playing;
    if (playing) last.current = -1;
    if (playing && state.current.value >= 1) state.current.value = 0;
    invalidate();
  }, [playing, invalidate]);
  useEffect(() => {
    if (progress !== undefined) {
      state.current.value = clampProgress(progress);
      state.current.playing = false;
      invalidate();
    }
  }, [progress, invalidate]);
  useEffect(() => {
    if (follow && selectedId) {
      const p =
        b.find((p) => p.semanticId === selectedId) ??
        a.find((p) => p.semanticId === selectedId);
      if (p) focusProduct(p);
    }
  }, [follow, selectedId, a, b, focusProduct]);
  useImperativeHandle(
    playback,
    () => ({
      seek(value) {
        state.current.value = clampProgress(value);
        state.current.playing = false;
        invalidate();
      },
      play() {
        if (state.current.value >= 1) state.current.value = 0;
        state.current.playing = true;
        invalidate();
      },
      pause() {
        state.current.playing = false;
        invalidate();
      },
    }),
    [invalidate],
  );
  useImperativeHandle(
    camera,
    () => ({
      view: (v) => rig.current?.view(v),
      fit: (v, n) => rig.current?.fit(v, n),
      zoom: (v) => rig.current?.zoom(v),
      capture: () => rig.current?.capture(),
    }),
    [],
  );
  useFrame((_, delta) => {
    const s = state.current;
    if (reduced) {
      s.value = 1;
      if (s.playing) {
        s.playing = false;
        onStop();
      }
    } else if (s.playing)
      s.value = Math.min(
        1,
        s.value + (Math.min(delta, 0.05) * s.speed) / (SEGMENT_SECONDS * count),
      );
    const { index } = timelineAt(s.value, count);
    if (index !== last.current) {
      last.current = index;
      onStep(index);
      if (follow && (s.playing || s.value > 0)) {
        const step = steps[index],
          p =
            b.find((p) => p.semanticId === step?.elementId) ??
            a.find((p) => p.semanticId === step?.elementId);
        if (p) focusProduct(p);
      }
    }
    if (report.current !== s.value) {
      onTick(s.value);
      report.current = s.value;
    }
    if (s.playing) {
      if (s.value >= 1) {
        s.playing = false;
        onStop();
      } else invalidate();
    }
  });
  const changed = (pair: (typeof pairs)[number]) =>
    !pair.before ||
    !pair.after ||
    pair.before.bounds.min.some(
      (v, i) => Math.abs(v - pair.after!.bounds.min[i]!) > 1e-6,
    ) ||
    pair.before.bounds.max.some(
      (v, i) => Math.abs(v - pair.after!.bounds.max[i]!) > 1e-6,
    ) ||
    steps.some(
      (s) =>
        s.geometry &&
        s.elementId ===
          parentElementId((pair.after ?? pair.before)!.semanticId),
    );
  return (
    <>
      <Studio />
      <CameraRig
        bounds={bounds}
        handle={rig}
        orbit={!playing}
        onUserControl={() => {
          state.current.playing = false;
          onStop();
        }}
      />
      <Grid
        position={[0, -0.02, 0]}
        args={[16, 16]}
        cellSize={0.5}
        sectionSize={2}
        cellColor={BRAND.surfaceRaised}
        sectionColor={BRAND.border}
        fadeDistance={18}
      />
      {ghost
        ? a
            .filter(
              (p) =>
                !onlyChanged ||
                pairs.some(
                  (pair) => pair.globalId === p.globalId && changed(pair),
                ),
            )
            .map((p) => (
              <ProductMesh
                key={`ghost-${p.globalId}`}
                product={p}
                opacity={0.1}
                color={BRAND.skyDeep}
                wireframe
                immediate
              />
            ))
        : null}
      {pairs
        .filter((pair) => !onlyChanged || changed(pair))
        .map((pair) => {
          const id = (pair.after ?? pair.before)!.semanticId;
          let index = steps.findIndex(
            (s) => s.elementId === parentElementId(id),
          );
          if (index < 0)
            index = Math.max(
              0,
              steps.findIndex((s) => s.elementId === "shell"),
            );
          return (
            <AnimatedPair
              key={pair.globalId}
              pair={pair}
              index={index}
              count={count}
              changed={changed(pair)}
              showSweep={!id.startsWith("detail:")}
              selected={selectedId === id || selectedId === parentElementId(id)}
              hovered={hoveredId === id || hoveredId === parentElementId(id)}
              read={read}
              onSelect={onSelect}
              onHover={onHover}
            />
          );
        })}
      {steps.map((step, index) => {
        const p =
          b.find((p) => p.semanticId === step.elementId) ??
          a.find((p) => p.semanticId === step.elementId);
        return p ? (
          <Dimension
            key={step.id}
            step={step}
            product={p}
            read={read}
            index={index}
            count={count}
          />
        ) : null;
      })}
    </>
  );
}

export function RevisionMorph({
  fromUrl,
  toUrl,
  changes,
  progress,
  playing: externalPlaying,
  speed = 1,
  split = false,
  onProgress,
  onStep,
  onPlayingChange,
  showNarration = true,
}: Props) {
  const before = useIfcModel(fromUrl),
    after = useIfcModel(toUrl),
    a = usePreparedModel(before.model),
    b = usePreparedModel(after.model);
  const [ownPlaying, setOwnPlaying] = useState(false),
    [follow, setFollow] = useState(true),
    [ghost, setGhost] = useState(true),
    [stepIndex, setStepIndex] = useState(0),
    [ownSpeed, setSpeed] = useState(speed);
  const playing = externalPlaying ?? ownPlaying;
  const root = useRef<HTMLDivElement>(null),
    camera = useRef<CameraHandle>(null),
    playback = useRef<Playback>(null),
    range = useRef<HTMLInputElement>(null),
    output = useRef<HTMLOutputElement>(null),
    badge = useRef<HTMLDivElement>(null);
  const selectedId = useSelection((s) => s.selectedId),
    setSelected = useSelection((s) => s.setSelected),
    hoveredId = useSelection((s) => s.hoveredId),
    setHovered = useSelection((s) => s.setHovered);
  const [onlyChanged, setOnlyChanged] = useState(false);
  const [orbiting, setOrbiting] = useState(true);
  const steps = useMemo(() => changeSteps(changes), [changes]);
  const link = useMemo(() => new CameraLink(), []);
  const bounds = useMemo<Bounds>(
    () => ({
      min: [
        Math.min(
          before.model?.bounds.min[0] ?? 0,
          after.model?.bounds.min[0] ?? 0,
        ),
        0,
        Math.min(
          before.model?.bounds.min[2] ?? 0,
          after.model?.bounds.min[2] ?? 0,
        ),
      ],
      max: [
        Math.max(
          before.model?.bounds.max[0] ?? 2,
          after.model?.bounds.max[0] ?? 2,
        ),
        Math.max(
          before.model?.bounds.max[1] ?? 8,
          after.model?.bounds.max[1] ?? 8,
        ),
        Math.max(
          before.model?.bounds.max[2] ?? 2,
          after.model?.bounds.max[2] ?? 2,
        ),
      ],
    }),
    [before.model, after.model],
  );
  const modifiedIds = useMemo(
    () =>
      new Set(
        pairByGlobalId(a, b)
          .filter(
            (pair) =>
              !pair.before ||
              !pair.after ||
              JSON.stringify(pair.before.bounds) !==
                JSON.stringify(pair.after.bounds) ||
              steps.some(
                (s) =>
                  s.geometry &&
                  s.elementId ===
                    parentElementId((pair.after ?? pair.before)!.semanticId),
              ),
          )
          .map((pair) => (pair.after ?? pair.before)!.semanticId),
      ),
    [a, b, steps],
  );
  const setPlaying = (v: boolean) => {
    setOwnPlaying(v);
    onPlayingChange?.(v);
  };
  const stop = () => setPlaying(false);
  const seek = (value: number) => {
    stop();
    playback.current?.seek(value);
    onProgress?.(value);
  };
  const ready = !!before.model && !!after.model;
  const tick = (value: number) => {
    if (range.current) range.current.value = String(value);
    if (output.current)
      output.current.textContent = `${Math.round(value * 100)} %`;
    root.current?.setAttribute("data-progress", value.toFixed(3));
    if (badge.current)
      badge.current.textContent = `${value === 1 ? "IFC B exacto" : value === 0 ? "IFC A exacto" : "Interpolación ilustrativa"} · sintético`;
  };
  const step = steps[stepIndex];
  return (
    <div
      ref={root}
      className={styles.frame}
      data-testid="revision-morph"
      data-phase={ready ? "ready" : "loading"}
      data-progress="0"
    >
      {ready ? (
        split ? (
          <div className={deltaStyles.split}>
            {[a, b].map((products, i) => (
              <div key={i} className={deltaStyles.half}>
                <span className={deltaStyles.revision}>
                  rev {i ? "B" : "A"} · IFC exacto
                </span>
                <SceneCanvas
                  label={`IFC ${i ? "B" : "A"} sintético, cámaras sincronizadas`}
                  rotating={orbiting}
                  onRotationChange={setOrbiting}
                >
                  <Studio />
                  <CameraRig
                    bounds={bounds}
                    handle={i ? null : camera}
                    link={link}
                    orbit={i === 0}
                    onUserControl={() => setOrbiting(false)}
                  />
                  {products
                    .filter(
                      (p) => !onlyChanged || modifiedIds.has(p.semanticId),
                    )
                    .map((p) => (
                      <ProductMesh
                        key={p.globalId}
                        product={p}
                        selected={p.semanticId === selectedId}
                        hovered={p.semanticId === hoveredId}
                        onSelect={(id) => setSelected(id)}
                        onHover={setHovered}
                      />
                    ))}
                </SceneCanvas>
              </div>
            ))}
          </div>
        ) : (
          <SceneCanvas label="Comparación de IFC sintéticos A y B emparejados por GlobalId">
            <TimelineScene
              a={a}
              b={b}
              bounds={bounds}
              steps={steps}
              progress={progress}
              playing={playing}
              speed={ownSpeed}
              ghost={ghost}
              follow={follow}
              selectedId={selectedId}
              hoveredId={hoveredId}
              onlyChanged={onlyChanged}
              playback={playback}
              camera={camera}
              onTick={tick}
              onStep={(i) => {
                setStepIndex(i);
                const s = steps[i];
                if (s) {
                  onStep?.(s.elementId, i);
                  if (playing) setSelected(s.elementId);
                }
              }}
              onStop={stop}
              onSelect={(id) => {
                stop();
                setSelected(id);
              }}
              onHover={setHovered}
            />
          </SceneCanvas>
        )
      ) : (
        <LoadingState error={before.error ?? after.error} />
      )}
      <CameraTools handle={camera} container={root} />
      <div
        className={styles.selectors}
        role="group"
        aria-label="Cámara de revisiones"
      >
        <button
          className={styles.button}
          aria-pressed={!follow}
          onClick={() => {
            setFollow(false);
            camera.current?.view("iso");
          }}
        >
          <Eye /> Vista general
        </button>
        <button
          className={styles.button}
          aria-pressed={follow}
          onClick={() => setFollow((v) => !v)}
        >
          <LocateFixed /> Seguir el cambio
        </button>
        <button
          className={styles.button}
          aria-pressed={onlyChanged}
          onClick={() => setOnlyChanged((v) => !v)}
        >
          Solo modificados
        </button>
        <button
          className={styles.button}
          aria-pressed={ghost}
          onClick={() => setGhost((v) => !v)}
        >
          Fantasma A
        </button>
      </div>
      <div ref={badge} className={styles.badge}>
        {split ? "IFC A | B exactos · sintético" : "IFC A exacto · sintético"}
      </div>
      {!split ? (
        <div className={deltaStyles.transport}>
          <div className={deltaStyles.marks}>
            {steps.map((s, i) => (
              <button
                key={s.id}
                aria-label={`Ir al cambio ${i + 1}: ${s.narration}`}
                onClick={() => seek(i / steps.length)}
                title={s.narration}
              >
                {i + 1}
              </button>
            ))}
          </div>
          <label className={deltaStyles.scrub}>
            A
            <input
              ref={range}
              className={styles.range}
              type="range"
              min="0"
              max="1"
              step=".001"
              defaultValue={progress ?? 0}
              aria-label="Interpolación IFC de A a B"
              disabled={!ready}
              onInput={(e) => seek(Number(e.currentTarget.value))}
            />
            B<output ref={output}>0 %</output>
          </label>
          {showNarration ? (
            <div className={deltaStyles.narration}>
              <button
                className={styles.button}
                disabled={!ready}
                aria-label={playing ? "Pausar morph" : "Reproducir morph"}
                onClick={() => {
                  if (playing) playback.current?.pause();
                  else playback.current?.play();
                  setPlaying(!playing);
                }}
              >
                {playing ? <Pause /> : <Play />}
              </button>
              <p>
                <strong>
                  {step
                    ? `Cambio ${stepIndex + 1} de ${steps.length}`
                    : "Revisiones A → B"}
                </strong>
                {step?.narration ??
                  "Arrastra el avance para comparar las dos revisiones IFC."}
              </p>
              <label className={deltaStyles.speed}>
                Velocidad
                <select
                  aria-label="Velocidad de los cambios"
                  value={ownSpeed}
                  onChange={(e) => setSpeed(Number(e.target.value))}
                >
                  {[0.5, 1, 2].map((v) => (
                    <option key={v} value={v}>
                      {v.toLocaleString("es-ES")}×
                    </option>
                  ))}
                </select>
              </label>
              <button
                className={styles.button}
                aria-label="Siguiente cambio"
                onClick={() =>
                  seek(Math.min(1, (stepIndex + 1) / Math.max(1, steps.length)))
                }
              >
                <SkipForward />
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
