"use client";

import { BRAND } from "@/lib/brand";
import { apiEnabled, apiURL } from "@/lib/api/config";
import { toast } from "sonner";

import { Grid, Line } from "@react-three/drei";
import { useReducedMotion } from "motion/react";
import {
  Box,
  Crosshair,
  Eye,
  EyeOff,
  Layers,
  Scissors,
  TreePine,
} from "lucide-react";
import { useEffect, useEffectEvent, useMemo, useRef, useState, type ReactNode } from "react";
import { Box3, Plane, Vector3 } from "three";
import { isTyping } from "@/components/shell/global-keys";
import type { Bounds, Vec3 } from "@/workers/ifc-protocol";
import { AzimuthRing, Dimensions } from "./annotations";
import { chooseFraming, type Sample } from "./framing";
import { FOCUS_SAMPLES, focusMargin, ghostsFor, placedBox, unionBox } from "./focus";
import { buildHierarchy, clickTarget, levelUp, type Hierarchy, type HierarchyNode } from "./hierarchy";
import { useIfcModel, usePreparedModel } from "./model-resource";
import { OcclusionIndex } from "./occlusion";
import {
  explosionOffset,
  ProductMesh,
  type ElementState,
} from "./product-mesh";
import { IfcInspector } from "./inspector";
import { ProcessEnvironment } from "./process-environment";
import { elementLabel, hasAssumption, parentElementId, productLabel } from "./semantic";
import { AnimatedSection } from "./section";
import { ViewBookmarks } from "./view-bookmarks";
import {
  AdaptiveResolution,
  asBox,
  CameraRig,
  CameraTools,
  Legend,
  LoadingState,
  SceneCanvas,
  SceneLabel,
  Studio,
  type CameraHandle,
  type PerformanceSample,
  type Projection,
  type View,
} from "./stage";
import type { IfcViewerProps, PlantProductInfo } from "./types";
import styles from "./viewer.module.css";

export type ExtendedViewerProps = IfcViewerProps & {
  elementStates?: Record<string, ElementState>;
  measureKey?: number;
  onMeasure?(sample: PerformanceSample): void;
  onRequestMeasure?(): void;
  performanceSample?: PerformanceSample | null;
};

const NONE: ReadonlySet<string> = new Set();
type Focus = { id: string; ids: Set<string>; target: Box3; samples: Sample[] };

/** Rótulo de un nodo: «tag · nombre» en proceso; el de siempre en recipientes. */
const labelOf = (node: HierarchyNode) => productLabel(node);
const boundsOf = (box: Box3): Bounds => ({ min: box.min.toArray() as Vec3, max: box.max.toArray() as Vec3 });

function SelectionDimensions({ box }: { box: Box3 }) {
  const { min, max } = box;
  const gap = Math.max(.1, box.getSize(new Vector3()).length() * .07);
  const edges: [Vec3, Vec3, string, number][] = [
    [[min.x,min.y-gap,max.z+gap],[max.x,min.y-gap,max.z+gap],"X",max.x-min.x],
    [[max.x+gap,min.y-gap,min.z],[max.x+gap,min.y-gap,max.z],"Y",max.z-min.z],
    [[max.x+gap,min.y,max.z+gap],[max.x+gap,max.y,max.z+gap],"Z",max.y-min.y],
  ];
  const value = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 3 });
  return edges.map(([start,end,axis,length]) => {
    const center = start.map((v,i) => (v+end[i]!)/2) as Vec3;
    return <group key={axis}>
      <Line points={[start,end]} color={BRAND.sky} lineWidth={1.4} depthTest={false} renderOrder={12} />
      <SceneLabel position={center} center>
        <span className="pointer-events-none whitespace-nowrap rounded bg-surface px-1.5 py-0.5 font-mono text-[11px] text-accent-text shadow-sm">
          {axis} {value.format(length)} m
        </span>
      </SceneLabel>
    </group>;
  });
}

function productInfo(hierarchy: Hierarchy): PlantProductInfo[] {
  return [...hierarchy.nodes.values()].map((node) => ({
    semanticId: node.semanticId,
    ...(node.parentId ? { parentId: node.parentId } : {}),
    globalId: node.globalId,
    name: node.name,
    ...(node.tag ? { tag: node.tag } : {}),
    ...(node.description ? { description: node.description } : {}),
    ifcType: node.ifcType,
    psets: node.psets,
    bounds: node.bounds,
    center: node.center,
    triangles: node.triangles,
    isAssembly: node.isAssembly,
    label: labelOf(node),
    childIds: node.childIds,
  }));
}

export function IfcViewer({
  ifcUrl,
  ifcGzipUrl,
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
  holdPrevious = false,
  scenario,
  animateEnvironment = true,
  focusOnSelect,
  projection,
  onProducts,
  showSelectionDimensions,
  overlay,
  onFocusChange,
}: ExtendedViewerProps) {
  const contextual = scenario && scenario !== "neutral" ? scenario : undefined;
  // Proyecto de proceso: selección jerárquica, encuadre al seleccionar y perspectiva.
  const process = scenario !== undefined;
  const focusEnabled = focusOnSelect ?? process;
  const reducedMotion = useReducedMotion();
  const environmentMoving = animateEnvironment && reducedMotion === false &&
    contextual !== undefined;
  const load = useIfcModel(ifcUrl, holdPrevious, ifcGzipUrl),
    products = usePreparedModel(load.model);
  const model = load.model;
  const hierarchy = useMemo(() => buildHierarchy(products, model?.assemblies), [products, model]);
  const [selection, setSelection] = useState<string>();
  const [hover, setHover] = useState<string | null>(null);
  const [view, setView] = useState<View>("iso");
  const [projectionChoice, setProjectionChoice] = useState<Projection>();
  const [rigProjection, setRigProjection] = useState<Projection>();
  const [personalView, setPersonalView] = useState(false);
  const [mode, setMode] = useState<"solid" | "xray" | "exploded">("solid");
  const [tree, setTree] = useState(false),
    [cut, setCut] = useState(false),
    [inspector, setInspector] = useState(false);
  const [cutFraction, setCutFraction] = useState(0.55),
    [isolate, setIsolate] = useState(false);
  const [hidden, setHidden] = useState<Set<string>>(() => new Set());
  const [ghosts, setGhosts] = useState<ReadonlySet<string>>(NONE);
  const [exporting, setExporting] = useState(false);
  const container = useRef<HTMLDivElement>(null),
    camera = useRef<CameraHandle>(null);
  const focusState = useRef<Focus | null>(null);
  // "" (sin selección) cuenta como nada: así una pantalla controlada puede deseleccionar.
  const activeId = (selectedId ?? selection) || undefined;
  const activeNode = activeId ? hierarchy.nodes.get(activeId) : undefined;
  // El ratón sobre una pieza señala lo que seleccionaría un clic (el equipo entero o la pieza).
  const hoverId = hoveredId ?? (hover ? clickTarget(hierarchy, hover, activeId) : undefined);
  const hoverNode = hoverId ? hierarchy.nodes.get(hoverId) : undefined;
  const activeView = suppliedView ?? view,
    activeMode = suppliedMode ?? mode;
  const baseProjection = projectionChoice ?? projection ?? (process ? "perspective" : "orthographic");
  // Alzado, Planta y Como el plano son vistas técnicas: siempre ortográficas.
  const effectiveProjection: Projection = activeView === "iso" ? baseProjection : "orthographic";
  const selectedSet = useMemo(
    () => new Set(activeNode?.productIds.length ? activeNode.productIds : activeId ? [activeId] : []),
    [activeNode, activeId],
  );
  const hoverSet = useMemo(
    () => new Set(hoverNode?.productIds.length ? hoverNode.productIds : hoverId ? [hoverId] : []),
    [hoverNode, hoverId],
  );
  const cutHeight = model
    ? model.bounds.min[1] +
      (model.bounds.max[1] - model.bounds.min[1]) * cutFraction
    : 0;
  const cutPlane = useMemo(() => new Plane(new Vector3(0, -1, 0), 0), []);
  const planes = useMemo(() => cut && activeMode !== "exploded" ? [cutPlane] : [], [cut, activeMode, cutPlane]);
  const select = (id: string) => {
    setSelection(id);
    onSelect?.(id);
  };
  const clearSelection = () => {
    setSelection(undefined);
    onSelect?.("");
  };
  /** Esc o clic en vacío: sube un nivel (pieza → equipo) y, desde la raíz, deja la selección vacía. */
  const goUp = () => {
    if (!activeId) return;
    const up = levelUp(hierarchy, activeId);
    if (up) select(up);
    else clearSelection();
  };
  const highlight = (id: string | null) => {
    setHover(id);
    onHover?.(id);
  };
  const visibleProducts = useMemo(
    () =>
      products.filter(
        (p) =>
          !hidden.has(p.semanticId) && (!isolate || !selectedSet.size || selectedSet.has(p.semanticId)),
      ),
    [products, hidden, isolate, selectedSet],
  );
  const positions = useMemo(() => new Map(visibleProducts.map((product) => {
    const offset = explosionOffset(product, activeMode === "exploded" ? 1 : 0);
    return [product.semanticId, product.center.map((v, i) => v + offset[i]!) as Vec3] as const;
  })), [visibleProducts, activeMode]);
  // Índice de oclusión: mallas auxiliares fuera de la escena, con la posición de cada producto.
  const occlusion = useMemo(
    () => (visibleProducts.length ? new OcclusionIndex(visibleProducts, positions) : null),
    [visibleProducts, positions],
  );
  useEffect(() => () => occlusion?.dispose(), [occlusion]);
  const boxes = useMemo(
    () => new Map(visibleProducts.map((product) => [product.semanticId, placedBox(product, positions.get(product.semanticId))])),
    [visibleProducts, positions],
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
  // Cota del agua o del terreno en los escenarios: ni la cámara ni la vista general bajan de ahí.
  const groundY = process ? 0 : model?.bounds.min[1];

  const clearFocus = () => {
    focusState.current = null;
    setGhosts(NONE);
  };
  /**
   * Encuadra un producto o un equipo: candidatos en semiesfera puntuados por visibilidad con rayos
   * (three-mesh-bvh), elevación, continuidad y forma; transición suave con el objetivo como punto
   * de órbita y atenuación de lo que aún lo tape desde el ojo final.
   */
  const frame = (id: string, smooth = true) => {
    const handle = camera.current;
    if (!handle?.lookAt || !handle.lens || !occlusion || !model) return;
    const node = hierarchy.nodes.get(id);
    const ids = new Set(node?.productIds.length ? node.productIds : [id]);
    const target = unionBox(visibleProducts, ids, positions);
    if (target.isEmpty()) return;
    if (activeView !== "iso") {
      // Vistas técnicas: se conserva la orientación del plano y solo se centra y acerca.
      clearFocus();
      handle.fit(boundsOf(target));
      return;
    }
    const started = performance.now();
    const samples = occlusion.samples([...ids], FOCUS_SAMPLES);
    const lens = handle.lens();
    const now = handle.current?.();
    const current = now ? new Vector3(...now.eye).sub(new Vector3(...now.target)) : undefined;
    const shot = chooseFraming({
      target,
      scene: asBox(displayBounds ?? model.bounds),
      samples,
      raycast: occlusion.raycaster(ids),
      lens,
      current: current && current.lengthSq() > 1e-8 ? current.normalize() : undefined,
      options: { groundY, margin: focusMargin(target.getSize(new Vector3()).length()) },
    });
    const blockers = occlusion.blockers(shot.eye, shot.target, samples, ids, lens.kind === "orthographic");
    const occluding = ghostsFor(blockers, target, boxes);
    const elapsed = performance.now() - started;
    focusState.current = { id, ids, target, samples };
    container.current?.setAttribute("data-framing-ms", elapsed.toFixed(1));
    container.current?.setAttribute("data-framing-visibility", shot.visibility.toFixed(2));
    setGhosts(occluding.length ? new Set(occluding) : NONE);
    void handle.lookAt({
      eye: shot.eye.toArray() as Vec3,
      target: shot.target.toArray() as Vec3,
      zoom: shot.zoom,
      focus: boundsOf(target),
    }, smooth);
  };
  /** Tras mover la cámara a mano: se recalcula qué sigue tapando el componente encuadrado. */
  const refreshGhosts = () => {
    const focus = focusState.current, handle = camera.current;
    if (!focus || !occlusion || !handle?.current) return;
    const { eye } = handle.current();
    const blockers = occlusion.blockers(new Vector3(...eye), focus.target.getCenter(new Vector3()), focus.samples, focus.ids,
      handle.lens?.().kind === "orthographic");
    const occluding = ghostsFor(blockers, focus.target, boxes);
    setGhosts(occluding.length ? new Set(occluding) : NONE);
  };

  // Encuadre al cambiar la selección (clic, tabla o ficha) y al llegar un modelo nuevo.
  const framedKey = useRef<string | undefined>(undefined);
  const followSelection = useEffectEvent(() => {
    if (!focusEnabled || !model || rigProjection !== effectiveProjection) return;
    const key = activeId ? `${activeId}@${model.url}` : undefined;
    if (key === framedKey.current) return;
    const previous = framedKey.current;
    framedKey.current = key;
    if (activeId) frame(activeId);
    else if (previous) {
      clearFocus();
      camera.current?.view(activeView);
    }
  });
  useEffect(() => {
    // En el fotograma siguiente: el BVH de las mallas nuevas ya está construido y la transición
    // de cámara no compite con el render que ha traído la selección.
    const frameId = requestAnimationFrame(() => followSelection());
    return () => cancelAnimationFrame(frameId);
  }, [activeId, model, focusEnabled, rigProjection, effectiveProjection]);
  // Sin foco activo (vista cambiada, pieza oculta…) no queda nada atenuado.
  const focusLost = useEffectEvent(() => {
    if (focusState.current && (!activeId || !selectedSet.size)) clearFocus();
  });
  useEffect(() => {
    focusLost();
  }, [activeId, selectedSet]);
  const reportFocus = useEffectEvent((occluding: string[]) => onFocusChange?.({ occluding }));
  useEffect(() => {
    reportFocus([...ghosts]);
  }, [ghosts]);
  const reportProducts = useEffectEvent((info: PlantProductInfo[]) => onProducts?.(info));
  useEffect(() => {
    if (model) reportProducts(productInfo(hierarchy));
  }, [hierarchy, model]);
  // Esc sube un nivel en la selección (fuera de campos de texto y diálogos).
  const escape = useEffectEvent((event: KeyboardEvent) => {
    if (event.key !== "Escape" || event.defaultPrevented || isTyping(event.target)) return;
    if (document.querySelector("[role=dialog]")) return;
    event.preventDefault();
    goUp();
  });
  useEffect(() => {
    if (!process || !activeId) return;
    const onKey = (event: KeyboardEvent) => escape(event);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [process, activeId]);

  const pickProduct = (productId: string) => select(clickTarget(hierarchy, productId, activeId));
  const focusProduct = (productId: string) => {
    // Doble clic: los dos clics ya han bajado al nivel que toca; se encuadra ese nivel.
    const target = clickTarget(hierarchy, productId, activeId);
    if (!focusEnabled) frame(target);
    else if (target === activeId) frame(target);
  };
  /** Una vista elegida a mano manda: la selección se conserva, pero no se vuelve a encuadrar. */
  const settleFocus = () => {
    clearFocus();
    framedKey.current = activeId && model ? `${activeId}@${model.url}` : undefined;
  };
  const changeView = (next: View) => {
    setPersonalView(false);
    settleFocus();
    setView(next);
    camera.current?.view(next);
  };
  const labelNode = hoverNode ?? activeNode;
  const labelPosition = labelNode
    ? (() => {
        const ids = new Set(labelNode.productIds.length ? labelNode.productIds : [labelNode.semanticId]);
        const box = unionBox(visibleProducts, ids, positions);
        if (box.isEmpty()) return undefined;
        const center = box.getCenter(new Vector3());
        return [center.x, box.max.y, center.z] as Vec3;
      })()
    : undefined;
  const selectionBox = activeNode ? unionBox(visibleProducts, selectedSet, positions) : undefined;
  const selectionLabel = activeNode ? labelOf(activeNode) : undefined;
  const overlayContent: ReactNode = model && overlay
    ? overlay({ products: visibleProducts, selectedId: activeId, bounds: model.bounds })
    : null;
  const toggleHidden = (ids: string[]) =>
    setHidden((previous) => {
      const next = new Set(previous);
      const show = ids.every((id) => next.has(id));
      for (const id of ids) {
        if (show) next.delete(id);
        else next.add(id);
      }
      return next;
    });
  const treeRow = (id: string, depth: number): ReactNode => {
    const node = hierarchy.nodes.get(id);
    if (!node) return null;
    const label = process ? labelOf(node) : elementLabel(node.semanticId);
    const ids = node.productIds.length ? node.productIds : [node.semanticId];
    const isHidden = ids.every((productId) => hidden.has(productId));
    return (
      <div key={node.globalId} role="treeitem" aria-level={depth + 1} aria-selected={activeId === node.semanticId}
        aria-expanded={node.childIds.length ? true : undefined}>
        <div className={styles.treeRow} style={depth ? { paddingLeft: depth * 12 } : undefined}>
          <button
            className={styles.button}
            aria-pressed={activeId === node.semanticId}
            onClick={() => select(node.semanticId)}
            title={node.isAssembly ? `${node.ifcType} · ${node.productIds.length} piezas` : node.ifcType}
          >
            {label}
          </button>
          <button
            className={styles.button}
            aria-label={`${isHidden ? "Mostrar" : "Ocultar"} ${label}`}
            onClick={() => toggleHidden(ids)}
          >
            {isHidden ? <EyeOff /> : <Eye />}
          </button>
        </div>
        {node.childIds.length ? (
          <div role="group">{node.childIds.map((child) => treeRow(child, depth + 1))}</div>
        ) : null}
      </div>
    );
  };
  return (
    <div
      className={styles.frame}
      ref={container}
      data-testid="ifc-viewer"
      data-phase={model ? "ready" : load.error ? "error" : "loading"}
      data-products={model?.products.length}
      data-assemblies={model?.assemblies?.length ?? 0}
      data-triangles={model?.triangles}
      data-height={model?.bounds.max[1]}
      data-parse-ms={model?.parseMs.toFixed(2)}
      data-ifc-url={model?.url}
      data-scenario={scenario}
      data-projection={effectiveProjection}
      data-selection={activeId ?? ""}
      data-selection-bounds={selectionBox && !selectionBox.isEmpty()
        ? [...selectionBox.min.toArray(), ...selectionBox.max.toArray()].map((v) => v.toFixed(3)).join(",")
        : undefined}
      data-occluding={[...ghosts].join(" ")}
      data-environment-motion={scenario ? (environmentMoving ? "on" : "off") : undefined}
      data-provenance={model?.products.some(p => p.psets.TrazIA_Traceability?.Dataset === "real") ? "Datos reales" : model?.products.some(p => p.psets.TrazIA_Traceability?.Dataset === "synthetic") ? "Datos sintéticos" : "Procedencia sin declarar"}
      data-approval={model?.products.some(p => p.psets.TrazIA_Traceability?.Draft === true) ? "DRAFT · requiere revisión" : "Consultar aprobación en IFC"}
    >
      {model ? (
        <SceneCanvas label="Modelo IFC; usa el árbol para seleccionar componentes"
          initialRotating={!scenario} shadows={!!contextual} pixelBudget={scenario ? 880_000 : undefined}
          onPointerMissed={process ? goUp : undefined}>
          {contextual ? (
            <>
              <AdaptiveResolution />
              <ProcessEnvironment key={contextual} id={contextual} motion={environmentMoving} bounds={model.bounds} products={products} />
            </>
          ) : (
            <Studio effects={!scenario} stage />
          )}
          <CameraRig
            bounds={displayBounds ?? model.bounds}
            orbitCenter={displayBounds ? undefined : products.find(product => product.semanticId === "shell")?.center}
            framing={scenario ? 1.18 : undefined}
            view={activeView}
            handle={camera}
            measureKey={measureKey}
            onMeasure={onMeasure}
            projection={effectiveProjection}
            groundY={process ? groundY : undefined}
            onProjection={setRigProjection}
            onRest={refreshGhosts}
          />
          {!contextual ? <Grid
            position={[0, -0.015, 0]}
            args={scenario ? [96, 72] : [20, 20]}
            cellSize={scenario ? 2 : 0.5}
            sectionSize={scenario ? 10 : 2}
            cellColor={BRAND.surfaceRaised}
            sectionColor={BRAND.border}
            fadeDistance={scenario ? 95 : 20}
            infiniteGrid
          /> : null}
          {visibleProducts.map((product) => {
            const trace = product.psets.TrazIA_Traceability;
            const parent = parentElementId(product.semanticId);
            // Un estado marcado en el equipo (p. ej. «cambiado») se ve en todas sus piezas.
            const owner = hierarchy.nodes.get(product.semanticId)?.parentId;
            const status =
              elementStates?.[product.semanticId] ??
              (parent !== product.semanticId ? elementStates?.[parent] : undefined) ??
              (owner ? elementStates?.[owner] : undefined) ??
              (hasAssumption(product.semanticId, product.psets) ? "assumed" : trace?.Draft === false && trace?.ApprovalJSON
                ? "approved"
                : "draft");
            const selected = selectedSet.has(product.semanticId);
            return (
              <ProductMesh
                key={product.globalId}
                product={product}
                position={positions.get(product.semanticId) ?? product.center}
                selected={selected}
                hovered={
                  !selected && (
                    hoverSet.has(product.semanticId) ||
                    parent === hoverId ||
                    (parent === activeId && product.semanticId !== activeId))
                }
                ghost={ghosts.has(product.semanticId)}
                state={status}
                useIfcColors={!!scenario}
                mode={activeMode}
                planes={planes}
                onSelect={pickProduct}
                onHover={highlight}
                onFocus={focusProduct}
              />
            );
          })}
          {cut && activeMode !== "exploded" ? (
            <AnimatedSection products={visibleProducts} height={cutHeight} plane={cutPlane} />
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
          {activeNode && selectionBox && !selectionBox.isEmpty() ? (
            <SceneLabel
              position={selectionBox.getCenter(new Vector3()).toArray() as Vec3}
              center
              zIndexRange={[1, 0]}
              style={{ pointerEvents: "none" }}
            >
              <span
                data-ifc-anchor={activeNode.semanticId}
                style={{ display: "block", width: 1, height: 1 }}
              />
            </SceneLabel>
          ) : null}
          {process && labelNode && labelPosition ? (
            <SceneLabel
              key={labelNode.semanticId}
              position={labelPosition}
              center
              zIndexRange={[2, 0]}
              style={{ pointerEvents: "none", transform: "translateY(-22px)" }}
            >
              <span className={styles.label} data-hover-label={labelNode.semanticId}>
                {labelOf(labelNode)}
              </span>
            </SceneLabel>
          ) : null}
          {showSelectionDimensions && selectionBox && !selectionBox.isEmpty() ? <SelectionDimensions box={selectionBox} /> : null}
          {overlayContent}
        </SceneCanvas>
      ) : (
        <LoadingState error={load.error} />
      )}
      <CameraTools
        handle={camera}
        container={container}
        onReset={() => {
          setPersonalView(false);
          settleFocus();
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
                ["iso", process ? "General" : "Iso"],
                ["front", "Alzado"],
                ["top", "Planta"],
                ["plan", "Como el plano"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                className={styles.button}
                aria-pressed={!personalView && activeView === key}
                title={key === "iso" && process ? "Vista general en tres cuartos" : undefined}
                onClick={() => changeView(key)}
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
        {process && !suppliedView ? (
          <button
            type="button"
            className={styles.button}
            aria-pressed={effectiveProjection === "perspective"}
            title={effectiveProjection === "perspective"
              ? "Perspectiva · pulsa para ver en ortográfica"
              : "Ortográfica · pulsa para ver en perspectiva"}
            onClick={() => {
              const next: Projection = effectiveProjection === "perspective" ? "orthographic" : "perspective";
              setProjectionChoice(next);
              if (activeView !== "iso") changeView("iso");
            }}
          >
            <Box /> Perspectiva
          </button>
        ) : null}
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
      {model ? <ViewBookmarks key={ifcUrl} url={ifcUrl} camera={camera} onRestore={() => { setPersonalView(true); settleFocus(); }} /> : null}
      <div className={styles.secondary}>
        <button type="button" className={styles.button} disabled={!apiEnabled || !activeNode || exporting}
          title={!apiEnabled ? "Conecta la API para crear el BCF" : "PNG, cámara actual y GUID seleccionado"}
          onClick={async () => {
            setExporting(true);
            try {
              const capture = await camera.current?.snapshot?.();
              if (!capture || !activeNode) throw new Error("Selecciona un elemento IFC");
              const bytes = new Uint8Array(await capture.blob.arrayBuffer());
              let binary = ""; for (const byte of bytes) binary += String.fromCharCode(byte);
              const response = await fetch(apiURL("/viewer/bcf"), { method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ png_base64: btoa(binary), eye: capture.pose.eye, target: capture.pose.target,
                  zoom: capture.pose.zoom, up: capture.up,
                  viewport_height: capture.viewportHeight, guid: activeNode.globalId }) });
              if (!response.ok) throw new Error("No se pudo crear el BCF; comprueba la API y reintenta");
              const url = URL.createObjectURL(await response.blob());
              const link = document.createElement("a"); link.href = url; link.download = "vista_DRAFT.bcfzip"; link.click();
              setTimeout(() => URL.revokeObjectURL(url), 1000);
            } catch (error) { toast.error(error instanceof Error ? error.message : "Error al exportar BCF"); }
            finally { setExporting(false); }
          }}>{exporting ? "Creando BCF…" : "Captura BCF"}</button>
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
          disabled={!activeNode}
          onClick={() => activeId && frame(activeId)}
          title="Encuadrar selección"
        >
          <Crosshair />
        </button>
        <button
          className={styles.button}
          disabled={!activeNode}
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
          <h4>{model?.schema ?? "IFC"} / {hierarchy.nested ? "Equipos y piezas" : "Equipo"}</h4>
          <div role="tree" aria-label="Elementos del modelo">
            {hierarchy.roots.map((id) => treeRow(id, 0))}
          </div>
          {activeNode ? (
            <>
              <span className={styles.small}>{activeNode.ifcType}</span>
              <span className={styles.small}>
                GlobalId: {activeNode.globalId}
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
          {selectionLabel ?? "Selecciona un componente"}
        </strong>
        <br />
        {model
          ? `${model.schema} · ${model.triangles.toLocaleString("es-ES")} triángulos · sintético`
          : "Geometría leída del IFC"}
        {process && activeNode ? (
          <>
            <br />
            {activeNode.parentId ? "Esc: volver al equipo" : "Esc: vista general"}
            {activeNode.childIds.length ? " · clic: bajar a una pieza" : ""}
          </>
        ) : null}
        {performanceSample ? (
          <>
            <br />
            {performanceSample.fps.toFixed(1)} fps medios · p95{" "}
            {performanceSample.p95Ms.toFixed(1)} ms
          </>
        ) : null}
      </div>
      {inspector ? (
        <IfcInspector product={activeNode ? { ...activeNode, label: selectionLabel } : undefined} onClose={() => setInspector(false)} />
      ) : null}
      <Legend />
      <p className={styles.srOnly} role="status">
        {activeNode
          ? `${selectionLabel} seleccionado. ${activeNode.globalId}`
          : "Sin selección"}
      </p>
    </div>
  );
}
