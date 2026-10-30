"use client";

import "@xyflow/react/dist/style.css";
import {
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
  type NodeTypes,
} from "@xyflow/react";
import { useTheme } from "next-themes";
import { memo, useEffect, useMemo } from "react";
import { Icon } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { apiEnabled } from "@/lib/api/config";
import { useMounted } from "@/lib/use-mounted";
import { STAGE_EDGES, STAGES, type StageDef, type StageId } from "@/lib/mock/pipeline";
import { usePipeline, type StageRunState } from "@/stores/pipeline";
import { STAGE_ICON } from "./stage-meta";

type StageNodeData = { def: StageDef; run: StageRunState; active: boolean; column: number };
type StageNode = Node<StageNodeData, "stage">;

function StageNodeView({ data }: NodeProps<StageNode>) {
  const { def, run, active, column } = data;
  const done = run.status === "done";
  const available = apiEnabled ? run.lastEventAt !== null : def.available;
  return (
    <div
      // Los nodos entran por columnas, de izquierda a derecha, siguiendo el flujo
      style={{ animationDelay: `${column * 60}ms` }}
      className={cn(
        "pipeline-node relative w-[172px] rounded-[var(--radius-card)] border bg-surface px-3 py-2.5",
        "transition-[border-color,background-color,box-shadow] duration-[var(--dur-base)] ease-[var(--ease-out)]",
        !available && "border-dashed border-border-strong bg-transparent",
        available && !done && !active && "border-border",
        done && "border-live/50",
        active && available && "border-accent shadow-[0_0_0_3px_var(--accent-soft)]",
      )}
    >
      {active && available ? <span aria-hidden className="pipeline-breathe pointer-events-none absolute -inset-[4px] rounded-[14px] border border-accent" /> : null}
      <Handle type="target" position={Position.Left} className="!size-1.5 !border-0 !bg-border-strong" />
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "inline-flex size-7 items-center justify-center rounded-[6px]",
            available ? (done ? "bg-live-soft text-live" : "bg-accent-soft text-accent-text") : "bg-surface-sunken text-faint",
          )}
        >
          <Icon icon={STAGE_ICON[def.id]} size={15} />
        </span>
        <div className="min-w-0 flex-1 leading-tight">
          <p className={cn("truncate text-[13px] font-medium", available ? "text-text" : "text-muted")}>{def.name}</p>
          <p className="truncate font-mono text-[10.5px] text-faint">{def.code}</p>
        </div>
      </div>
      <p className="mt-2 text-[11px] text-muted">
        {!available
          ? apiEnabled ? "Sin ejecutar" : "Próximamente"
          : active
            ? apiEnabled ? "Último evento" : "Procesando…"
            : done
              ? `${run.ok}/${run.total} correctos`
              : "En espera"}
      </p>
      <Handle type="source" position={Position.Right} className="!size-1.5 !border-0 !bg-border-strong" />
    </div>
  );
}

const StageNodeMemo = memo(StageNodeView);
const nodeTypes: NodeTypes = { stage: StageNodeMemo };

/* Posiciones fijas: los extractores en columna, en paralelo. */
const POSITIONS: Record<StageId, { x: number; y: number }> = {
  ingest: { x: 0, y: 230 }, classify: { x: 200, y: 230 },
  extract_labels: { x: 410, y: 0 }, extract_tables: { x: 410, y: 85 },
  extract_ocr: { x: 410, y: 170 }, extract_detector: { x: 410, y: 255 },
  extract_vision: { x: 410, y: 340 }, extract_hdm: { x: 410, y: 425 },
  geometry2d: { x: 620, y: 85 }, rag: { x: 620, y: 230 }, memory: { x: 620, y: 375 },
  reconcile: { x: 840, y: 230 }, calibrate: { x: 1040, y: 230 },
  family: { x: 1240, y: 230 }, ifc: { x: 1440, y: 230 }, validate: { x: 1640, y: 230 },
};

function Graph() {
  const stages = usePipeline((s) => s.stages);
  const activeStage = usePipeline((s) => s.activeStage);
  const { resolvedTheme } = useTheme();
  const mounted = useMounted();

  const { fitView } = useReactFlow();
  useEffect(() => {
    let raf = 0;
    const onResize = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => fitView({ padding: 0.12 }));
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      cancelAnimationFrame(raf);
    };
  }, [fitView]);

  const nodes = useMemo<StageNode[]>(
    () =>
      STAGES.map((def) => ({
        id: def.id,
        type: "stage",
        position: POSITIONS[def.id],
        draggable: false,
        selectable: false,
        data: { def, run: stages[def.id], active: activeStage === def.id, column: Math.round(POSITIONS[def.id].x / 205) },
      })),
    [stages, activeStage],
  );

  const edges = useMemo<Edge[]>(
    () =>
      STAGE_EDGES.map(([source, target]) => {
        const available = apiEnabled ? stages[source].total > 0 && stages[target].total > 0 : STAGES.find((s) => s.id === source)?.available && STAGES.find((s) => s.id === target)?.available;
        const flowing = activeStage === target && stages[source].status !== "idle";
        const done = stages[source].status === "done" && stages[target].status === "done";
        return {
          id: `${source}-${target}`,
          source,
          target,
          type: "smoothstep",
          animated: flowing,
          style: {
            stroke: done ? "var(--live)" : flowing ? "var(--accent)" : "var(--border-strong)",
            strokeWidth: done || flowing ? 1.6 : 1.2,
            strokeDasharray: available ? undefined : "4 4",
            opacity: available ? 1 : 0.6,
          },
        };
      }),
    [stages, activeStage],
  );

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.12, maxZoom: 1.2 }}
      proOptions={{ hideAttribution: true }}
      colorMode={mounted && resolvedTheme === "light" ? "light" : "dark"}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      panOnScroll={false}
      zoomOnScroll={false}
      preventScrolling={false}
      aria-label="Grafo de etapas del pipeline"
    />
  );
}

export function PipelineGraph() {
  return (
    <div className="drafting-grid h-[480px] w-full rounded-[var(--radius-card)]">
      <ReactFlowProvider>
        <Graph />
      </ReactFlowProvider>
    </div>
  );
}
