"use client";

import { BRAND } from "@/lib/brand";

import { Grid } from "@react-three/drei";
import {
  Crosshair,
  Eye,
  EyeOff,
  Layers,
  Scissors,
  TreePine,
} from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { Plane, Vector3 } from "three";
import type { Vec3 } from "@/workers/ifc-protocol";
import { AzimuthRing, Dimensions } from "./annotations";
import { useIfcModel, usePreparedModel } from "./model-resource";
import {
  explosionOffset,
  ProductMesh,
  type ElementState,
} from "./product-mesh";
import { IfcInspector } from "./inspector";
import { elementLabel } from "./semantic";
import { SectionCaps } from "./section";
import {
  CameraRig,
  CameraTools,
  Legend,
  LoadingState,
  SceneCanvas,
  SceneLabel,
  Studio,
  type CameraHandle,
  type PerformanceSample,
  type View,
} from "./stage";
import type { IfcViewerProps } from "./types";
import styles from "./viewer.module.css";

export type ExtendedViewerProps = IfcViewerProps & {
  elementStates?: Record<string, ElementState>;
  measureKey?: number;
  onMeasure?(sample: PerformanceSample): void;
  onRequestMeasure?(): void;
  performanceSample?: PerformanceSample | null;
};

export function IfcViewer({
  ifcUrl,
  selectedId,
  hoveredId,
  onSelect,
  onHover,
  annotations = [],
  view: suppliedView,
  mode: suppliedMode,
  elementStates,
  measureKey,
  onMeasure,
  onRequestMeasure,
  performanceSample,
}: ExtendedViewerProps) {
  const load = useIfcModel(ifcUrl),
    products = usePreparedModel(load.model);
  const [selection, setSelection] = useState<string>();
  const [hover, setHover] = useState<string | null>(null);
  const [view, setView] = useState<View>("iso");
  const [mode, setMode] = useState<"solid" | "xray" | "exploded">("solid");
  const [tree, setTree] = useState(false),
    [cut, setCut] = useState(false),
    [inspector, setInspector] = useState(false);
  const [cutFraction, setCutFraction] = useState(0.55),
    [isolate, setIsolate] = useState(false);
  const [hidden, setHidden] = useState<Set<string>>(() => new Set());
  const container = useRef<HTMLDivElement>(null),
    camera = useRef<CameraHandle>(null);
  const activeId = selectedId ?? selection,
    activeHover = hoveredId ?? hover;
  const activeView = suppliedView ?? view,
    activeMode = suppliedMode ?? mode;
  const model = load.model;
  const cutHeight = model
    ? model.bounds.min[1] +
      (model.bounds.max[1] - model.bounds.min[1]) * cutFraction
    : 0;
  const planes = useMemo(
    () =>
      cut && activeMode !== "exploded"
        ? [new Plane(new Vector3(0, -1, 0), cutHeight)]
        : [],
    [cut, cutHeight, activeMode],
  );
  const select = (id: string) => {
    setSelection(id);
    onSelect?.(id);
  };
  const highlight = (id: string | null) => {
    setHover(id);
    onHover?.(id);
  };
  const focus = (id: string) => {
    const product = products.find((p) => p.semanticId === id);
    if (product) camera.current?.fit(product.bounds);
  };
  const selected = products.find((p) => p.semanticId === activeId);
  const visibleProducts = useMemo(
    () =>
      products.filter(
        (p) =>
          !hidden.has(p.semanticId) && (!isolate || p.semanticId === activeId),
      ),
    [products, hidden, isolate, activeId],
  );
  const displayBounds = useMemo(() => {
    if (!model) return undefined;
    if (activeView === "top" && activeMode !== "exploded") {
      const shell = products.find((p) => p.semanticId === "shell"),
        x = shell?.center[0] ?? 0,
        z = shell?.center[2] ?? 0;
      const radius =
        Math.max(
          Math.abs(model.bounds.max[0] - x),
          Math.abs(model.bounds.min[0] - x),
          Math.abs(model.bounds.max[2] - z),
          Math.abs(model.bounds.min[2] - z),
        ) + 0.9;
      return {
        min: [x - radius, model.bounds.min[1], z - radius] as Vec3,
        max: [x + radius, model.bounds.max[1], z + radius] as Vec3,
      };
    }
    if (activeMode !== "exploded") return model.bounds;
    const low = [Infinity, Infinity, Infinity],
      high = [-Infinity, -Infinity, -Infinity];
    for (const product of products) {
      const offset = explosionOffset(product, 1);
      for (let i = 0; i < 3; i++) {
        low[i] = Math.min(low[i]!, product.bounds.min[i]! + offset[i]!);
        high[i] = Math.max(high[i]!, product.bounds.max[i]! + offset[i]!);
      }
    }
    return { min: low as Vec3, max: high as Vec3 };
  }, [model, products, activeMode, activeView]);
  return (
    <div
      className={styles.frame}
      ref={container}
      data-testid="ifc-viewer"
      data-phase={model ? "ready" : load.error ? "error" : "loading"}
      data-products={model?.products.length}
      data-triangles={model?.triangles}
      data-height={model?.bounds.max[1]}
      data-parse-ms={model?.parseMs.toFixed(2)}
    >
      {model ? (
        <SceneCanvas label="Modelo IFC sintético; usa el árbol para seleccionar componentes">
          <Studio />
          <CameraRig
            bounds={displayBounds ?? model.bounds}
            view={activeView}
            handle={camera}
            measureKey={measureKey}
            onMeasure={onMeasure}
          />
          <Grid
            position={[0, -0.015, 0]}
            args={[20, 20]}
            cellSize={0.5}
            sectionSize={2}
            cellColor={BRAND.surfaceRaised}
            sectionColor={BRAND.border}
            fadeDistance={20}
            infiniteGrid
          />
          {visibleProducts.map((product) => {
            const offset = explosionOffset(
              product,
              activeMode === "exploded" ? 1 : 0,
            );
            const position = product.center.map(
              (v, i) => v + offset[i]!,
            ) as Vec3;
            const trace = product.psets.TrazIA_Traceability;
            const status =
              elementStates?.[product.semanticId] ??
              (trace?.Draft === false && trace?.ApprovalJSON
                ? "approved"
                : "draft");
            return (
              <ProductMesh
                key={product.globalId}
                product={product}
                position={position}
                selected={product.semanticId === activeId}
                hovered={product.semanticId === activeHover}
                state={status}
                mode={activeMode}
                planes={planes}
                onSelect={select}
                onHover={highlight}
                onFocus={focus}
              />
            );
          })}
          {cut && activeMode !== "exploded" ? (
            <SectionCaps products={visibleProducts} height={cutHeight} />
          ) : null}
          {activeMode !== "exploded" ? (
            <Dimensions
              annotations={
                activeView === "top"
                  ? annotations.filter((a) => a.id === "diameter")
                  : annotations
              }
              products={products}
            />
          ) : null}
          {activeView === "top" ? <AzimuthRing model={model} /> : null}
          {selected ? (
            <SceneLabel
              position={
                selected.center.map(
                  (v, i) =>
                    v +
                    explosionOffset(
                      selected,
                      activeMode === "exploded" ? 1 : 0,
                    )[i]!,
                ) as Vec3
              }
              center
              zIndexRange={[1, 0]}
              style={{ pointerEvents: "none" }}
            >
              <span
                data-ifc-anchor={selected.semanticId}
                style={{ display: "block", width: 1, height: 1 }}
              />
            </SceneLabel>
          ) : null}
        </SceneCanvas>
      ) : (
        <LoadingState error={load.error} />
      )}
      <CameraTools
        handle={camera}
        container={container}
        onReset={() => {
          if (suppliedView) camera.current?.view(suppliedView);
          else {
            setView("iso");
            camera.current?.view("iso");
          }
        }}
      />
      <div className={styles.selectors}>
        {!suppliedView ? (
          <div className={styles.group} aria-label="Vistas guardadas">
            {(
              [
                ["iso", "Iso"],
                ["front", "Alzado"],
                ["top", "Planta"],
                ["plan", "Como el plano"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                className={styles.button}
                aria-pressed={activeView === key}
                onClick={() => setView(key)}
              >
                {label}
              </button>
            ))}
          </div>
        ) : (
          <button
            className={styles.button}
            onClick={() => camera.current?.view("plan")}
            title="Vista ortográfica alineada con el alzado"
          >
            Como el plano
          </button>
        )}
        {!suppliedMode ? (
          <select
            className={styles.select}
            aria-label="Representación del modelo"
            value={activeMode}
            onChange={(e) =>
              setMode(e.target.value as "solid" | "xray" | "exploded")
            }
          >
            <option value="solid">Sólido</option>
            <option value="xray">Rayos X</option>
            <option value="exploded">Explosionado</option>
          </select>
        ) : null}
      </div>
      <div className={styles.secondary}>
        {onRequestMeasure ? (
          <button className={styles.button} onClick={onRequestMeasure}>
            Medir 5 s
          </button>
        ) : null}
        <button
          className={styles.button}
          aria-pressed={tree}
          onClick={() => setTree((v) => !v)}
        >
          <TreePine /> Elementos
        </button>
        <button
          className={styles.button}
          aria-expanded={inspector}
          onClick={() => setInspector((v) => !v)}
        >
          Inspector IFC
        </button>
        <button
          className={styles.button}
          aria-pressed={cut && activeMode !== "exploded"}
          disabled={activeMode === "exploded"}
          onClick={() => setCut((v) => !v)}
        >
          <Scissors /> Corte
        </button>
        <button
          className={styles.button}
          disabled={!selected}
          onClick={() => selected && focus(selected.semanticId)}
          title="Encuadrar selección"
        >
          <Crosshair />
        </button>
        <button
          className={styles.button}
          disabled={!selected}
          aria-pressed={isolate}
          onClick={() => setIsolate((v) => !v)}
          title="Aislar selección"
        >
          <Layers />
        </button>
      </div>
      {cut && activeMode !== "exploded" ? (
        <label className={styles.cut}>
          Plano de corte · {cutHeight.toFixed(2)} m
          <input
            className={styles.range}
            aria-label="Altura del plano de corte"
            type="range"
            min="0"
            max="1"
            step=".005"
            value={cutFraction}
            onChange={(e) => setCutFraction(Number(e.target.value))}
          />
        </label>
      ) : null}
      {tree ? (
        <div className={styles.tree} aria-label="Árbol IFC">
          <h4>{model?.schema ?? "IFC"} / Equipo</h4>
          {products.map((product) => (
            <div key={product.globalId} className={styles.treeRow}>
              <button
                className={styles.button}
                aria-pressed={activeId === product.semanticId}
                onClick={() => select(product.semanticId)}
              >
                {elementLabel(product.semanticId)}
              </button>
              <button
                className={styles.button}
                aria-label={`${hidden.has(product.semanticId) ? "Mostrar" : "Ocultar"} ${elementLabel(product.semanticId)}`}
                onClick={() =>
                  setHidden((previous) => {
                    const next = new Set(previous);
                    if (next.has(product.semanticId))
                      next.delete(product.semanticId);
                    else next.add(product.semanticId);
                    return next;
                  })
                }
              >
                {hidden.has(product.semanticId) ? <EyeOff /> : <Eye />}
              </button>
            </div>
          ))}
          {selected ? (
            <>
              <span className={styles.small}>{selected.ifcType}</span>
              <span className={styles.small}>
                GlobalId: {selected.globalId}
              </span>
            </>
          ) : null}
          <button
            className={styles.button}
            onClick={() => {
              setHidden(new Set());
              setIsolate(false);
            }}
          >
            Mostrar todo
          </button>
        </div>
      ) : null}
      <div className={styles.caption}>
        <strong>
          {selected
            ? elementLabel(selected.semanticId)
            : "Selecciona un componente"}
        </strong>
        <br />
        {model
          ? `${model.schema} · ${model.triangles.toLocaleString("es-ES")} triángulos · sintético`
          : "Geometría leída del IFC"}
        {performanceSample ? (
          <>
            <br />
            {performanceSample.fps.toFixed(1)} fps medios · p95{" "}
            {performanceSample.p95Ms.toFixed(1)} ms
          </>
        ) : null}
      </div>
      {inspector ? (
        <IfcInspector product={selected} onClose={() => setInspector(false)} />
      ) : null}
      <Legend />
      <p className={styles.srOnly} role="status">
        {selected
          ? `${elementLabel(selected.semanticId)} seleccionado. ${selected.globalId}`
          : "Sin selección"}
      </p>
    </div>
  );
}
