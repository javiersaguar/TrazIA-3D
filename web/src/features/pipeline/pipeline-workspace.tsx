"use client";

import { ChevronRight, Info, Play, RotateCcw, X } from "lucide-react";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { HealthRing } from "@/components/ui/data";
import { Tip } from "@/components/ui/controls";
import { SyntheticNotice } from "@/components/ui/notice";
import { Badge, Button, Code, EmptyState, Icon, Panel, PanelHeader, Skeleton } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { relativeSeconds } from "@/lib/format";
import { STAGES, type StageDef, type StageId } from "@/lib/mock/pipeline";
import { useRevision } from "@/lib/queries";
import { usePipeline, type StageRunState } from "@/stores/pipeline";
import { useUi } from "@/stores/ui";
import { STAGE_ICON } from "./stage-meta";

const PipelineGraph = dynamic(() => import("./pipeline-graph").then((m) => m.PipelineGraph), {
  ssr: false,
  loading: () => <Skeleton className="h-[380px] w-full" />,
});

export function PipelineWorkspace() {
  const revision = useUi((s) => s.revision);
  const { data: rev } = useRevision(revision);
  const running = usePipeline((s) => s.running);
  const lastFinishedAt = usePipeline((s) => s.lastFinishedAt);
  const start = usePipeline((s) => s.start);
  const stages = usePipeline((s) => s.stages);
  const [filter, setFilter] = useState<StageId | null>(null);

  // La primera visita lanza la repetición para que la pantalla no empiece vacía.
  const autoStarted = useRef(false);
  useEffect(() => {
    if (rev && !autoStarted.current && !lastFinishedAt && !running) {
      autoStarted.current = true;
      start(rev);
    }
  }, [rev, lastFinishedAt, running, start]);

  return (
    <div className="space-y-5">
      <SyntheticNotice>
        Repetición simulada del pipeline sobre los documentos de V-101 rev {revision}. Los recuentos salen de esos archivos;
        el ritmo es artificial y por eso no se muestran latencias ni costes.
      </SyntheticNotice>

      <Panel className="overflow-hidden">
        <PanelHeader
          title="Grafo del pipeline"
          description="Los extractores corren en paralelo entre la clasificación y la normalización. Las etapas discontinuas aún no existen."
          actions={
            <Button variant="primary" size="sm" disabled={running || !rev} onClick={() => rev && start(rev)}>
              <Icon icon={lastFinishedAt ? RotateCcw : Play} size={14} />
              {running ? "Procesando…" : lastFinishedAt ? "Repetir" : "Procesar"}
            </Button>
          }
        />
        <div className="px-3 pb-3">
          <PipelineGraph />
        </div>
      </Panel>

      <section>
        <div className="mb-3 flex items-end justify-between">
          <div>
            <h2 className="text-[15px] font-semibold text-strong">Etapas</h2>
            <p className="text-[13px] text-muted">El anillo es la salud de la etapa en la última ejecución, no un recuento de ficheros.</p>
          </div>
          <span className="text-xs text-muted">
            {STAGES.filter((s) => s.available).length} de {STAGES.length} etapas disponibles
          </span>
        </div>
        <StageCarousel stages={stages} onShowEvents={setFilter} />
      </section>

      <EventsTable filter={filter} onClearFilter={() => setFilter(null)} />
    </div>
  );
}

function StageCarousel({
  stages,
  onShowEvents,
}: {
  stages: Record<StageId, StageRunState>;
  onShowEvents: (id: StageId) => void;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const bar = useRef<HTMLDivElement>(null);

  // Barra de progreso del carrusel: escala en X, sin provocar layout.
  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const update = () => {
      const visible = el.clientWidth / el.scrollWidth;
      const offset = el.scrollLeft / Math.max(1, el.scrollWidth - el.clientWidth);
      if (bar.current) {
        bar.current.style.width = `${visible * 100}%`;
        bar.current.style.transform = `translateX(${offset * ((1 - visible) / visible) * 100}%)`;
      }
    };
    update();
    el.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      el.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, []);

  return (
    <div>
      <div ref={scroller} className="flex snap-x snap-mandatory gap-4 overflow-x-auto pb-3 [scrollbar-width:none]" tabIndex={0} aria-label="Tarjetas de etapa">
        {STAGES.map((def) => (
          <StageCard key={def.id} def={def} run={stages[def.id]} onShowEvents={() => onShowEvents(def.id)} />
        ))}
      </div>
      <div className="mt-1 h-1 overflow-hidden rounded-full bg-surface-sunken">
        <div ref={bar} className="h-full rounded-full bg-accent/60" />
      </div>
    </div>
  );
}

function StageCard({ def, run, onShowEvents }: { def: StageDef; run: StageRunState; onShowEvents: () => void }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(id);
  }, []);

  const health = def.available && run.total > 0 ? run.ok / run.total : null;
  const badge = !def.available ? (
    <Badge tone="neutral">Próximamente</Badge>
  ) : run.status === "done" ? (
    run.ok === run.total ? <Badge tone="live">Al día</Badge> : <Badge tone="danger">Con errores</Badge>
  ) : (
    <Badge tone="neutral">En espera</Badge>
  );

  return (
    <Panel className={cn("flex w-[340px] shrink-0 snap-start flex-col p-5", !def.available && "border-dashed bg-transparent")}>
      <div className="flex items-start gap-3">
        <span className={cn("inline-flex size-10 items-center justify-center rounded-[var(--radius-control)]", def.available ? "bg-surface-sunken text-text" : "bg-surface-sunken text-faint")}>
          <Icon icon={STAGE_ICON[def.id]} size={18} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="flex flex-wrap items-baseline gap-x-2">
            <span className="font-semibold whitespace-nowrap text-strong">{def.name}</span>
            <Code className="whitespace-nowrap">{def.code}</Code>
          </p>
          <div className="mt-1.5">{badge}</div>
        </div>
        <div className="relative">
          <HealthRing value={health} />
          {def.module ? (
            <Tip content={`Implementado en src/trazia/${def.module}`}>
              <button type="button" className="absolute -top-1 -right-1 rounded-full text-faint hover:text-text" aria-label="Dónde está implementada">
                <Icon icon={Info} size={14} />
              </button>
            </Tip>
          ) : null}
        </div>
      </div>

      <p className="mt-3 min-h-[40px] text-[13px] leading-snug text-muted">{def.description}</p>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-border pt-4 text-[13px]">
        <Metric label="Ficheros OK" value={def.available ? `${run.ok} / ${run.total}` : "—"} />
        <Metric label="Reintentos" value={def.available && run.total ? "0" : "—"} />
        <Metric label="Latencia media" value={<span className="text-faint">Sin medir</span>} />
        <Metric label="Último evento" value={run.lastEventAt ? relativeSeconds((now - run.lastEventAt) / 1000) : "—"} />
      </dl>

      <Button className="mt-5 w-full" onClick={onShowEvents} disabled={run.lastEventAt == null}>
        Ver eventos
        <Icon icon={ChevronRight} size={14} />
      </Button>
    </Panel>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 font-medium text-text">{value}</dd>
    </div>
  );
}

function EventsTable({ filter, onClearFilter }: { filter: StageId | null; onClearFilter: () => void }) {
  const events = usePipeline((s) => s.events);
  const rows = filter ? events.filter((e) => e.stage === filter) : events;
  const stageName = (id: StageId) => STAGES.find((s) => s.id === id)?.name ?? id;

  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        title="Últimos eventos"
        description={filter ? `Solo la etapa ${stageName(filter)}` : "De todas las etapas, el más reciente arriba"}
        actions={
          filter ? (
            <Button size="sm" variant="ghost" onClick={onClearFilter}>
              <Icon icon={X} size={14} />
              Quitar filtro
            </Button>
          ) : null
        }
      />
      {rows.length === 0 ? (
        <EmptyState icon={Play} title="Todavía no hay eventos">
          Pulsa «Procesar» para repetir el pipeline sobre los documentos de la demo.
        </EmptyState>
      ) : (
        <div className="overflow-x-auto px-3 pb-3">
          <table className="w-full border-separate border-spacing-0 text-[13px]">
            <thead>
              <tr className="text-left text-xs text-muted">
                {["Fichero", "Etapa", "Estado", "Detalle", "Cuándo"].map((h, i) => (
                  <th
                    key={h}
                    className={cn(
                      "border-y border-border bg-surface-sunken px-3 py-2.5 font-medium",
                      i === 0 && "rounded-l-[var(--radius-control)] border-l",
                      i === 4 && "rounded-r-[var(--radius-control)] border-r text-right",
                    )}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 14).map((e) => (
                <tr key={e.id} className="animate-[row-in_var(--dur-slow)_var(--ease-out)]">
                  <td className="border-b border-border px-3 py-2.5"><Code className="text-text">{e.file}</Code></td>
                  <td className="border-b border-border px-3 py-2.5">{stageName(e.stage)}</td>
                  <td className="border-b border-border px-3 py-2.5">
                    <Badge tone={e.status === "ok" ? "live" : e.status === "error" ? "danger" : "neutral"}>
                      {e.status === "ok" ? "OK" : e.status === "error" ? "Error" : "Omitido"}
                    </Badge>
                  </td>
                  <td className="border-b border-border px-3 py-2.5 text-muted">{e.detail}</td>
                  <td className="border-b border-border px-3 py-2.5 text-right text-muted">+{e.at.toFixed(1).replace(".", ",")} s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
