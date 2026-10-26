"use client";

import { FileDiff, Fingerprint, GitCompareArrows, Pause, Play, Ruler } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { isTyping } from "@/components/shell/global-keys";
import { RevisionMorph } from "@/components/three";
import { Segmented, Tip } from "@/components/ui/controls";
import { KpiCard } from "@/components/ui/data";
import { SyntheticNotice } from "@/components/ui/notice";
import { Badge, Code, Icon, Kbd, Panel, PanelHeader, Skeleton } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { formatDelta, formatValue, shortHash } from "@/lib/format";
import { DEMO } from "@/lib/mock/api";
import { groupChanges, type ChangeGroup } from "@/lib/mock/impact";
import { useChanges } from "@/lib/queries";
import { useSelection } from "@/stores/selection";

const ImpactGraph = dynamic(() => import("./impact-graph").then((m) => m.ImpactGraph), {
  ssr: false,
  loading: () => <Skeleton className="h-[420px] w-full" />,
});

type Mode = "A" | "B" | "delta";

const LEAF_LABEL: Record<string, string> = {
  azimuth: "orientación",
  diameter: "diámetro",
  elevation: "elevación",
  projection: "proyección",
};
const STEP_MS = 2600;

export function ChangesWorkspace() {
  const { data: diff } = useChanges();
  const groups = useMemo(() => (diff ? groupChanges(diff.changes) : []), [diff]);
  const setSelected = useSelection((s) => s.setSelected);
  const [mode, setMode] = useState<Mode>("delta");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(1);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const focus = useCallback(
    (g: ChangeGroup) => {
      setActiveId(g.id);
      setSelected(g.elementId, g.fields[0]?.path ?? null);
    },
    [setSelected],
  );

  // Reproducción: recorre los cambios por severidad; el avance del morph acompaña al paso.
  useEffect(() => {
    if (!playing || !groups.length) return;
    const index = groups.findIndex((g) => g.id === activeId);
    const next = groups[index + 1];
    timer.current = setTimeout(
      () => {
        if (!next) {
          setPlaying(false);
          setProgress(1);
          return;
        }
        focus(next);
        setProgress((index + 2) / groups.length);
      },
      index < 0 ? 150 : STEP_MS,
    );
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [playing, activeId, groups, focus]);

  const togglePlay = useCallback(() => {
    setMode("delta");
    setPlaying((p) => {
      if (!p) {
        setActiveId(null);
        setProgress(0);
      }
      return !p;
    });
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== " " || isTyping(e.target) || e.target instanceof HTMLButtonElement) return;
      e.preventDefault();
      togglePlay();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [togglePlay]);

  const morphProgress = mode === "A" ? 0 : mode === "B" ? 1 : progress;
  const active = groups.find((g) => g.id === activeId);
  const step = active ? groups.indexOf(active) + 1 : 0;

  return (
    <div className="space-y-5">
      <SyntheticNotice>Las revisiones A y B se generaron para la demo con cambios conocidos.</SyntheticNotice>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard icon={GitCompareArrows} tone="revision" label="Cambios de campos" loading={!diff} value={diff?.summary.changes ?? 0} context={`${groups.length} cambios agrupados por elemento`} />
        <KpiCard icon={Ruler} tone="accent" label="Afectan a la geometría" loading={!diff} value={diff?.summary.geometry_changes ?? 0} context="El IFC rev B conserva los GUID" />
        <KpiCard icon={FileDiff} tone="sky" label="Documentos nuevos" loading={!diff} value={diff?.summary.document_changes ?? 0} context="GA y hoja de datos reemitidos" />
        <KpiCard
          icon={Fingerprint}
          tone="violet"
          label="Huella de datos"
          loading={!diff}
          value={<span className="font-mono text-[18px]">{diff ? `${shortHash(diff.before_sha256, 6)} → ${shortHash(diff.after_sha256, 6)}` : ""}</span>}
          context="SHA-256 del JSON antes y después"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[400px_minmax(0,1fr)]">
        <Panel className="flex max-h-[640px] min-h-0 flex-col overflow-hidden">
          <PanelHeader title="Cambios rev A → rev B" description="Ordenados por severidad. Selecciona uno para verlo en el modelo y en el grafo." />
          <ol className="min-h-0 flex-1 space-y-1.5 overflow-y-auto px-3 pb-3">
            {!diff
              ? Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-24 w-full" />)
              : groups.map((g) => <ChangeItem key={g.id} group={g} active={g.id === activeId} onSelect={() => (setPlaying(false), focus(g))} />)}
          </ol>
        </Panel>

        <Panel className="relative flex min-h-[640px] flex-col overflow-hidden">
          <div className="flex items-center gap-3 px-4 pt-3 pb-2">
            <Segmented<Mode>
              label="Comparación"
              value={mode}
              onChange={(m) => {
                setMode(m);
                setPlaying(false);
              }}
              options={[
                { value: "A", label: "rev A" },
                { value: "B", label: "rev B" },
                { value: "delta", label: "Δ", title: "Fantasma de la rev A sobre la rev B" },
              ]}
            />
            <label className="ml-auto flex items-center gap-2 text-xs text-muted">
              Avance
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={morphProgress}
                onChange={(e) => {
                  setMode("delta");
                  setPlaying(false);
                  setProgress(Number(e.target.value));
                }}
                className="w-40 accent-[var(--revision)]"
                aria-label="Avance de la rev A a la rev B"
              />
              <span className="w-11 text-right whitespace-nowrap">{Math.round(morphProgress * 100)} %</span>
            </label>
          </div>
          <div className="min-h-0 flex-1 px-2 pb-2">
            <RevisionMorph
              fromUrl={DEMO.revisions.A.ifc}
              toUrl={DEMO.revisions.B.ifc}
              changes={diff}
              progress={morphProgress}
              onProgress={(p) => {
                // Arrastrar el avance en el visor pausa también la reproducción de la pantalla.
                setPlaying(false);
                setMode("delta");
                setProgress(p);
              }}
            />
          </div>

          {/* Caja de narración, como en Ciberconciencia */}
          <div className="absolute bottom-5 left-5 flex max-w-[460px] items-start gap-3 rounded-[var(--radius-card)] border border-border bg-surface-raised/95 px-3.5 py-3 shadow-[var(--shadow-pop)]">
            <Tip content={playing ? "Pausar" : "Reproducir los cambios"} shortcut={["Espacio"]}>
              <button
                type="button"
                onClick={togglePlay}
                disabled={!groups.length}
                aria-label={playing ? "Pausar" : "Reproducir los cambios"}
                className="inline-flex size-8 shrink-0 items-center justify-center rounded-full border border-border text-text hover:bg-surface-sunken"
              >
                <Icon icon={playing ? Pause : Play} size={14} />
              </button>
            </Tip>
            <div className="min-w-0 text-[13px]">
              <AnimatePresence mode="wait" initial={false}>
                <motion.p
                  key={active?.id ?? "idle"}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.18 }}
                  className="text-text"
                >
                  {active ? narration(active) : "Reproduce los cambios: la cámara acompaña cada paso y el modelo pasa de la rev A a la rev B."}
                </motion.p>
              </AnimatePresence>
              <p className="mt-1 text-xs text-muted">
                {active ? `Paso ${step} de ${groups.length}` : <>Pulsa <Kbd>Espacio</Kbd> para empezar</>}
              </p>
            </div>
          </div>
        </Panel>
      </div>

      <Panel className="overflow-hidden">
        <PanelHeader
          title="Impacto por disciplina"
          description="Cambio → elemento → disciplinas que deben revisarlo. Reglas explicables, pendientes de validar con ingeniería."
        />
        <div className="px-3 pb-3">
          <ImpactGraph groups={groups} activeId={activeId} />
        </div>
      </Panel>
    </div>
  );
}

function narration(g: ChangeGroup): string {
  const d = g.disciplines.map((x) => x.code).join(", ");
  if (g.kind === "nuevo") return `${g.title}: aparece en la rev B con ${g.fields.length} datos. Revisan ${d}.`;
  if (g.delta) return `${g.title}: ${formatDelta(g.delta.value, g.delta.unit)}. Revisan ${d}.`;
  return `${g.title} cambia. Revisan ${d}.`;
}

function ChangeItem({ group, active, onSelect }: { group: ChangeGroup; active: boolean; onSelect: () => void }) {
  const f = group.fields[0];
  const source = f?.after_source ?? f?.before_source;
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        aria-pressed={active}
        className={cn(
          "w-full rounded-[var(--radius-card)] border px-3.5 py-3 text-left",
          "transition-[background-color,border-color] duration-[var(--dur-fast)] ease-[var(--ease-out)]",
          active ? "border-revision/60 bg-revision-soft" : "border-border hover:bg-surface-sunken",
        )}
      >
        <div className="flex items-start gap-2.5">
          <svg viewBox="0 0 16 16" className="mt-0.5 size-4 shrink-0 text-revision" aria-hidden>
            <path d="M8 2 14.5 13.5h-13Z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
          </svg>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <p className="truncate font-medium text-text">{group.title}</p>
              <Badge tone={group.severity === "alta" ? "danger" : group.severity === "media" ? "warning" : "neutral"}>{group.severity}</Badge>
            </div>
            {group.delta && f ? (
              <p className="mt-1 text-[13px]">
                <span className="font-semibold text-revision">{formatDelta(group.delta.value, group.delta.unit)}</span>
                <span className="text-muted">
                  {" "}
                  · {formatValue(f.before!.value, f.before!.unit)} → {formatValue(f.after!.value, f.after!.unit)}
                </span>
              </p>
            ) : (
              <p className="mt-1 text-[13px] text-muted">
                {group.fields
                  .map((x) => {
                    const leaf = x.path.split(".").at(-1) ?? "";
                    return `${LEAF_LABEL[leaf] ?? leaf} ${x.after ? formatValue(x.after.value, x.after.unit) : "—"}`;
                  })
                  .join(" · ")}
              </p>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-1">
              {group.disciplines.map((d) => (
                <Tip key={d.code} content={d.reason}>
                  <span className="rounded-full bg-accent-soft px-1.5 py-0.5 text-[11px] font-medium text-accent-text">{d.code}</span>
                </Tip>
              ))}
              {source ? (
                <span className="ml-auto text-[11px] text-faint">
                  <Code className="text-[11px]">{source.document_id}</Code>
                  {source.page ? ` · pág. ${source.page}` : source.cell ? ` · ${source.cell}` : ""}
                </span>
              ) : null}
            </div>
          </div>
        </div>
      </button>
    </li>
  );
}
