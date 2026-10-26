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
import { cn } from "@/lib/cn";
import { useMounted } from "@/lib/use-mounted";
import { formatDelta } from "@/lib/format";
import type { ElementId } from "@/lib/mock/fields";
import { DISCIPLINES, type ChangeGroup, type Discipline } from "@/lib/mock/impact";

const ELEMENT_NAMES: Record<string, string> = {
  shell: "Virola",
  "head-top": "Fondo superior",
  "head-bottom": "Fondo inferior",
  skirt: "Faldón",
};
const elementName = (id: ElementId) => ELEMENT_NAMES[id] ?? `Boquilla ${id.replace("nozzle:", "")}`;

type ChangeData = { group: ChangeGroup; active: boolean };
type ElementData = { label: string; active: boolean };
type DisciplineData = { code: Discipline; count: number; active: boolean };

function ChangeNodeView({ data }: NodeProps<Node<ChangeData, "change">>) {
  const { group, active } = data;
  return (
    <div className={cn("w-[220px] rounded-[var(--radius-control)] border bg-surface px-3 py-2", active ? "border-revision" : "border-border")}>
      <p className="flex items-center gap-1.5 text-[12px] font-medium text-text">
        <DeltaMark />
        <span className="truncate">{group.title}</span>
      </p>
      <p className="mt-0.5 text-[11px] text-revision">
        {group.delta ? formatDelta(group.delta.value, group.delta.unit) : group.kind === "nuevo" ? `${group.fields.length} campos nuevos` : group.kind}
      </p>
      <Handle type="source" position={Position.Right} className="!size-1.5 !border-0 !bg-border-strong" />
    </div>
  );
}

function ElementNodeView({ data }: NodeProps<Node<ElementData, "element">>) {
  return (
    <div className={cn("rounded-full border bg-surface-sunken px-3 py-1.5 text-[12px]", data.active ? "border-accent text-accent-text" : "border-border text-muted")}>
      <Handle type="target" position={Position.Left} className="!size-1.5 !border-0 !bg-border-strong" />
      {data.label}
      <Handle type="source" position={Position.Right} className="!size-1.5 !border-0 !bg-border-strong" />
    </div>
  );
}

function DisciplineNodeView({ data }: NodeProps<Node<DisciplineData, "discipline">>) {
  return (
    <div className={cn("flex w-[170px] items-center gap-2.5 rounded-[var(--radius-control)] border bg-surface px-3 py-2", data.active ? "border-revision" : "border-border")}>
      <Handle type="target" position={Position.Left} className="!size-1.5 !border-0 !bg-border-strong" />
      <span className={cn("inline-flex h-7 min-w-9 items-center justify-center rounded-full px-1.5 text-[11px] font-semibold", data.active ? "bg-revision-soft text-revision" : "bg-accent-soft text-accent-text")}>
        {data.code}
      </span>
      <div className="leading-tight">
        <p className="text-[12px] font-medium text-text">{DISCIPLINES[data.code]}</p>
        <p className="text-[11px] text-muted">{data.count} {data.count === 1 ? "cambio" : "cambios"}</p>
      </div>
    </div>
  );
}

function DeltaMark() {
  return (
    <svg viewBox="0 0 12 12" className="size-3 shrink-0 text-revision" aria-hidden>
      <path d="M6 1.5 11 10.5H1Z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}

const nodeTypes: NodeTypes = {
  change: memo(ChangeNodeView),
  element: memo(ElementNodeView),
  discipline: memo(DisciplineNodeView),
};

function Graph({ groups, activeId }: { groups: ChangeGroup[]; activeId: string | null }) {
  const { resolvedTheme } = useTheme();
  const mounted = useMounted();
  const { fitView } = useReactFlow();
  useEffect(() => {
    let raf = 0;
    const onResize = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => fitView({ padding: 0.1 }));
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      cancelAnimationFrame(raf);
    };
  }, [fitView]);

  const { nodes, edges } = useMemo(() => {
    const active = groups.find((g) => g.id === activeId);
    const elements = [...new Set(groups.map((g) => g.elementId))];
    const disciplineCount = new Map<Discipline, number>();
    for (const g of groups) for (const d of g.disciplines) disciplineCount.set(d.code, (disciplineCount.get(d.code) ?? 0) + 1);
    const disciplines = [...disciplineCount.keys()];
    const rowH = 64;
    const colY = (n: number, i: number, total: number) => (i - (n - 1) / 2) * rowH + ((total - 1) / 2) * rowH;
    const total = groups.length;

    const nodes: Node[] = [
      ...groups.map((g, i) => ({
        id: `c:${g.id}`,
        type: "change",
        position: { x: 0, y: i * rowH },
        data: { group: g, active: g.id === activeId },
        draggable: false,
      })),
      ...elements.map((e, i) => ({
        id: `e:${e}`,
        type: "element",
        position: { x: 320, y: colY(elements.length, i, total) + 8 },
        data: { label: elementName(e), active: active?.elementId === e },
        draggable: false,
      })),
      ...disciplines.map((d, i) => ({
        id: `d:${d}`,
        type: "discipline",
        position: { x: 540, y: colY(disciplines.length, i, total) },
        data: { code: d, count: disciplineCount.get(d) ?? 0, active: !!active?.disciplines.some((x) => x.code === d) },
        draggable: false,
      })),
    ];

    const seen = new Set<string>();
    const edges: Edge[] = [];
    for (const g of groups) {
      const on = g.id === activeId;
      edges.push({
        id: `c:${g.id}->e:${g.elementId}`,
        source: `c:${g.id}`,
        target: `e:${g.elementId}`,
        type: "smoothstep",
        animated: on,
        style: { stroke: on ? "var(--revision)" : "var(--border-strong)", strokeWidth: on ? 1.6 : 1.1 },
      });
      for (const d of g.disciplines) {
        const id = `e:${g.elementId}->d:${d.code}`;
        const hot = on;
        if (seen.has(id) && !hot) continue;
        seen.add(id);
        edges.push({
          id: hot ? `${id}:hot` : id,
          source: `e:${g.elementId}`,
          target: `d:${d.code}`,
          type: "smoothstep",
          animated: hot,
          zIndex: hot ? 1 : 0,
          style: { stroke: hot ? "var(--revision)" : "var(--border-strong)", strokeWidth: hot ? 1.6 : 1.1 },
        });
      }
    }
    return { nodes, edges };
  }, [groups, activeId]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.1, maxZoom: 1.1 }}
      proOptions={{ hideAttribution: true }}
      colorMode={mounted && resolvedTheme === "light" ? "light" : "dark"}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      zoomOnScroll={false}
      preventScrolling={false}
      aria-label="Grafo de impacto por disciplina"
    />
  );
}

export function ImpactGraph({ groups, activeId }: { groups: ChangeGroup[]; activeId: string | null }) {
  return (
    <div className="drafting-grid h-[420px] w-full rounded-[var(--radius-card)]">
      <ReactFlowProvider>
        <Graph groups={groups} activeId={activeId} />
      </ReactFlowProvider>
    </div>
  );
}
