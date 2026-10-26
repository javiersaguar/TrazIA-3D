"use client";

import { Grid } from "@react-three/drei";
import { Crosshair, Eye, EyeOff, Layers, Scissors, TreePine } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { Plane, Vector3 } from "three";
import type { Vec3 } from "@/workers/ifc-protocol";
import { AzimuthRing, Dimensions } from "./annotations";
import { useIfcModel, usePreparedModel } from "./model-resource";
import { explosionOffset, ProductMesh, type ElementState } from "./product-mesh";
import { elementLabel } from "./semantic";
import { SectionCaps } from "./section";
import { CameraRig, CameraTools, Legend, LoadingState, SceneCanvas, Studio, type CameraHandle,
  type PerformanceSample, type View } from "./stage";
import type { IfcViewerProps } from "./types";
import styles from "./viewer.module.css";

export type ExtendedViewerProps = IfcViewerProps & {
  elementStates?: Record<string, ElementState>;
  measureKey?: number;
  onMeasure?(sample: PerformanceSample): void;
};

export function IfcViewer({ ifcUrl, selectedId, hoveredId, onSelect, onHover, annotations = [],
  view: suppliedView, mode: suppliedMode, elementStates, measureKey, onMeasure }: ExtendedViewerProps) {
  const load = useIfcModel(ifcUrl), products = usePreparedModel(load.model);
  const [selection, setSelection] = useState<string>();
  const [hover, setHover] = useState<string | null>(null);
  const [view, setView] = useState<View>("iso");
  const [mode, setMode] = useState<"solid" | "xray" | "exploded">("solid");
  const [tree, setTree] = useState(false), [cut, setCut] = useState(false);
  const [cutFraction, setCutFraction] = useState(.55), [isolate, setIsolate] = useState(false);
  const [hidden, setHidden] = useState<Set<string>>(() => new Set());
  const container = useRef<HTMLDivElement>(null), camera = useRef<CameraHandle>(null);
  const activeId = selectedId ?? selection, activeHover = hoveredId ?? hover;
  const activeView = suppliedView ?? view, activeMode = suppliedMode ?? mode;
  const model = load.model;
  const cutHeight = model ? model.bounds.min[1] + (model.bounds.max[1] - model.bounds.min[1]) * cutFraction : 0;
  const planes = useMemo(() => cut ? [new Plane(new Vector3(0, -1, 0), cutHeight)] : [], [cut, cutHeight]);
  const select = (id: string) => { setSelection(id); onSelect?.(id); };
  const highlight = (id: string | null) => { setHover(id); onHover?.(id); };
  const focus = (id: string) => { const product = products.find(p => p.semanticId === id); if (product) camera.current?.fit(product.bounds); };
  const selected = products.find(p => p.semanticId === activeId);
  const visibleProducts = useMemo(() => products.filter(p => !hidden.has(p.semanticId) && (!isolate || p.semanticId === activeId)), [products, hidden, isolate, activeId]);
  return <div className={styles.frame} ref={container} data-testid="ifc-viewer" data-phase={model ? "ready" : load.error ? "error" : "loading"}
    data-products={model?.products.length} data-triangles={model?.triangles} data-height={model?.bounds.max[1]}
    data-parse-ms={model?.parseMs.toFixed(2)}>
    {model ? <SceneCanvas label="Modelo IFC sintético; usa el árbol para seleccionar componentes">
      <Studio />
      <CameraRig bounds={model.bounds} view={activeView} handle={camera} measureKey={measureKey} onMeasure={onMeasure} />
      <Grid position={[0, -.015, 0]} args={[20, 20]} cellSize={.5} sectionSize={2} cellColor="#253345"
        sectionColor="#3b4d63" fadeDistance={20} infiniteGrid />
      {visibleProducts.map(product => {
        const offset = explosionOffset(product, activeMode === "exploded" ? 1 : 0);
        const position = product.center.map((v, i) => v + offset[i]!) as Vec3;
        const trace = product.psets.TrazIA_Traceability;
        const status = elementStates?.[product.semanticId] ?? (trace?.Draft === false && trace?.ApprovalJSON ? "approved" : "draft");
        return <ProductMesh key={product.globalId} product={product} position={position} selected={product.semanticId === activeId}
          hovered={product.semanticId === activeHover} state={status} mode={activeMode} planes={planes}
          onSelect={select} onHover={highlight} onFocus={focus} />;
      })}
      {cut && activeMode !== "exploded" ? <SectionCaps products={visibleProducts} height={cutHeight} /> : null}
      {activeMode !== "exploded" ? <Dimensions annotations={annotations} products={products} /> : null}
      {activeView === "top" ? <AzimuthRing model={model} /> : null}
    </SceneCanvas> : <LoadingState error={load.error} />}
    <CameraTools handle={camera} container={container} />
    <div className={styles.selectors}>
      {!suppliedView ? <div className={styles.group} aria-label="Vistas guardadas">
        {([["iso", "Iso"], ["front", "Alzado"], ["top", "Planta"], ["plan", "Como el plano"]] as const).map(([key, label]) =>
          <button key={key} className={styles.button} aria-pressed={activeView === key} onClick={() => setView(key)}>{label}</button>)}
      </div> : <button className={styles.button} onClick={() => camera.current?.view("plan")} title="Vista ortográfica alineada con el alzado">Como el plano</button>}
      {!suppliedMode ? <div className={styles.group} aria-label="Representación del modelo">
        {([["solid", "Sólido"], ["xray", "Rayos X"], ["exploded", "Explosionado"]] as const).map(([key, label]) =>
          <button key={key} className={styles.button} aria-pressed={activeMode === key} onClick={() => setMode(key)}>{label}</button>)}
      </div> : null}
    </div>
    <div className={styles.secondary}>
      <button className={styles.button} aria-pressed={tree} onClick={() => setTree(v => !v)}><TreePine /> Elementos</button>
      <button className={styles.button} aria-pressed={cut} disabled={activeMode === "exploded"} onClick={() => setCut(v => !v)}><Scissors /> Corte</button>
      <button className={styles.button} disabled={!selected} onClick={() => selected && focus(selected.semanticId)} title="Encuadrar selección"><Crosshair /></button>
      <button className={styles.button} disabled={!selected} aria-pressed={isolate} onClick={() => setIsolate(v => !v)} title="Aislar selección"><Layers /></button>
    </div>
    {cut ? <label className={styles.cut}>Plano de corte · {cutHeight.toFixed(2)} m
      <input className={styles.range} aria-label="Altura del plano de corte" type="range" min="0" max="1" step=".005" value={cutFraction} onChange={e => setCutFraction(Number(e.target.value))} />
    </label> : null}
    {tree ? <div className={styles.tree} aria-label="Árbol IFC"><h4>{model?.schema ?? "IFC"} / Equipo</h4>
      {products.map(product => <div key={product.globalId} className={styles.treeRow}>
        <button className={styles.button} aria-pressed={activeId === product.semanticId} onClick={() => select(product.semanticId)}>{elementLabel(product.semanticId)}</button>
        <button className={styles.button} aria-label={`${hidden.has(product.semanticId) ? "Mostrar" : "Ocultar"} ${elementLabel(product.semanticId)}`}
          onClick={() => setHidden(previous => { const next = new Set(previous); if (next.has(product.semanticId)) next.delete(product.semanticId); else next.add(product.semanticId); return next; })}>
          {hidden.has(product.semanticId) ? <EyeOff /> : <Eye />}
        </button>
      </div>)}
      {selected ? <><span className={styles.small}>{selected.ifcType}</span><span className={styles.small}>GlobalId: {selected.globalId}</span></> : null}
      <button className={styles.button} onClick={() => { setHidden(new Set()); setIsolate(false); }}>Mostrar todo</button>
    </div> : null}
    <div className={styles.caption}><strong>{selected ? elementLabel(selected.semanticId) : "Selecciona un componente"}</strong><br />
      {model ? `${model.schema} · ${model.triangles.toLocaleString("es-ES")} triángulos · sintético` : "Geometría leída del IFC"}
    </div>
    <Legend />
    <p className={styles.srOnly} role="status">{selected ? `${elementLabel(selected.semanticId)} seleccionado. ${selected.globalId}` : "Sin selección"}</p>
  </div>;
}
