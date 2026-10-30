"use client";

import { studyScope } from "@/features/study/scope";
import { CircleDashed, FlaskConical, Terminal } from "lucide-react";
import { useMemo, useState } from "react";
import { Segmented } from "@/components/ui/controls";
import { SyntheticNotice } from "@/components/ui/notice";
import { Badge, Button, Code, EmptyState, Panel, PanelHeader, Skeleton } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import {
  isStudyEmpty,
  type StudyMetrics,
  type StudyReport,
  type StudyVariant,
} from "@/lib/mock/estudio-types";
import { useStudy } from "@/lib/queries";

/* Proveedores reservados del generador v2 (DEC-21): nunca se usan para desarrollar ni entrenar. */
const RESERVED = new Set(["meridian", "cantabrico"]);
/* Una variante que no lee nada puntúa 0,20 (escala 0,10 + innovación 0,10): ver docs/ESTUDIO.md. */
const FLOOR = 0.2;

const pct = (x: number | null | undefined, d = 1) =>
  x == null ? "—" : `${(x * 100).toFixed(d).replace(".", ",")} %`;
const num = (x: number | null | undefined, d = 3) => (x == null ? "—" : x.toFixed(d).replace(".", ","));
const signed = (x: number) => `${x > 0 ? "+" : x < 0 ? "−" : ""}${Math.abs(x).toFixed(3).replace(".", ",")}`;
const pValue = (p: number) => (p < 1e-6 ? "< 10⁻⁶" : p < 0.001 ? p.toExponential(1).replace(".", ",") : num(p, 3));

const STRATEGY_NAMES: Record<string, string> = {
  a: "A · visión + 3D",
  b: "B · datos + reglas",
  c: "C · RAG",
  d: "D · híbrido",
};

function strategyFamily(id: string) {
  return STRATEGY_NAMES[id.charAt(0)] ?? id;
}

export function EstudioWorkspace() {
  const { data, isPending, isError, error, refetch } = useStudy();

  if (isPending) return <LoadingState />;
  if (isError) return <Panel className="p-5"><p role="alert" className="text-warning">No se pudo cargar el estudio: {error.message}</p><Button className="mt-3" onClick={() => void refetch()}>Reintentar</Button></Panel>;
  if (!data || isStudyEmpty(data) || data.variants.length === 0) {
    return (
      <Panel>
        <EmptyState icon={CircleDashed} title="Aún no hay resultados del estudio">
          Lectura publica <Code>generated/estudio/estudio.json</Code> al ejecutar el estudio. No se muestran cifras
          simuladas: esta pantalla se llena solo con mediciones.
        </EmptyState>
        <Reproduce className="mx-5 mb-5" />
      </Panel>
    );
  }
  return <StudyView study={data} />;
}

function LoadingState() {
  return (
    <div className="space-y-5">
      <Skeleton className="h-10 w-full" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
      <Skeleton className="h-72 w-full" />
    </div>
  );
}

function StudyView({ study }: { study: StudyReport }) {
  const ranked = useMemo(
    () => [...study.variants].sort((a, b) => b.metrics.score - a.metrics.score),
    [study.variants],
  );
  const scored: string[] = study.datasets.filter((d) => d === "S-dev" || d === "S-reservado");
  const equipment = Object.entries(study.sets ?? {})
    .filter(([k]) => scored.includes(k))
    .reduce((n, [, v]) => n + v.cases, 0);
  const scope = studyScope(study);
  const pending = (study.unmeasured ?? []).filter((u) => !u.id.startsWith("S-"));
  const total = study.variants.length + pending.length;

  return (
    <div className="space-y-5">
      {study.synthetic === true ? <SyntheticNotice>
        {`Estudio sobre ${equipment} equipos de ${scope.vendors} estilos medidos (${scored.join(" + ")}), en ${scope.degradations} degradaciones, con generador ${study.generator ?? "sin versión"} e intervalos bootstrap (semilla ${study.seed}).`}
      </SyntheticNotice> : <Panel className="p-4 text-sm text-muted">Informe local. Comprueba su origen y alcance antes de interpretar las cifras.</Panel>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <RecommendationCard label="Planos vectoriales" variant={study.recommendation.vectorial} study={study} />
        <RecommendationCard label="Planos escaneados" variant={study.recommendation.escaneado} study={study} />
        <Panel className="p-5">
          <p className="text-xs text-muted">Variantes medidas</p>
          <p className="mt-1 text-[28px] leading-none font-semibold text-strong tabular-nums">
            {study.variants.length}
            <span className="text-[15px] font-normal text-muted"> / {total}</span>
          </p>
          <div className="mt-3 h-1.5 rounded-full bg-surface-sunken" aria-hidden>
            <div
              className="h-full origin-left rounded-full bg-accent transition-transform duration-[var(--dur-slow)] ease-[var(--ease-out)]"
              style={{ transform: `scaleX(${total ? study.variants.length / total : 0})` }}
            />
          </div>
          <p className="mt-3 text-[13px] text-muted">
            Cada estrategia se añade al estudio en cuanto existe. Las que faltan aparecen abajo con el motivo, nunca con
            cifras inventadas.
          </p>
          <p className="mt-2 text-xs text-faint">Generado {new Date(study.generated_at).toLocaleString("es-ES")}</p>
        </Panel>
      </div>

      <Panel className="overflow-hidden">
        <PanelHeader
          title="Puntuación GA2MODEL con intervalo del 95 %"
          description="0,35 geometría + 0,25 atributos·(1 − ECE) + 0,20 F1 de cambios + 0,10 escala + 0,10 innovación. Solo ganan las variantes con alucinación < 1 % y cita del 100 %."
        />
        <ForestPlot variants={ranked} />
      </Panel>

      <Panel className="overflow-hidden">
        <PanelHeader
          title="Métricas por variante"
          description={`Sobre ${scored.join(" + ") || study.datasets.join(" + ")}. La geometría vale 0 si la revisión no llega a IFC.`}
        />
        <MetricsTable variants={ranked} />
      </Panel>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel>
          <PanelHeader
            title="Ablaciones"
            description="Cuánto cae la puntuación al quitar un canal. Intervalo pareado: si no cruza el cero, el canal aporta."
          />
          <Ablations study={study} />
        </Panel>
        <Panel>
          <PanelHeader
            title="Frontera coste–acierto"
            description="Segundos por revisión frente a puntuación. Las variantes de la frontera no las mejora ninguna otra en las dos cosas a la vez."
          />
          <ParetoChart variants={ranked} front={study.pareto} />
        </Panel>
      </div>

      <Breakdown variants={ranked} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel>
          <PanelHeader
            title="Comparaciones pareadas"
            description="McNemar exacto sobre los mismos campos de los mismos documentos."
          />
          <Pairwise study={study} />
        </Panel>
        <Panel>
          <PanelHeader title="Sin medir todavía" description="Lo que falta y por qué. Se mide con la misma vara al llegar." />
          <Unmeasured study={study} />
        </Panel>
      </div>

      <Panel className="p-5">
        <p className="font-medium text-strong">Lectura de los datos</p>
        <p className="mt-1 max-w-[110ch] text-[13px] text-muted">{study.recommendation.rationale}</p>
        <Reproduce className="mt-4" />
      </Panel>
    </div>
  );
}

function RecommendationCard({ label, variant, study }: { label: string; variant: string | null; study: StudyReport }) {
  const v = study.variants.find((x) => x.id === variant);
  return (
    <Panel className="p-5">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-muted">Recomendación · {label}</p>
        {v ? (
          <Badge tone={v.eligible === false ? "warning" : "approved"}>
            {v.eligible === false ? "No cumple restricciones" : "Cumple restricciones"}
          </Badge>
        ) : null}
      </div>
      {v ? (
        <>
          <p className="mt-1.5 text-[20px] font-semibold text-strong">{strategyFamily(v.id)}</p>
          <p className="text-[13px] text-muted">
            <Code className="text-muted">{v.id}</Code>
          </p>
          <dl className="mt-3 grid grid-cols-3 gap-3 border-t border-border pt-3 text-[13px]">
            <Stat label="Puntuación" value={num(v.metrics.score)} />
            <Stat label="Geometría" value={pct(v.metrics.geometry, 0)} />
            <Stat label="Atributos" value={pct(v.metrics.attributes, 0)} />
          </dl>
        </>
      ) : (
        <p className="mt-2 text-[13px] text-muted">Sin variante medida para este tipo de documento.</p>
      )}
    </Panel>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-[15px] font-semibold text-strong tabular-nums">{value}</dd>
    </div>
  );
}

/** Diagrama de bosque: punto = puntuación, línea = IC 95 %, banda = suelo sin lectura. */
function ForestPlot({ variants }: { variants: StudyVariant[] }) {
  const ticks = [0, 0.2, 0.4, 0.6, 0.8, 1];
  const at = (v: number) => `${Math.max(0, Math.min(1, v)) * 100}%`;
  return (
    <div className="overflow-x-auto px-5 pb-5">
      <div className="min-w-[720px]">
        {variants.map((v, i) => {
          const ci = v.ci95.score;
          const muted = v.eligible === false;
          return (
            <div key={v.id} className="grid h-9 grid-cols-[180px_1fr_120px] items-center gap-4 text-[13px]">
              <span className={cn("truncate font-medium", muted ? "text-muted" : "text-text")}>{v.id}</span>
              <div className="relative h-full">
                <div className="absolute inset-y-0 left-0 bg-surface-sunken" style={{ width: at(FLOOR) }} aria-hidden />
                {ticks.map((t) => (
                  <div key={t} className="absolute inset-y-0 w-px bg-border" style={{ left: at(t) }} aria-hidden />
                ))}
                <div
                  className="estudio-row absolute inset-0"
                  style={{ animationDelay: `${i * 60}ms` }}
                  title={`${v.id}: ${num(v.metrics.score)}${ci ? ` [${num(ci[0])}; ${num(ci[1])}]` : ""}`}
                >
                  {ci ? (
                    <div
                      className={cn("absolute top-1/2 h-0.5 -translate-y-1/2 rounded-full", muted ? "bg-warning" : "bg-accent")}
                      style={{ left: at(ci[0]), width: `calc(${at(ci[1])} - ${at(ci[0])})` }}
                    >
                      <span className={cn("absolute -top-1.5 left-0 h-3.5 w-0.5", muted ? "bg-warning" : "bg-accent")} />
                      <span className={cn("absolute -top-1.5 right-0 h-3.5 w-0.5", muted ? "bg-warning" : "bg-accent")} />
                    </div>
                  ) : null}
                  <span
                    className={cn(
                      "absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 bg-surface",
                      muted ? "border-warning" : "border-accent",
                    )}
                    style={{ left: at(v.metrics.score) }}
                  />
                </div>
              </div>
              <span className="text-right tabular-nums">
                <span className="font-semibold text-strong">{num(v.metrics.score)}</span>
                {ci ? <span className="ml-1.5 text-xs text-muted">±{num((ci[1] - ci[0]) / 2)}</span> : null}
              </span>
            </div>
          );
        })}
        <div className="grid grid-cols-[180px_1fr_120px] gap-4 pt-1 text-[11px] text-muted">
          <span />
          <div className="relative h-5">
            {ticks.map((t) => (
              <span key={t} className="absolute -translate-x-1/2 tabular-nums" style={{ left: at(t) }}>
                {String(t).replace(".", ",")}
              </span>
            ))}
            <span className="absolute top-4 left-[10%] -translate-x-1/2 whitespace-nowrap text-faint">sin lectura</span>
          </div>
          <span />
        </div>
      </div>
    </div>
  );
}

function MetricsTable({ variants }: { variants: StudyVariant[] }) {
  const cols: { label: string; get: (m: StudyMetrics) => string; good?: (m: StudyMetrics) => boolean | undefined }[] = [
    { label: "Geometría", get: (m) => pct(m.geometry) },
    { label: "Atributos", get: (m) => pct(m.attributes) },
    { label: "ECE", get: (m) => num(m.ece), good: (m) => (m.ece == null ? undefined : m.ece < 0.05) },
    { label: "F1 cambios", get: (m) => pct(m.f1_delta) },
    { label: "Alucinación", get: (m) => pct(m.hallucination_rate), good: (m) => m.hallucination_rate < 0.01 },
    { label: "Cita", get: (m) => pct(m.citation_coverage), good: (m) => m.citation_coverage >= 1 },
    { label: "Intervalos", get: (m) => pct(m.interval_coverage) },
    { label: "s / rev", get: (m) => num(m.seconds_per_revision, 2) },
    { label: "€ / equipo", get: (m) => num(m.cost_eur_per_equipment, 2) },
  ];
  return (
    <div className="overflow-x-auto px-3 pb-3">
      <table className="w-full border-separate border-spacing-0 text-[13px]">
        <thead>
          <tr className="text-left text-xs text-muted">
            <th className="rounded-l-[var(--radius-control)] border-y border-l border-border bg-surface-sunken px-3 py-2.5 font-medium">
              Variante
            </th>
            {cols.map((c, i) => (
              <th
                key={c.label}
                className={cn(
                  "border-y border-border bg-surface-sunken px-3 py-2.5 text-right font-medium whitespace-nowrap",
                  i === cols.length - 1 && "rounded-r-[var(--radius-control)] border-r",
                )}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {variants.map((v) => (
            <tr key={v.id}>
              <td className="border-b border-border px-3 py-2.5">
                <p className="font-medium text-text">{v.id}</p>
                {v.description ? <p className="text-xs text-muted">{v.description}</p> : null}
              </td>
              {cols.map((c) => {
                const good = c.good?.(v.metrics);
                return (
                  <td
                    key={c.label}
                    className={cn(
                      "border-b border-border px-3 py-2.5 text-right whitespace-nowrap tabular-nums",
                      good === true && "text-approved",
                      good === false && "text-warning",
                    )}
                  >
                    {c.get(v.metrics)}
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

function Ablations({ study }: { study: StudyReport }) {
  if (!study.ablations.length) {
    return <p className="px-5 pb-5 text-[13px] text-muted">Sin ablaciones medidas todavía.</p>;
  }
  const extent = Math.max(0.05, ...study.ablations.flatMap((a) => [Math.abs(a.delta_score), ...(a.ci95 ?? []).map(Math.abs)]));
  const x = (v: number) => 50 + (v / extent) * 48; // % del ancho, 0 en el centro
  return (
    <ul className="space-y-4 px-5 pb-5">
      {study.ablations.map((a) => {
        const crosses = a.ci95 ? a.ci95[0] <= 0 && a.ci95[1] >= 0 : true;
        return (
          <li key={a.id}>
            <div className="flex items-baseline justify-between gap-3 text-[13px]">
              <span className="font-medium text-text">{a.id}</span>
              <span className="tabular-nums text-strong">
                {signed(a.delta_score)}
                {a.ci95 ? <span className="ml-1.5 text-xs text-muted">[{signed(a.ci95[0])}; {signed(a.ci95[1])}]</span> : null}
              </span>
            </div>
            <div className="relative mt-1.5 h-3 rounded-full bg-surface-sunken" aria-hidden>
              <div className="absolute top-[-3px] bottom-[-3px] left-1/2 w-px bg-border-strong" />
              {a.ci95 ? (
                <div
                  className={cn("absolute top-1/2 h-1 -translate-y-1/2 rounded-full", crosses ? "bg-muted" : "bg-revision")}
                  style={{ left: `${x(a.ci95[0])}%`, width: `${x(a.ci95[1]) - x(a.ci95[0])}%` }}
                />
              ) : null}
              <div
                className={cn("absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full", crosses ? "bg-muted" : "bg-revision")}
                style={{ left: `${x(a.delta_score)}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-muted">
              {crosses ? "El intervalo cruza el cero: no se puede afirmar que el canal aporte." : `Quitar este canal empeora ${a.of ?? "la variante"} de forma significativa.`}
            </p>
          </li>
        );
      })}
    </ul>
  );
}

function ParetoChart({ variants, front }: { variants: StudyVariant[]; front: string[] }) {
  const W = 300;
  const H = 180;
  const secs = variants.map((v) => Math.max(0.001, v.metrics.seconds_per_revision));
  const lo = Math.log10(Math.min(...secs, 0.01));
  const hi = Math.log10(Math.max(...secs, 100));
  const x = (s: number) => ((Math.log10(Math.max(0.001, s)) - lo) / (hi - lo)) * W;
  const y = (v: number) => H - v * H;
  const onFront = variants.filter((v) => front.includes(v.id)).sort((a, b) => a.metrics.seconds_per_revision - b.metrics.seconds_per_revision);
  // Etiquetas sin solaparse: se ordenan por altura y se separan al menos 13 unidades.
  const labelled = [...variants]
    .sort((a, b) => b.metrics.score - a.metrics.score)
    .reduce<{ v: StudyVariant; ly: number }[]>((acc, v) => {
      const want = y(v.metrics.score);
      const prev = acc.at(-1);
      acc.push({ v, ly: prev && want - prev.ly < 13 ? prev.ly + 13 : want });
      return acc;
    }, []);
  const decades = Array.from({ length: Math.floor(hi) - Math.ceil(lo) + 1 }, (_, i) => Math.ceil(lo) + i);
  return (
    <figure className="px-5 pb-5">
      <svg viewBox="0 0 360 228" className="h-[250px] w-full text-muted" role="img" aria-label="Frontera de Pareto">
        <g transform="translate(40 10)">
          {[0, 0.25, 0.5, 0.75, 1].map((t) => (
            <g key={t}>
              <line x1={0} x2={W} y1={y(t)} y2={y(t)} stroke="var(--border)" />
              <text x={-8} y={y(t) + 4} textAnchor="end" fontSize="10" fill="currentColor">
                {String(t).replace(".", ",")}
              </text>
            </g>
          ))}
          {decades.map((d) => (
            <text key={d} x={x(10 ** d)} y={H + 16} textAnchor="middle" fontSize="10" fill="currentColor">
              {10 ** d >= 1 ? `${10 ** d} s` : `${(10 ** d).toString().replace(".", ",")} s`}
            </text>
          ))}
          {onFront.length > 1 ? (
            <polyline
              points={onFront.map((v) => `${x(v.metrics.seconds_per_revision)},${y(v.metrics.score)}`).join(" ")}
              fill="none"
              stroke="var(--accent)"
              strokeDasharray="4 4"
            />
          ) : null}
          {labelled.map(({ v, ly }) => {
            const isFront = front.includes(v.id);
            return (
              <g key={v.id}>
                <circle
                  cx={x(v.metrics.seconds_per_revision)}
                  cy={y(v.metrics.score)}
                  r={isFront ? 6 : 4.5}
                  fill={isFront ? "var(--accent)" : "var(--surface)"}
                  stroke={isFront ? "var(--accent)" : "var(--border-strong)"}
                  strokeWidth="1.5"
                >
                  <title>{`${v.id}: ${num(v.metrics.score)} · ${num(v.metrics.seconds_per_revision, 2)} s/rev · ${num(v.metrics.cost_eur_per_equipment, 2)} €`}</title>
                </circle>
                <text x={x(v.metrics.seconds_per_revision) + 9} y={ly + 3.5} fontSize="9.5" fill="currentColor">
                  {v.id}
                </text>
              </g>
            );
          })}
          <text x={W / 2} y={H + 32} textAnchor="middle" fontSize="10.5" fill="currentColor">
            Segundos por revisión (escala logarítmica)
          </text>
        </g>
      </svg>
    </figure>
  );
}

type Axis = "by_dataset" | "by_style" | "by_degradation";
const AXES: { value: Axis; label: string }[] = [
  { value: "by_dataset", label: "Conjunto" },
  { value: "by_style", label: "Proveedor" },
  { value: "by_degradation", label: "Degradación" },
];
const GROUP_NAMES: Record<string, string> = {
  vectorial: "Vectorial",
  escaneado_limpio: "Escaneado limpio",
  escaneado_pobre: "Escaneado pobre",
};

function Breakdown({ variants }: { variants: StudyVariant[] }) {
  const [axis, setAxis] = useState<Axis>("by_style");
  const groups = Array.from(new Set(variants.flatMap((v) => Object.keys(v[axis]))));
  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        title="Dónde gana y dónde pierde cada variante"
        description="Puntuación por grupo; debajo, geometría y atributos. Los proveedores reservados nunca se usan para desarrollar."
        actions={<Segmented<Axis> label="Desglose" value={axis} onChange={setAxis} options={AXES} />}
      />
      <div className="overflow-x-auto px-3 pb-3">
        <table className="w-full border-separate border-spacing-0 text-[13px]">
          <thead>
            <tr className="text-left text-xs text-muted">
              <th className="rounded-l-[var(--radius-control)] border-y border-l border-border bg-surface-sunken px-3 py-2.5 font-medium">
                Grupo
              </th>
              {variants.map((v, i) => (
                <th
                  key={v.id}
                  className={cn(
                    "border-y border-border bg-surface-sunken px-3 py-2.5 text-right font-medium whitespace-nowrap",
                    i === variants.length - 1 && "rounded-r-[var(--radius-control)] border-r",
                  )}
                >
                  {v.id}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <tr key={g}>
                <td className="border-b border-border px-3 py-2.5 whitespace-nowrap">
                  <span className="font-medium text-text">{GROUP_NAMES[g] ?? g}</span>
                  {axis === "by_style" && RESERVED.has(g) ? (
                    <Badge tone="sky" className="ml-2">
                      reservado
                    </Badge>
                  ) : null}
                </td>
                {variants.map((v) => {
                  const m = v[axis][g];
                  return (
                    <td key={v.id} className="border-b border-border px-3 py-2 text-right">
                      {m ? <ScoreCell m={m} /> : <span className="text-faint">—</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function ScoreCell({ m }: { m: StudyMetrics }) {
  const share = Math.max(0, Math.min(1, (m.score - FLOOR) / (1 - FLOOR)));
  return (
    <div className="ml-auto w-[120px]">
      <div className="flex items-center justify-end gap-2">
        <div className="h-1.5 w-12 rounded-full bg-surface-sunken" aria-hidden>
          <div className="h-full origin-left rounded-full bg-accent" style={{ transform: `scaleX(${share})` }} />
        </div>
        <span className="font-semibold text-strong tabular-nums">{num(m.score)}</span>
      </div>
      <p className="mt-0.5 text-[11px] text-muted tabular-nums">
        geo {pct(m.geometry, 0)} · attr {pct(m.attributes, 0)}
      </p>
    </div>
  );
}

function Pairwise({ study }: { study: StudyReport }) {
  if (!study.pairwise.length) return <p className="px-5 pb-5 text-[13px] text-muted">Hace falta más de una variante.</p>;
  return (
    <div className="overflow-x-auto px-3 pb-3">
      <table className="w-full border-separate border-spacing-0 text-[13px]">
        <thead>
          <tr className="text-left text-xs text-muted">
            {["A", "B", "Solo A acierta", "Solo B acierta", "p"].map((h, i) => (
              <th
                key={h}
                className={cn(
                  "border-y border-border bg-surface-sunken px-3 py-2.5 font-medium whitespace-nowrap",
                  i === 0 && "rounded-l-[var(--radius-control)] border-l",
                  i === 4 && "rounded-r-[var(--radius-control)] border-r",
                  i >= 2 && "text-right",
                )}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {study.pairwise.map((p) => (
            <tr key={`${p.a}-${p.b}`}>
              <td className="border-b border-border px-3 py-2.5 font-medium text-text">{p.a}</td>
              <td className="border-b border-border px-3 py-2.5 text-text">{p.b}</td>
              <td className="border-b border-border px-3 py-2.5 text-right tabular-nums">{p.only_a ?? "—"}</td>
              <td className="border-b border-border px-3 py-2.5 text-right tabular-nums">{p.only_b ?? "—"}</td>
              <td className={cn("border-b border-border px-3 py-2.5 text-right tabular-nums", p.mcnemar_p < 0.05 ? "text-approved" : "text-muted")}>
                {pValue(p.mcnemar_p)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Unmeasured({ study }: { study: StudyReport }) {
  const items = study.unmeasured ?? [];
  if (!items.length) return <p className="px-5 pb-5 text-[13px] text-muted">Todo medido.</p>;
  const byReason = new Map<string, string[]>();
  for (const u of items) byReason.set(u.reason, [...(byReason.get(u.reason) ?? []), u.id]);
  return (
    <ul className="space-y-3 px-5 pb-5">
      {[...byReason.entries()].map(([reason, ids]) => (
        <li key={reason}>
          <p className="text-[13px] text-text first-letter:uppercase">{reason}</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {ids.map((id) => (
              <Badge key={id} tone="neutral">
                {id}
              </Badge>
            ))}
          </div>
        </li>
      ))}
    </ul>
  );
}

function Reproduce({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-start gap-4 rounded-[var(--radius-card)] border border-border p-4", className)}>
      <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-full bg-sky-soft text-sky">
        <Terminal size={16} strokeWidth={1.5} aria-hidden />
      </span>
      <div className="min-w-0">
        <p className="font-medium text-strong">Reproducir el estudio</p>
        <Code className="mt-1.5 block text-text">uv run python -m synthetic --conjunto todos</Code>
        <Code className="mt-1 block text-text">uv run python -m bench.estudio</Code>
      </div>
      <FlaskConical className="ml-auto hidden shrink-0 text-faint sm:block" size={18} strokeWidth={1.5} aria-hidden />
    </div>
  );
}
