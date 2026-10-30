"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import { isTyping } from "@/components/shell/global-keys";
import { IfcViewer } from "@/components/three";
import { Segmented } from "@/components/ui/controls";
import { SyntheticNotice } from "@/components/ui/notice";
import { Skeleton } from "@/components/ui/primitives";
import { DEMO, type RevisionId } from "@/lib/mock/api";
import type { ReviewField } from "@/lib/mock/fields";
import { useReviewFields } from "@/lib/queries";
import type { Annotation } from "@/features/viewer3d/types";
import { useSelection } from "@/stores/selection";
import { useUi } from "@/stores/ui";
import { FieldQueue } from "./field-queue";
import { ApprovalButton } from "./approval-button";

import { EvidenceLink } from "./evidence-link";
import { useFieldAction } from "./use-field-action";

const ReviewLayout = dynamic(
  () => import("./review-layout").then((m) => m.ReviewLayout),
  { ssr: false, loading: () => <Skeleton className="h-[620px]" /> },
);

// pdf.js solo en cliente y en diferido
const PdfPanel = dynamic(() => import("./pdf-panel").then((m) => m.PdfPanel), {
  ssr: false,
  loading: () => <Skeleton className="m-3 aspect-[1/1.414]" />,
});

export function ReviewWorkspace() {
  const revision = useUi((s) => s.revision);
  const setRevision = useUi((s) => s.setRevision);
  const { data: fields } = useReviewFields(revision);
  const { selectedId, hoveredId, selectedPath, setSelected, setHovered } =
    useSelection();
  const { apply, undoLast } = useFieldAction(revision);
  const [editingPath, setEditingPath] = useState<string | null>(null);
  const [view, setView] = useState<"iso" | "front" | "top">("iso");
  const [mode, setMode] = useState<"solid" | "xray" | "exploded">("solid");

  const selectField = useCallback(
    (f: ReviewField) => setSelected(f.elementId, f.path),
    [setSelected],
  );

  // Al elegir un elemento en 3D se selecciona su campo de mayor riesgo.
  const onSelectElement = useCallback(
    (id: string) => {
      const first = fields?.find((f) => f.elementId === id);
      if (first) selectField(first);
      else setSelected(id);
    },
    [fields, selectField, setSelected],
  );

  const annotations = useMemo<Annotation[]>(
    () =>
      (fields ?? [])
        .filter(
          (f) =>
            f.elementId === (selectedId ?? "") && typeof f.value === "number",
        )
        .map((f) => ({
          id: f.path,
          label: f.label,
          value: Number(f.correctedValue ?? f.value),
          unit: f.unit,
          confidence: f.confidence,
        })),
    [fields, selectedId],
  );

  // Teclado de revisión: J/K, A, E, S, Ctrl+Z
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!fields?.length || isTyping(e.target)) return;
      const ui = useUi.getState();
      if (ui.commandOpen || ui.shortcutsOpen) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        undoLast();
        return;
      }
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const index = fields.findIndex((f) => f.path === selectedPath);
      const current = fields[index];
      switch (e.key.toLowerCase()) {
        case "j": {
          const next = fields[Math.min(fields.length - 1, index + 1)];
          if (next) selectField(next);
          break;
        }
        case "k": {
          const prev = fields[Math.max(0, index - 1)];
          if (prev) selectField(prev);
          break;
        }
        case "a":
          if (current) {
            apply(current, "accepted");
            const next = fields
              .slice(index + 1)
              .find((f) => f.status === "candidate");
            if (next) selectField(next);
          }
          break;
        case "e":
          if (current) {
            e.preventDefault();
            setEditingPath(current.path);
          }
          break;
        case "s":
          if (current) apply(current, "assumed");
          break;
        default:
          return;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [fields, selectedPath, selectField, apply, undoLast]);

  return (
    <div className="space-y-4">
      <SyntheticNotice>
        Plano y hoja de datos sintéticos. En modo API, la aprobación humana se
        guarda vinculada a la huella de esta versión.
      </SyntheticNotice>

      <div className="flex flex-wrap items-center gap-3">
        <Segmented<RevisionId>
          label="Revisión"
          value={revision}
          onChange={(r) => {
            setRevision(r);
            setEditingPath(null);
          }}
          options={[
            { value: "A", label: "rev A" },
            { value: "B", label: "rev B" },
          ]}
        />
        <Segmented
          label="Vista del modelo"
          value={view}
          onChange={setView}
          options={[
            { value: "iso", label: "Iso" },
            { value: "front", label: "Alzado" },
            { value: "top", label: "Planta" },
          ]}
        />
        <Segmented
          label="Modo del modelo"
          value={mode}
          onChange={setMode}
          options={[
            { value: "solid", label: "Sólido" },
            { value: "xray", label: "Rayos X" },
            { value: "exploded", label: "Explosionado" },
          ]}
        />
        <div className="ml-auto">
          <ApprovalButton key={revision} revision={revision} fields={fields} />
        </div>
      </div>

      <ReviewLayout
        pdf={
          fields ? (
            <PdfPanel
              key={revision}
              url={DEMO.revisions[revision].pdf}
              fields={fields}
              selectedPath={selectedPath}
              selectedId={selectedId}
              hoveredId={hoveredId}
              onSelect={selectField}
              onHover={(f) => setHovered(f?.elementId ?? null)}
            />
          ) : (
            <Skeleton className="m-3 aspect-[1/1.414]" />
          )
        }
        model={
          <div className="h-full min-h-0 p-2">
            <IfcViewer
              ifcUrl={DEMO.revisions[revision].ifc}
              selectedId={selectedId ?? undefined}
              hoveredId={hoveredId ?? undefined}
              onSelect={onSelectElement}
              onHover={setHovered}
              annotations={annotations}
              view={view}
              mode={mode}
            />
          </div>
        }
        fields={
          <FieldQueue
            fields={fields}
            selectedPath={selectedPath}
            hoveredId={hoveredId}
            editingPath={editingPath}
            onSelect={selectField}
            onHover={(f) => setHovered(f?.elementId ?? null)}
            onAction={(f, status, value) => apply(f, status, value)}
            onEdit={setEditingPath}
          />
        }
      >
        <EvidenceLink
          key={selectedPath}
          path={selectedPath}
          elementId={selectedId}
        />
      </ReviewLayout>
    </div>
  );
}
