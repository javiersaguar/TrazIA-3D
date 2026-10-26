"use client";

import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown, Boxes, CheckCheck, CircleSlash, Coins } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { PlantScene } from "@/components/three";
import { KpiCard } from "@/components/ui/data";
import { Icon, Panel, PanelHeader, Skeleton } from "@/components/ui/primitives";
import { EquipmentStatus, SyntheticBadge } from "@/components/ui/status";
import { cn } from "@/lib/cn";
import { formatPercent } from "@/lib/format";
import type { EquipmentRow } from "@/lib/mock/api";
import { useEquipment, useReviewFields } from "@/lib/queries";
import { useReviewLog } from "@/stores/review-log";
import { useUi } from "@/stores/ui";

const col = createColumnHelper<EquipmentRow>();

export function ProjectWorkspace() {
  const router = useRouter();
  const revision = useUi((s) => s.revision);
  const equipment = useEquipment();
  const fields = useReviewFields(revision);
  const actions = useReviewLog((s) => s.actions);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  const reviewed = fields.data?.filter((f) => f.status !== "candidate").length ?? 0;
  const total = fields.data?.length ?? 0;
  const spark = actions.length ? [0, ...actions.filter((a) => a.rev === revision).map((a) => a.reviewedAfter)] : undefined;
  const real = equipment.data?.filter((e) => !e.illustrative) ?? [];
  const illustrative = (equipment.data?.length ?? 0) - real.length;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          icon={Boxes}
          tone="sky"
          label="Equipos con datos"
          loading={equipment.isPending}
          value={real.length}
          context={`${real.map((e) => e.tag).join(", ")} · ${illustrative} ilustrativos en planta`}
        />
        <KpiCard
          icon={CheckCheck}
          tone="live"
          label={`Campos revisados · rev ${revision}`}
          loading={fields.isPending}
          value={total ? formatPercent(reviewed / total) : "—"}
          context={`${reviewed} de ${total} campos`}
          spark={spark && spark.length > 1 ? spark : undefined}
        />
        <KpiCard
          icon={CircleSlash}
          tone="accent"
          label="Conflictos abiertos"
          loading={fields.isPending}
          value={0}
          context="El núcleo bloquea valores contradictorios antes del modelo"
        />
        <KpiCard
          icon={Coins}
          tone="violet"
          label="Coste de extracción"
          value={<span className="text-muted">Sin medir</span>}
          context="El extractor actual no llama a ningún modelo"
        />
      </div>

      <Panel className="overflow-hidden">
        <PanelHeader
          title="Planta"
          description="Escena ilustrativa: solo V-101 tiene documentos y datos; el resto de equipos ocupa sitio para enseñar la escala."
          actions={<SyntheticBadge />}
        />
        <div className="h-[440px] px-3 pb-3">
          {equipment.data ? (
            <PlantScene
              equipment={equipment.data.map((e) => ({ tag: e.tag, ifcUrl: e.ifcUrl, status: e.status }))}
              onSelect={setSelectedTag}
            />
          ) : (
            <Skeleton className="h-full w-full" />
          )}
        </div>
      </Panel>

      <Panel className="overflow-hidden">
        <PanelHeader title="Equipos" description="Ordena por cualquier columna. Abre V-101 para revisar sus campos." />
        <EquipmentTable
          rows={equipment.data}
          reviewed={{ reviewed, total }}
          selectedTag={selectedTag}
          onOpen={(row) => !row.illustrative && router.push("/revision")}
        />
      </Panel>
    </div>
  );
}

function EquipmentTable({
  rows,
  reviewed,
  selectedTag,
  onOpen,
}: {
  rows: EquipmentRow[] | undefined;
  reviewed: { reviewed: number; total: number };
  selectedTag: string | null;
  onOpen: (row: EquipmentRow) => void;
}) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const columns = useMemo(
    () => [
      col.accessor("tag", {
        header: "Tag",
        cell: (c) => (
          <span className="flex items-center gap-2">
            <span className="font-medium text-text">{c.getValue()}</span>
            {c.row.original.illustrative ? <SyntheticBadge /> : null}
          </span>
        ),
      }),
      col.accessor("kind", { header: "Tipo", cell: (c) => <span className="text-muted">{c.getValue()}</span> }),
      col.accessor("area", { header: "Área", cell: (c) => <span className="text-muted">{c.getValue()}</span> }),
      col.accessor((r) => r.revisions.join(", "), {
        id: "revisions",
        header: "Revisiones",
        cell: (c) => c.getValue() || <span className="text-faint">—</span>,
      }),
      col.accessor("status", { header: "Estado", cell: (c) => <EquipmentStatus status={c.getValue()} /> }),
      col.accessor((r) => (r.illustrative ? -1 : reviewed.reviewed), {
        id: "reviewed",
        header: "Campos revisados",
        meta: { numeric: true },
        cell: (c) =>
          c.row.original.illustrative ? (
            <span className="text-faint">—</span>
          ) : (
            <span>
              {reviewed.reviewed} <span className="text-faint">/ {reviewed.total}</span>
            </span>
          ),
      }),
    ],
    [reviewed],
  );

  const table = useReactTable({
    data: rows ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (!rows) {
    return (
      <div className="space-y-2 px-5 pb-5">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto px-3 pb-3">
      <table className="w-full border-separate border-spacing-0 text-[13px]">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => {
                const numeric = (h.column.columnDef.meta as { numeric?: boolean } | undefined)?.numeric;
                const sorted = h.column.getIsSorted();
                return (
                  <th
                    key={h.id}
                    className={cn(
                      "border-y border-border bg-surface-sunken px-3 py-2.5 text-xs font-medium text-muted first:rounded-l-[var(--radius-control)] first:border-l last:rounded-r-[var(--radius-control)] last:border-r",
                      numeric ? "text-right" : "text-left",
                    )}
                    aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : "none"}
                  >
                    <button
                      type="button"
                      onClick={h.column.getToggleSortingHandler()}
                      className={cn("inline-flex items-center gap-1 hover:text-text", numeric && "flex-row-reverse")}
                    >
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      <Icon icon={sorted === "asc" ? ArrowUp : sorted === "desc" ? ArrowDown : ArrowUpDown} size={13} className={sorted ? "text-accent-text" : "text-faint"} />
                    </button>
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              onClick={() => onOpen(row.original)}
              className={cn(
                "transition-colors duration-[var(--dur-fast)]",
                row.original.illustrative ? "cursor-default" : "cursor-pointer hover:bg-surface-sunken",
                selectedTag === row.original.tag && "bg-accent-soft/60",
              )}
            >
              {row.getVisibleCells().map((cell) => {
                const numeric = (cell.column.columnDef.meta as { numeric?: boolean } | undefined)?.numeric;
                return (
                  <td key={cell.id} className={cn("border-b border-border px-3 py-3", numeric && "text-right")}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
