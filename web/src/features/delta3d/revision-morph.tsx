"use client";

import { Grid, Line } from "@react-three/drei";
import { Eye, LocateFixed, Pause, Play, SkipForward } from "lucide-react";
import { useReducedMotion } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Bounds } from "@/workers/ifc-protocol";
import { useSelection } from "@/stores/selection";
import { useIfcModel, usePreparedModel } from "../viewer3d/model-resource";
import { ProductMesh } from "../viewer3d/product-mesh";
import { CameraRig, CameraTools, Legend, LoadingState, SceneCanvas, SceneLabel as Html, Studio, type CameraHandle } from "../viewer3d/stage";
import type { RevisionMorphProps } from "../viewer3d/types";
import { changeSteps, clampProgress, morphState, pairByGlobalId } from "./morph";
import styles from "../viewer3d/viewer.module.css";

export function RevisionMorph({ fromUrl, toUrl, changes, progress: controlledProgress, onProgress,
  showNarration = controlledProgress === undefined }: RevisionMorphProps & { showNarration?: boolean }) {
  const before = useIfcModel(fromUrl), after = useIfcModel(toUrl);
  const a = usePreparedModel(before.model), b = usePreparedModel(after.model);
  const [ownProgress, setOwnProgress] = useState(0), [playing, setPlaying] = useState(false);
  const [follow, setFollow] = useState(false), [ghost, setGhost] = useState(true);
  const container = useRef<HTMLDivElement>(null), camera = useRef<CameraHandle>(null);
  const reduced = useReducedMotion(), callback = useRef(onProgress);
  const selectedId = useSelection(s => s.selectedId);
  const setSelected = useSelection(s => s.setSelected);
  const current = useRef(0);
  const progress = clampProgress(controlledProgress ?? ownProgress);
  useEffect(() => { current.current = progress; callback.current = onProgress; }, [progress, onProgress]);
  const setProgress = (value: number) => { setOwnProgress(value); onProgress?.(value); };
  const pairs = useMemo(() => pairByGlobalId(a, b), [a, b]);
  const steps = useMemo(() => changeSteps(changes), [changes]);
  const stepIndex = Math.min(steps.length - 1, Math.floor(progress * steps.length));
  const step = steps[stepIndex];
  const bounds = useMemo<Bounds>(() => ({ min: [Math.min(before.model?.bounds.min[0] ?? 0, after.model?.bounds.min[0] ?? 0),
    0, Math.min(before.model?.bounds.min[2] ?? 0, after.model?.bounds.min[2] ?? 0)],
    max: [Math.max(before.model?.bounds.max[0] ?? 2, after.model?.bounds.max[0] ?? 2),
      Math.max(before.model?.bounds.max[1] ?? 8, after.model?.bounds.max[1] ?? 8),
      Math.max(before.model?.bounds.max[2] ?? 2, after.model?.bounds.max[2] ?? 2)] }), [before.model, after.model]);
  useEffect(() => {
    if (!playing || reduced) return;
    let frame = 0, previous = 0;
    const animate = (now: number) => {
      if (!previous) previous = now;
      const next = Math.min(1, current.current + Math.min(64, now - previous) / 9000);
      previous = now; current.current = next;
      setOwnProgress(next); callback.current?.(next);
      if (next < 1) frame = requestAnimationFrame(animate); else setPlaying(false);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [playing, reduced]);
  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const changed = () => {
      if (preference.matches) { setPlaying(false); setFollow(false); setOwnProgress(1); callback.current?.(1); }
    };
    preference.addEventListener("change", changed);
    return () => preference.removeEventListener("change", changed);
  }, []);
  useEffect(() => {
    if (!follow || !step || reduced) return;
    const product = b.find(p => p.semanticId === step.elementId) ?? a.find(p => p.semanticId === step.elementId);
    if (product) camera.current?.fit(product.bounds);
  }, [follow, step, a, b, reduced]);
  useEffect(() => {
    if (!follow || !selectedId || reduced) return;
    const product = b.find(p => p.semanticId === selectedId) ?? a.find(p => p.semanticId === selectedId);
    if (product) camera.current?.fit(product.bounds);
  }, [follow, selectedId, a, b, reduced]);
  const ready = before.model && after.model;
  const changedIds = useMemo(() => {
    const ids = new Set(steps.filter(s => s.geometry).map(s => s.elementId));
    for (const pair of pairs) {
      if (!pair.before || !pair.after || pair.before.bounds.min.some((v, i) => Math.abs(v - pair.after!.bounds.min[i]!) > 1e-6) ||
          pair.before.bounds.max.some((v, i) => Math.abs(v - pair.after!.bounds.max[i]!) > 1e-6)) ids.add((pair.after ?? pair.before)!.semanticId);
    }
    return ids;
  }, [steps, pairs]);
  const markers = useMemo(() => steps.map(change => ({ change,
    product: b.find(p => p.semanticId === change.elementId) ?? a.find(p => p.semanticId === change.elementId),
  })).filter(entry => !!entry.product).sort((left, right) => right.product!.center[1] - left.product!.center[1])
    .map((entry, index) => ({ ...entry,
      position: [index % 2 ? bounds.min[0] - .8 : bounds.max[0] + .8, entry.product!.center[1], bounds.max[2] + .6] as [number, number, number],
    })), [steps, a, b, bounds]);
  return <div className={styles.frame} ref={container} data-testid="revision-morph" data-phase={ready ? "ready" : "loading"} data-progress={progress.toFixed(3)}>
    {ready ? <SceneCanvas label="Comparación de IFC sintéticos A y B emparejados por GlobalId">
      <Studio />
      <CameraRig bounds={bounds} handle={camera} onUserControl={() => { setPlaying(false); setFollow(false); }} />
      <Grid position={[0, -.02, 0]} args={[16, 16]} cellSize={.5} sectionSize={2} cellColor="#253345" sectionColor="#3c4e65" fadeDistance={18} />
      {ghost ? a.map(product => <ProductMesh key={`ghost-${product.globalId}`} product={product} opacity={.12} color="#668fc7" wireframe immediate />) : null}
      {pairs.map(pair => {
        const state = morphState(pair, progress), changed = changedIds.has((pair.after ?? pair.before)!.semanticId);
        return <group key={pair.globalId}>
          {pair.before ? <ProductMesh product={pair.before} position={state.position} scale={state.scale}
            opacity={state.sourceOpacity} state={changed ? "changed" : "draft"} selected={pair.before.semanticId === selectedId}
            onSelect={id => setSelected(id)} immediate /> : null}
          {pair.after ? <ProductMesh product={pair.after} opacity={state.targetOpacity} state={changed ? "changed" : "draft"}
            selected={pair.after.semanticId === selectedId} onSelect={id => setSelected(id)} immediate /> : null}
        </group>;
      })}
      {markers.map(({ change, product, position }) => <group key={change.id}>
        <Line points={[product!.center, position]} color="#f5a35c" dashed dashSize={.07} gapSize={.05} lineWidth={.8} />
        <Html position={position} center zIndexRange={[8, 0]} style={{ pointerEvents: "none" }}>
          <div className={styles.delta}>Δ {change.label}</div>
        </Html>
      </group>)}
    </SceneCanvas> : <LoadingState error={before.error ?? after.error} />}
    <CameraTools handle={camera} container={container} />
    <div className={styles.selectors} role="group" aria-label="Cámara de revisiones">
      <button className={styles.button} aria-pressed={!follow} onClick={() => { setFollow(false); camera.current?.view("iso"); }}><Eye /> Vista general</button>
      <button className={styles.button} aria-pressed={follow} onClick={() => setFollow(v => !v)}><LocateFixed /> Seguir el cambio</button>
      <button className={styles.button} aria-pressed={ghost} onClick={() => setGhost(v => !v)}>Fantasma A</button>
    </div>
    <div className={styles.badge}>{progress === 1 ? "IFC B exacto" : progress === 0 ? "IFC A exacto" : "Interpolación ilustrativa"} · sintético</div>
    <label className={styles.scrub}>A<input className={styles.range} type="range" min="0" max="1" step=".001"
      value={progress} aria-label="Interpolación IFC de A a B" onChange={e => { setPlaying(false); setProgress(Number(e.target.value)); }} />B
      <output>{Math.round(progress * 100)} %</output>
    </label>
    {showNarration ? <div className={styles.narration}>
      <button className={styles.button} aria-label={playing ? "Pausar morph" : "Reproducir morph"} onClick={() => {
        if (reduced) { setPlaying(false); setProgress(progress < 1 ? 1 : 0); return; }
        if (progress >= 1) { current.current = 0; setProgress(0); }
        setPlaying(v => !v);
      }}>{playing ? <Pause /> : <Play />}</button>
      <p><strong>{step ? `Cambio ${stepIndex + 1} de ${steps.length}` : "Revisiones A → B"}</strong>
        {step?.narration ?? "Arrastra el avance para comparar las dos revisiones IFC."}</p>
      <button className={styles.button} aria-label="Siguiente cambio" onClick={() => {
        setPlaying(false); setProgress(steps.length ? Math.min(1, (stepIndex + 1.5) / steps.length) : 1);
      }}><SkipForward /></button>
    </div> : <div className={styles.caption}>A: referencia azul · B: mallas IFC exactas al finalizar</div>}
    <Legend />
  </div>;
}
