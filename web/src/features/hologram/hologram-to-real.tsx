"use client";

import { Select } from "@react-three/postprocessing";
import { useFrame, useThree } from "@react-three/fiber";
import { useReducedMotion } from "motion/react";
import {
  useCallback,
  useEffect,
  useId,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type Ref,
} from "react";
import { Vector3, type Material, type ShaderMaterial } from "three";
import { cn } from "@/lib/cn";
import type { Bounds } from "@/workers/ifc-protocol";
import { AssemblyMeshes } from "../showcase3d/assembly-meshes";
import {
  equipmentGeometry,
  retainEquipment,
  type EquipmentGeometry,
  type EquipmentKind,
  type Finish,
} from "../showcase3d/equipment-geometry";
import {
  useIfcModel,
  usePreparedModel,
  type PreparedProduct,
} from "../viewer3d/model-resource";
import { retainBrushedTextures } from "../viewer3d/brushed-textures";
import {
  CameraRig,
  LoadingState,
  SceneCanvas,
  Studio,
  type CameraHandle,
  type PerformanceSample,
} from "../viewer3d/stage";
import { DetailCallouts, type DetailAnchor } from "./callouts";
import { createHologram, createRevealSurface, scanProgress } from "./materials";
import { ParticleFlow } from "./particle-flow";
import styles from "./hologram.module.css";

export type HologramToRealProps = {
  source: "procedural" | "ifc";
  layout?: "side" | "inplace";
  progress?: number;
  autoplay?: boolean;
  callouts?: boolean;
  className?: string;
  kind?: EquipmentKind;
  measureKey?: number;
  onMeasure?(sample: PerformanceSample): void;
};
type Source = {
  bounds: Bounds;
  illustration?: EquipmentGeometry;
  products?: PreparedProduct[];
  anchors: DetailAnchor[];
};
type Playback = { seek(value: number): void; play(): void; pause(): void };

function SourceMeshes({
  data,
  material,
  materials,
}: {
  data: Source;
  material?: Material;
  materials?: Partial<Record<Finish, Material>>;
}) {
  if (data.illustration)
    return (
      <AssemblyMeshes
        model={data.illustration}
        material={material}
        materials={materials}
      />
    );
  return (
    <group dispose={null}>
      {data.products?.map((product) => (
        <group key={product.globalId} position={product.center}>
          {product.geometries.map((geometry, i) => (
            <mesh
              key={i}
              geometry={geometry}
              material={
                material ??
                materials?.[
                  /bolt|perno|anchor/i.test(product.name)
                    ? "bolts"
                    : /flange|brida/i.test(product.name)
                      ? "machined"
                      : "steel"
                ]
              }
            />
          ))}
        </group>
      ))}
    </group>
  );
}

function TransitionScene({
  data,
  layout,
  progress,
  autoplay,
  showCallouts,
  reserveCallouts,
  playback,
  onProgress,
  onComplete,
  onReady,
  measureKey,
  onMeasure,
}: {
  data: Source;
  layout: "side" | "inplace";
  progress?: number;
  autoplay: boolean;
  showCallouts: boolean;
  reserveCallouts: boolean;
  playback: Ref<Playback>;
  onProgress(value: number): void;
  onComplete(): void;
  onReady(): void;
  measureKey?: number;
  onMeasure?(sample: PerformanceSample): void;
}) {
  const invalidate = useThree((s) => s.invalidate),
    reduce = useReducedMotion();
  useEffect(() => {
    onReady();
  }, [onReady]);
  const camera = useRef<CameraHandle>(null),
    flow = useRef<ShaderMaterial | null>(null);
  const registerFlow = useCallback((value: ShaderMaterial | null) => {
    flow.current = value;
  }, []);
  const minY = data.bounds.min[1],
    maxY = data.bounds.max[1],
    height = maxY - minY;
  const width = data.bounds.max[0] - data.bounds.min[0];
  const offset = layout === "side" ? Math.max(width * 0.85 + 0.8, 2.1) : 0;
  const column = offset + width / 2 + 1.6;
  const assets = useMemo(
    () => ({
      hologram: createHologram(minY, maxY),
      surfaces: {
        steel: createRevealSurface(minY, maxY),
        paint: createRevealSurface(minY, maxY, "paint"),
        machined: createRevealSurface(minY, maxY, "machined"),
        bolts: createRevealSurface(minY, maxY, "bolts"),
      },
    }),
    [minY, maxY],
  );
  const owned = useRef<typeof assets | null>(null);
  useEffect(() => {
    owned.current = assets;
    const release = retainBrushedTextures();
    return () => {
      assets.hologram.dispose();
      Object.values(assets.surfaces).forEach((s) => s.material.dispose());
      release();
    };
  }, [assets]);
  const materialMap = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(assets.surfaces).map(([key, value]) => [
          key,
          value.material,
        ]),
      ),
    [assets],
  );
  const state = useRef({
    value: progress === undefined ? 0 : scanProgress(progress),
    playing: autoplay && progress === undefined,
    done: false,
    time: 0,
    reported: -1,
  });
  useEffect(() => {
    if (progress !== undefined) {
      state.current.value = scanProgress(progress);
      state.current.playing = false;
      invalidate();
    }
  }, [progress, invalidate]);
  useImperativeHandle(
    playback,
    () => ({
      seek(value) {
        state.current.value = scanProgress(value);
        state.current.playing = false;
        state.current.done = false;
        invalidate();
      },
      play() {
        if (state.current.value >= 1) {
          state.current.value = 0;
          state.current.time = 0;
        }
        state.current.done = false;
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
  useFrame((_, delta) => {
    const s = state.current,
      resource = owned.current;
    if (!resource) return;
    if (reduce) {
      s.value = 1;
      s.playing = false;
    } else if (s.playing)
      s.value = Math.min(1, s.value + Math.min(delta, 0.05) / 2.8);
    const moving = !reduce && s.value > 0 && s.value < 1;
    if (moving) s.time += Math.min(delta, 0.05);
    resource.hologram.uniforms.uTime!.value = s.time;
    resource.hologram.uniforms.uProgress!.value =
      layout === "side" ? 0 : s.value;
    Object.values(resource.surfaces).forEach((surface) => {
      surface.uniforms.uReveal.value = s.value;
    });
    if (flow.current) {
      flow.current.uniforms.uTime!.value = s.time;
      flow.current.uniforms.uProgress!.value = s.value;
    }
    if (
      Math.abs(s.reported - s.value) > 0.003 ||
      (s.value === 1 && s.reported !== 1)
    ) {
      onProgress(s.value);
      s.reported = s.value;
    }
    if (s.value >= 1 && !s.done) {
      s.done = true;
      s.playing = false;
      onComplete();
    }
    if (s.playing || moving) invalidate();
  });
  const viewBounds = useMemo<Bounds>(
    () => ({
      min: [data.bounds.min[0] - offset, minY, data.bounds.min[2]],
      max: [
        reserveCallouts ? column + 0.8 : data.bounds.max[0] + offset,
        maxY + 0.25,
        data.bounds.max[2],
      ],
    }),
    [data, offset, minY, maxY, column, reserveCallouts],
  );
  return (
    <>
      <Studio />
      <CameraRig
        bounds={viewBounds}
        view="front"
        handle={camera}
        measureKey={measureKey}
        onMeasure={onMeasure}
      />
      <Select enabled>
        <group position={[-offset, 0, 0]}>
          <SourceMeshes data={data} material={assets.hologram} />
        </group>
      </Select>
      <Select enabled>
        <group position={[offset, 0, 0]}>
          <SourceMeshes data={data} materials={materialMap} />
        </group>
      </Select>
      {layout === "side" ? (
        <ParticleFlow
          from={-offset + width / 2}
          to={offset - width / 2}
          height={minY + height * 0.5}
          register={registerFlow}
        />
      ) : null}
      {showCallouts ? (
        <DetailCallouts
          anchors={data.anchors}
          offset={offset}
          column={column}
          height={maxY}
          reduce={!!reduce}
        >
          <SourceMeshes data={data} materials={materialMap} />
        </DetailCallouts>
      ) : null}
    </>
  );
}

function IfcSource({ children }: { children(data: Source): React.ReactNode }) {
  const loaded = useIfcModel("/demo/ifc/rev_b.ifc"),
    products = usePreparedModel(loaded.model);
  const data = useMemo<Source | null>(() => {
    if (!loaded.model) return null;
    const groups: [PreparedProduct | undefined, string][] = [
      [
        products.find((p) => /flange|brida/i.test(p.name)) ??
          products.find((p) => p.semanticId.startsWith("nozzle:")),
        "Conexión · IFC",
      ],
      [products.find((p) => p.semanticId === "skirt"), "Faldón · IFC"],
      [
        products.find((p) => /lug|orejeta|lifting/i.test(p.name)),
        "Orejetas · IFC",
      ],
    ];
    const anchors = groups.flatMap(([product, name]) =>
      product
        ? [
            {
              name,
              point: new Vector3(...product.center),
              distance: Math.max(
                0.8,
                Math.min(
                  3.5,
                  (product.bounds.max[1] - product.bounds.min[1]) * 2,
                ),
              ),
            },
          ]
        : [],
    );
    return { bounds: loaded.model.bounds, products, anchors };
  }, [loaded.model, products]);
  return data ? children(data) : <LoadingState error={loaded.error} />;
}

function ProceduralSource({
  kind,
  children,
}: {
  kind: EquipmentKind;
  children(data: Source): React.ReactNode;
}) {
  const illustration = useMemo(() => equipmentGeometry(kind), [kind]);
  useEffect(() => retainEquipment(kind), [kind]);
  const data = useMemo<Source>(
    () => ({
      illustration,
      bounds: {
        min: illustration.bounds.min.toArray() as [number, number, number],
        max: illustration.bounds.max.toArray() as [number, number, number],
      },
      anchors: (
        [
          [illustration.anchors.flange, "Brida de boquilla", 1.35],
          [
            illustration.anchors.skirt,
            kind === "horizontal" || kind === "exchanger"
              ? "Silletas"
              : kind === "tank"
                ? "Base y anclajes"
                : "Faldón y anclajes",
            1.8,
          ],
          [illustration.anchors.lug, "Orejeta de izado", 0.9],
        ] as const
      ).flatMap(([point, name, distance]) =>
        point ? [{ name, point, distance }] : [],
      ),
    }),
    [illustration, kind],
  );
  return children(data);
}

function HologramPlayer({
  source,
  layout = "side",
  progress,
  autoplay = true,
  callouts = true,
  className,
  kind = "vertical",
  measureKey,
  onMeasure,
}: HologramToRealProps) {
  const playback = useRef<Playback>(null),
    input = useRef<HTMLInputElement>(null),
    output = useRef<HTMLOutputElement>(null);
  const reduce = useReducedMotion(),
    sliderId = useId();
  const [playing, setPlaying] = useState(autoplay && progress === undefined),
    [complete, setComplete] = useState(false);
  const [ready, setReady] = useState(false);
  const onReady = useCallback(() => setReady(true), []);
  const draw = (data: Source) => (
    <SceneCanvas
      label={
        source === "ifc"
          ? "Holograma y materialización de geometría IFC sintética"
          : "Holograma ilustrativo, no procede del IFC"
      }
    >
      <TransitionScene
        data={data}
        layout={layout}
        progress={progress}
        autoplay={autoplay}
        showCallouts={
          callouts && (progress === undefined ? complete : progress >= 0.98)
        }
        reserveCallouts={callouts}
        playback={playback}
        onProgress={(value) => {
          if (input.current) input.current.value = String(value * 100);
          if (output.current)
            output.current.textContent = `${Math.round(value * 100)} %`;
        }}
        onComplete={() => {
          setPlaying(false);
          setComplete(true);
        }}
        onReady={onReady}
        measureKey={measureKey}
        onMeasure={onMeasure}
      />
    </SceneCanvas>
  );
  return (
    <div
      className={cn(styles.root, className)}
      data-source={source}
      data-layout={layout}
    >
      <div className={styles.scene}>
        {source === "ifc" ? (
          <IfcSource>{draw}</IfcSource>
        ) : (
          <ProceduralSource kind={kind}>{draw}</ProceduralSource>
        )}
      </div>
      <div className={styles.caption}>
        <span>
          {source === "ifc"
            ? "Geometría leída de rev_b.ifc · datos sintéticos"
            : "Ilustrativo · no procede del IFC"}
        </span>
        <span>Holograma → acero</span>
      </div>
      <div className={styles.controls}>
        <button
          disabled={!ready || progress !== undefined || !!reduce}
          aria-label={
            playing ? "Pausar materialización" : "Reproducir materialización"
          }
          onClick={() => {
            if (playing) playback.current?.pause();
            else {
              setComplete(false);
              playback.current?.play();
            }
            setPlaying(!playing);
          }}
        >
          {playing && !reduce ? "Pausar" : "Reproducir"}
        </button>
        <label htmlFor={sliderId}>Materialización</label>
        <input
          ref={input}
          id={sliderId}
          type="range"
          min={0}
          max={100}
          step={0.1}
          defaultValue={(progress ?? 0) * 100}
          aria-label="Progreso de materialización"
          disabled={!ready || progress !== undefined || !!reduce}
          onInput={(e) => {
            setPlaying(false);
            setComplete(false);
            playback.current?.seek(Number(e.currentTarget.value) / 100);
          }}
        />
        <output ref={output}>{Math.round((progress ?? 0) * 100)} %</output>
      </div>
    </div>
  );
}

export function HologramToReal(props: HologramToRealProps) {
  return (
    <HologramPlayer
      key={`${props.source}-${props.kind ?? "vertical"}-${props.layout ?? "side"}`}
      {...props}
    />
  );
}
