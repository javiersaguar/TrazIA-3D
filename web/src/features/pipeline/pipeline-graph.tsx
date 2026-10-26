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
import { useMounted } from "@/lib/use-mounted";
import { STAGE_EDGES, STAGES, type StageDef, type StageId } from "@/lib/mock/pipeline";
import { usePipeline, type StageRunState } from "@/stores/pipeline";
import { STAGE_ICON } from "./stage-meta";

type StageNodeData = { def: StageDef; run: StageRunState; active: boolean };
type StageNode = Node<StageNodeData, "stage">;

function StageNodeView({ data }: NodeProps<StageNode>) {
  const { def, run, active } = data;
  const done = run.status === "done";
  return (
    <div
      className={cn(
        "relative w-[172px] rounded-[var(--radius-card)] border bg-surface px-3 py-2.5",
        "transition-[border-color,background-color,box-shadow] duration-[var(--dur-base)] ease-[var(--ease-out)]",
        !def.available && "border-dashed border-border-strong bg-transparent",
        def.available && !done && !active && "border-border",
        done && "border-live/50",
        active && def.available && "border-accent shadow-[0_0_0_3px_var(--accent-soft)]",
      )}
    >
      <Handle type="target" position={Position.Left} className="!size-1.5 !border-0 !bg-border-strong" />
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "inline-flex size-7 items-center justify-center rounded-[6px]",
            def.available ? (done ? "bg-live-soft text-live" : "bg-accent-soft text-accent-text") : "bg-surface-sunken text-faint",
          )}
        >
          <Icon icon={STAGE_ICON[def.id]} size={15} />
        </span>
        <div className="min-w-0 flex-1 leading-tight">
          <p className={cn("truncate text-[13px] font-medium", def.available ? "text-text" : "text-muted")}>{def.name}</p>
          <p className="truncate font-mono text-[10.5px] text-faint">{def.code}</p>
        </div>
      </div>
      <p className="mt-2 text-[11px] text-muted">
        {!def.available
          ? "Próximamente"
          : active
            ? "Procesando…"
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
  ingest: { x: 0, y: 160 },
  classify: { x: 220, y: 160 },
  extract_labels: { x: 460, y: 0 },
  extract_tables: { x: 460, y: 80 },
  extract_ocr: { x: 460, y: 160 },
  extract_vision: { x: 460, y: 240 },
  extract_hdm: { x: 460, y: 320 },
  reconcile: { x: 700, y: 160 },
  family: { x: 920, y: 160 },
  ifc: { x: 1140, y: 160 },
  validate: { x: 1360, y: 160 },
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
        data: { def, run: stages[def.id], active: activeStage === def.id },
      })),
    [stages, activeStage],
  );

  const edges = useMemo<Edge[]>(
    () =>
      STAGE_EDGES.map(([source, target]) => {
        const available = STAGES.find((s) => s.id === source)?.available && STAGES.find((s) => s.id === target)?.available;
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
    <div className="drafting-grid h-[380px] w-full rounded-[var(--radius-card)]">
      <ReactFlowProvider>
        <Graph />
      </ReactFlowProvider>
    </div>
  );
}
