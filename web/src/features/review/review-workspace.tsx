"use client";

import { Stamp } from "lucide-react";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { isTyping } from "@/components/shell/global-keys";
import { IfcViewer } from "@/components/three";
import { Segmented, Tip } from "@/components/ui/controls";
import { SyntheticNotice } from "@/components/ui/notice";
import { Button, Icon, Panel, Skeleton } from "@/components/ui/primitives";
import { DEMO, type RevisionId } from "@/lib/mock/api";
import type { ReviewField } from "@/lib/mock/fields";
import { useReviewFields } from "@/lib/queries";
import type { Annotation } from "@/features/viewer3d/types";
import { useSelection } from "@/stores/selection";
import { useUi } from "@/stores/ui";
import { FieldQueue } from "./field-queue";
import { useFieldAction } from "./use-field-action";

// pdf.js solo en cliente y en diferido
const PdfPanel = dynamic(() => import("./pdf-panel").then((m) => m.PdfPanel), {
  ssr: false,
  loading: () => <Skeleton className="m-3 aspect-[1/1.414]" />,
});

export function ReviewWorkspace() {
  const revision = useUi((s) => s.revision);
  const setRevision = useUi((s) => s.setRevision);
  const { data: fields } = useReviewFields(revision);
  const { selectedId, hoveredId, selectedPath, setSelected, setHovered } = useSelection();
  const { apply, undoLast } = useFieldAction(revision);
  const [editingPath, setEditingPath] = useState<string | null>(null);
  const [view, setView] = useState<"iso" | "front" | "top">("iso");
  const [mode, setMode] = useState<"solid" | "xray" | "exploded">("solid");

  const selectField = useCallback((f: ReviewField) => setSelected(f.elementId, f.path), [setSelected]);

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
        .filter((f) => f.elementId === (selectedId ?? "") && typeof f.value === "number")
        .map((f) => ({ id: f.path, label: f.label, value: Number(f.correctedValue ?? f.value), unit: f.unit, confidence: f.confidence })),
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
            const next = fields.slice(index + 1).find((f) => f.status === "candidate");
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

  const pending = fields?.filter((f) => f.status === "candidate").length ?? 0;

  return (
    <div className="space-y-4">
      <SyntheticNotice>Plano y hoja de datos generados para la demo; la aprobación aquí no firma nada en el núcleo.</SyntheticNotice>

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
          <Tip content={pending ? `Faltan ${pending} campos por revisar` : "Registra la revisión humana de esta versión"}>
            <span>
              <Button
                variant="primary"
                disabled={pending > 0}
                onClick={() =>
                  toast.success(`Revisión ${revision} lista para aprobar`, {
                    description: "En el producto se firma con la huella de datos (trazia approve). En la demo no se guarda.",
                  })
                }
              >
                <Icon icon={Stamp} size={15} />
                Aprobar revisión
              </Button>
            </span>
          </Tip>
        </div>
      </div>

      <div className="grid h-[calc(100dvh-236px)] min-h-[620px] grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)_380px]">
        <Panel className="min-h-0 overflow-hidden">
          {fields ? (
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
          )}
        </Panel>

        <Panel className="min-h-0 overflow-hidden p-2">
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
        </Panel>

        <Panel className="min-h-0 overflow-hidden">
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
        </Panel>
      </div>
    </div>
  );
}
