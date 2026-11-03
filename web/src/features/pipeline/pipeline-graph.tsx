"use client";

import "@xyflow/react/dist/style.css";
import { BaseEdge, Controls, Handle, MarkerType, Position, ReactFlow, ReactFlowProvider, getSmoothStepPath, useReactFlow, type Edge, type EdgeProps, type Node, type NodeProps } from "@xyflow/react";
import { ArrowLeft, ArrowRight, Focus, Maximize2, Pause, Play, Radio, RotateCcw, Route } from "lucide-react";
import { useTheme } from "next-themes";
import { memo, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { Button, Icon } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { apiEnabled } from "@/lib/api/config";
import { useMounted } from "@/lib/use-mounted";
import { STAGES, type StageDef, type StageId } from "@/lib/mock/pipeline";
import { usePipeline, type StageRunState } from "@/stores/pipeline";
import { STAGE_ICON } from "./stage-meta";
import { CONDITIONAL, NODE_HEIGHT, NODE_WIDTH, PROFILES, graphModel, type Strategy } from "./graph-model";
import { StageInspector } from "./stage-inspector";
import styles from "./pipeline-graph.module.css";

type StageNode = Node<{ def: StageDef; run: StageRunState; active: boolean; visited: boolean; live: boolean; moving: boolean; selected: boolean; inspect: () => void }, "stage">;
const StageNodeView = memo(function StageNodeView({ data }: NodeProps<StageNode>) {
  const { def, run, active, visited, live } = data;
  const label = live ? !apiEnabled ? "Sin API conectada" : run.lastEventAt === null ? "Sin eventos" : run.status === "skipped" ? "Omitida" : run.ok < run.total ? "Con errores" : `${run.ok}/${run.total} eventos OK` : active ? "Etapa en foco" : CONDITIONAL[def.id] ?? (visited ? "Explicada" : "Por explorar");
  return <div role="button" tabIndex={0} aria-label={`Explorar ${def.name}`} onClick={data.inspect} onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); event.stopPropagation(); data.inspect(); } }} data-stage={def.id} data-active={active} data-moving={data.moving} data-selected={data.selected} style={{ width: NODE_WIDTH, height: NODE_HEIGHT }} className={cn(styles.node, "rounded-xl border bg-surface px-3.5 py-3", active ? "border-accent shadow-[0_0_0_3px_var(--accent-soft)]" : live && run.total > run.ok ? "border-danger/60" : visited ? "border-live/50" : "border-border")}>
    <Handle type="target" position={Position.Left} className="!size-1.5 !border-0 !bg-border-strong" />
    <div className="flex items-center gap-2.5"><span className={cn("flex size-8 shrink-0 items-center justify-center rounded-lg", active ? "bg-accent-soft text-accent-text" : visited ? "bg-live-soft text-live" : "bg-surface-sunken text-muted")}><Icon icon={STAGE_ICON[def.id]} size={17} /></span><div className="min-w-0"><p className="text-[16px] leading-tight font-semibold text-strong">{def.name}</p><p className="mt-1 font-mono text-[11px] text-faint">{def.code}</p></div></div>
    <p className={cn("mt-2 text-[11px]", active ? "text-accent-text" : "text-muted")}>{label}</p>
    <Handle type="source" position={Position.Right} className="!size-1.5 !border-0 !bg-border-strong" />
  </div>;
});
function FlowEdge(props: EdgeProps) {
  const [path] = getSmoothStepPath({ ...props, borderRadius: 12 });
  const flowing = props.data?.flowing === true;
  const traced = props.data?.traced === true;
  const duration = `${0.78 / Number(props.data?.speed ?? 1)}s`;
  return <>
    {traced ? <path d={path} fill="none" stroke="var(--accent)" strokeWidth={16} opacity={0.18} style={{ pointerEvents: "none" }} /> : null}
    <BaseEdge id={props.id} path={path} style={props.style} markerEnd={props.markerEnd} />
    {flowing ? [0, 1, 2].map(i => <circle key={i} r={i === 0 ? 5 : 3.5} fill="var(--accent)" opacity={1 - i * 0.22} style={{ filter: "drop-shadow(0 0 5px var(--accent))", pointerEvents: "none" }}><animateMotion dur={duration} begin={`${-i * 0.26}s`} repeatCount="indefinite" path={path} /></circle>) : null}
  </>;
}
const nodeTypes = { stage: StageNodeView };
const edgeTypes = { flow: FlowEdge };

function Graph({ strategy, onStrategyChange }: { strategy: Strategy; onStrategyChange: (value: Strategy) => void }) {
  const jobStatus = usePipeline(s => s.jobStatus);
  const jobStrategy = usePipeline(s => s.jobStrategy);
  const inputFiles = usePipeline(s => s.inputFiles);
  const jobId = usePipeline(s => s.jobId);
  const connectionError = usePipeline(s => s.error);
  const stages = usePipeline(s => s.stages);
  const events = usePipeline(s => s.events);
  const activeStage = usePipeline(s => s.activeStage);
  const running = usePipeline(s => s.running);
  const jobRun = usePipeline(s => s.jobRun);
  const { resolvedTheme } = useTheme();
  const mounted = useMounted();
  const reduce = useSyncExternalStore(
    callback => { const query = matchMedia("(prefers-reduced-motion: reduce)"); query.addEventListener("change", callback); return () => query.removeEventListener("change", callback); },
    () => matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => true,
  );
  const container = useRef<HTMLDivElement>(null);
  const manualPan = useRef(false);
  const [visible, setVisible] = useState(true);
  const [pageVisible, setPageVisible] = useState(true);
  const [mode, setMode] = useState<"explain" | "live">("explain");
  const [playing, setPlaying] = useState(false);
  const [step, setStep] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [follow, setFollow] = useState(false);
  const [inspected, setInspected] = useState<StageId | null>(null);
  const [panelStage, setPanelStage] = useState<StageId | null>(null);
  const [expanded, setExpanded] = useState(false);
  const { fitView, setCenter } = useReactFlow();
  const live = mode === "live";
  const effectiveStrategy = live && jobRun && jobRun.strategy in PROFILES ? jobRun.strategy as Strategy : strategy;
  const observed = useMemo(() => live && apiEnabled ? STAGES.filter(s => stages[s.id].lastEventAt !== null).map(s => s.id) : [], [live, stages]);
  const observedKey = observed.join(",");
  const model = useMemo(() => graphModel(effectiveStrategy, observedKey ? observedKey.split(",") as StageId[] : []), [effectiveStrategy, observedKey]);
  const index = Math.min(step, model.ids.length - 1);
  const focus = live ? apiEnabled ? activeStage ?? inspected : null : model.ids[index];
  const def = STAGES.find(s => s.id === focus);
  const lastEvent = live && apiEnabled ? events.find(event => event.stage === focus) : null;
  const panelDef = STAGES.find(stage => stage.id === panelStage);
  const moving = playing && !live && !reduce && visible && pageVisible;

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => setVisible(entry?.isIntersecting ?? false));
    if (container.current) observer.observe(container.current);
    const visibility = () => setPageVisible(!document.hidden);
    document.addEventListener("visibilitychange", visibility);
    return () => { observer.disconnect(); document.removeEventListener("visibilitychange", visibility); };
  }, []);
  useEffect(() => {
    if (!moving) return;
    const timer = window.setTimeout(() => {
      if (index === model.ids.length - 1) setPlaying(false);
      else setStep(index + 1);
    }, 1050 / speed);
    return () => window.clearTimeout(timer);
  }, [moving, index, model.ids.length, speed]);
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      if (follow && focus && model.positions[focus]) {
        const p = model.positions[focus]!;
        void setCenter(p.x + NODE_WIDTH / 2, p.y + NODE_HEIGHT / 2, { zoom: 1.12, duration: reduce ? 0 : 280 });
      }
    });
    return () => cancelAnimationFrame(frame);
  }, [model, follow, focus, fitView, setCenter, reduce, expanded]);
  const layoutKey = model.ids.join(",");
  useEffect(() => {
    if (follow || manualPan.current) return;
    const timer = window.setTimeout(() => { void fitView({ padding: 0.12, maxZoom: 1, duration: reduce ? 0 : 280 }); }, 60);
    return () => clearTimeout(timer);
  }, [layoutKey, expanded, fitView, reduce, follow]);
  useEffect(() => {
    if (!expanded && !panelStage) return;
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") { if (panelStage) { setPanelStage(null); container.current?.querySelector<HTMLElement>(`[data-stage="${panelStage}"]`)?.focus({ preventScroll: true }); } else setExpanded(false); } };
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [expanded, panelStage]);
  useEffect(() => {
    const el = container.current;
    if (!el) return;
    const observer = new ResizeObserver(() => {
      if (!follow) void fitView({ padding: 0.12, maxZoom: 1 });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [fitView, follow]);

  const nodes = useMemo<StageNode[]>(() => model.ids.map((id, i) => ({ id, type: "stage", position: model.positions[id]!, draggable: false, ariaLabel: `${STAGES.find(s => s.id === id)!.name}: explorar etapa`, data: { def: STAGES.find(s => s.id === id)!, run: stages[id], active: focus === id, visited: live ? apiEnabled && stages[id].status === "done" : i < index, live, moving: focus === id && (moving || live && running && activeStage === id && !reduce && visible && pageVisible), selected: panelStage === id, inspect: () => { setPanelStage(id); setPlaying(false); if (live) setInspected(id); else setStep(i); } } })), [model, stages, focus, index, live, moving, running, reduce, visible, pageVisible, panelStage, activeStage]);
  const edges = useMemo<Edge[]>(() => model.edges.map(([source, target]) => {
    const lit = live ? apiEnabled && stages[source].status === "done" && stages[target].lastEventAt !== null : model.ids.indexOf(target) <= index;
    const traced = focus === target;
    const flowing = moving && traced || live && running && !reduce && visible && pageVisible && activeStage === target;
    const stroke = traced ? "var(--accent)" : lit ? "var(--live)" : "var(--border-strong)";
    return { id: `${source}-${target}`, source, target, type: "flow", data: { flowing, traced, speed }, markerEnd: { type: MarkerType.ArrowClosed, color: stroke, width: 18, height: 18 }, style: { stroke, strokeWidth: traced ? 4.5 : lit ? 2.4 : 1.5, opacity: traced || lit ? 1 : 0.55 } };
  }), [model, stages, index, focus, moving, live, running, activeStage, reduce, visible, pageVisible, speed]);
  const seek = (value: number) => { setPlaying(false); setStep(value); };
  return <div ref={container} className={cn("overflow-hidden rounded-xl border border-border bg-surface", expanded && "fixed inset-4 z-50 overflow-y-auto shadow-2xl")}>
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-3">
      <div className="flex flex-wrap items-center gap-3"><label className="text-xs text-muted">Recorrido <select aria-label="Estrategia del grafo" className="ml-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-text" value={effectiveStrategy} disabled={live || running && apiEnabled} onChange={e => { setPanelStage(null); manualPan.current = false; onStrategyChange(e.target.value as Strategy); seek(0); }}>{Object.entries(PROFILES).map(([key, p]) => <option key={key} value={key}>{p.name}</option>)}</select></label>
      <div className="flex gap-1 rounded-lg bg-surface-sunken p-1" aria-label="Origen del grafo"><Button size="sm" variant={!live ? "primary" : "ghost"} aria-pressed={!live} onClick={() => { setMode("explain"); setPlaying(false); }}>Explicación</Button><Button size="sm" variant={live ? "primary" : "ghost"} aria-pressed={live} onClick={() => { setMode("live"); setPlaying(false); }}><Icon icon={Radio} size={13} />Eventos reales</Button></div></div>
      <div className="flex gap-1"><Button size="sm" aria-pressed={!follow} onClick={() => { manualPan.current = false; setFollow(false); void fitView({ padding: 0.12, duration: reduce ? 0 : 280 }); }}><Icon icon={Route} size={14} />Vista general</Button><Button size="sm" aria-pressed={follow} variant={follow ? "primary" : "secondary"} onClick={() => { setInspected(null); setFollow(!follow); }}><Icon icon={Focus} size={14} />Seguir etapa</Button><Button size="sm" aria-label={expanded ? "Reducir grafo" : "Ampliar grafo"} aria-pressed={expanded} onClick={() => { manualPan.current = false; setExpanded(!expanded); }}><Icon icon={Maximize2} size={14} /></Button></div>
    </div>
    <div className="flex flex-wrap justify-between gap-2 border-b border-border px-4 py-2 text-xs text-muted"><span>{live ? apiEnabled ? "Estados recibidos del servidor; sin eventos no implica ejecución." : "Sin API conectada. La simulación de demo no acredita ejecución real." : "Mapa lógico · reproducción didáctica, sin ejecutar el pipeline"}</span><span>Arrastra para explorar · pulsa una etapa</span></div>
    <div className="grid grid-cols-4 gap-1 border-b border-border bg-surface-sunken/40 px-3 py-2" aria-label="Fases del recorrido">
      {([{ name: "Documentos", id: "ingest", hint: "Registrar y clasificar" }, { name: "Lectura", id: model.channels[0]!, hint: "Evidencias por canal" }, { name: effectiveStrategy === "d_hibrido" ? "Fusión" : "Reconciliación", id: "reconcile", hint: "Unidades y confianza" }, { name: "Modelo", id: "family", hint: "Familia, IFC y validación" }] as { name: string; id: StageId; hint: string }[]).map((phase, i) => <button type="button" key={phase.id} className="rounded-lg px-2 py-2 text-left hover:bg-accent-soft focus-visible:outline-2 focus-visible:outline-accent" onClick={() => { setPanelStage(phase.id); if (live) setInspected(phase.id); else seek(model.ids.indexOf(phase.id)); }}><span className="font-mono text-[10px] text-accent-text">0{i + 1}</span><span className="ml-2 text-xs font-semibold text-strong">{phase.name}</span><span className="mt-1 hidden text-[10px] text-muted sm:block">{phase.hint}</span></button>)}
    </div>
    <div className={cn("drafting-grid relative w-full", expanded ? "h-[calc(100dvh-390px)] min-h-[200px]" : "h-[560px] sm:h-[680px]")}>
      {panelDef ? <StageInspector jobLabel={`${jobStrategy ?? "estrategia sin informar"} · ${jobId ?? ""}`} def={panelDef} events={events} actual={apiEnabled && jobId !== null} jobStatus={jobStatus} inputFiles={inputFiles} connectionError={connectionError} onClose={() => { setPanelStage(null); container.current?.querySelector<HTMLElement>(`[data-stage="${panelStage}"]`)?.focus({ preventScroll: true }); }} /> : null}
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes} fitView fitViewOptions={{ padding: 0.12, maxZoom: 1 }} minZoom={0.2} maxZoom={1.6} proOptions={{ hideAttribution: true }} colorMode={mounted && resolvedTheme === "light" ? "light" : "dark"} nodesDraggable={false} nodesConnectable={false} nodesFocusable={false} onMoveStart={event => { if (event) { manualPan.current = true; setFollow(false); } }} zoomOnScroll={false} panOnScroll={false} preventScrolling={false} aria-label="Grafo de etapas del pipeline"><Controls showInteractive={false} /></ReactFlow>
    </div>
    <div className="border-t border-border bg-surface p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="mr-auto flex items-center gap-2 text-xs font-medium text-muted"><span className="size-2 rounded-full bg-accent" />{live ? "Observación de eventos" : `PASO ${String(index + 1).padStart(2, "0")} / ${model.ids.length}`}</span>
        {!live ? <><Button size="sm" aria-label="Volver al inicio" onClick={() => seek(0)}><Icon icon={RotateCcw} size={14} /></Button><Button size="sm" aria-label="Etapa anterior" disabled={index === 0} onClick={() => seek(index - 1)}><Icon icon={ArrowLeft} size={14} /></Button><Button size="sm" variant="primary" disabled={!!reduce} onClick={() => { setPanelStage(null); if (index === model.ids.length - 1) setStep(0); setPlaying(!playing); }}><Icon icon={playing ? Pause : Play} size={14} />{playing ? "Pausar" : "Reproducir explicación"}</Button><Button size="sm" aria-label="Etapa siguiente" disabled={index === model.ids.length - 1} onClick={() => seek(index + 1)}><Icon icon={ArrowRight} size={14} /></Button><select aria-label="Velocidad de explicación" className="rounded-lg border border-border bg-surface px-2 py-1 text-xs text-text" value={speed} onChange={e => setSpeed(Number(e.target.value))}><option value={0.5}>0,5×</option><option value={1}>1×</option><option value={2}>2×</option><option value={3}>3×</option></select></> : null}
      </div>
      {!live ? <input aria-label="Posición en el recorrido" className="my-3 w-full accent-[var(--accent)]" type="range" min={0} max={model.ids.length - 1} value={index} onChange={e => seek(Number(e.target.value))} /> : null}
      <div className="mt-2 grid gap-3 md:grid-cols-[1fr_300px]"><div aria-live={playing ? "off" : "polite"}><p className="font-semibold text-strong">{def?.name ?? "Esperando eventos"}</p><p className="mt-1 max-w-[85ch] text-[13px] leading-relaxed text-muted">{lastEvent?.detail ?? def?.description ?? "Procesa documentos para observar sus etapas. Los trabajos completados conservan sus estados."}</p>{lastEvent ? <p className="mt-2 font-mono text-[11px] text-muted">{lastEvent.file} · {lastEvent.status === "ok" ? "OK" : lastEvent.status === "error" ? "Error" : "Omitida"}</p> : null}</div><p className="border-l-2 border-accent/40 pl-3 text-xs leading-relaxed text-muted">{PROFILES[effectiveStrategy].detail}{reduce ? " Movimiento reducido: explora con las flechas o el deslizador." : ""}</p></div>
    </div>
  </div>;
}
export function PipelineGraph({ strategy = "b_reglas", onStrategyChange = () => {} }: { strategy?: Strategy; onStrategyChange?: (value: Strategy) => void }) {
  return <ReactFlowProvider><Graph strategy={strategy} onStrategyChange={onStrategyChange} /></ReactFlowProvider>;
}
