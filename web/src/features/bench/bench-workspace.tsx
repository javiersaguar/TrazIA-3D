"use client";

import { BenchStudy } from "@/features/study/bench-study";
import { Database, Terminal } from "lucide-react";
import Image from "next/image";
import { useState } from "react";
import { Segmented } from "@/components/ui/controls";
import { SyntheticNotice } from "@/components/ui/notice";
import { Badge, Code, Panel, PanelHeader, Skeleton } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { formatNumber, formatPercent } from "@/lib/format";
import type { BenchExtractor } from "@/lib/mock/api";
import type { BenchReport, BenchStyle, BenchStyleId, ReliabilityPoint } from "@/lib/mock/bench-types";
import { useBench } from "@/lib/queries";

const STYLES: { id: BenchStyleId; name: string; description: string }[] = [
  { id: "rotulado", name: "Rotulado", description: "Parámetros escritos como «ETIQUETA = valor»." },
  { id: "plano", name: "Plano dibujado", description: "Alzado con cotas, planta, tabla de boquillas y cajetín." },
  { id: "escaneado", name: "Escaneado", description: "El mismo plano como imagen, sin capa de texto." },
];

type Criterion = {
  weight: number;
  name: string;
  jury: string;
  metric: string;
  target: string;
  value: (s: BenchStyle) => string;
  meets?: (s: BenchStyle) => boolean;
};

const pct = (x: number | null) => (x == null ? "—" : formatPercent(x));
const num = (x: number | null, digits = 2) => (x == null ? "—" : x.toFixed(digits).replace(".", ","));

/* Rúbrica del reto (PDF, pág. 14) con la métrica principal de cada criterio. */
const CRITERIA: Criterion[] = [
  {
    weight: 35,
    name: "Fidelidad geométrica",
    jury: "Dimensiones principales y boquillas frente al IFC de referencia",
    metric: "Campos geométricos correctos (dimensiones y boquillas)",
    target: "Por fijar con el mentor",
    value: (s) => pct(s.geometry.field_accuracy),
  },
  {
    weight: 25,
    name: "Extracción de atributos",
    jury: "Acierto de valor + unidad y calibración de la confianza",
    metric: "Valor + unidad correctos · ECE",
    target: "ECE < 0,05",
    value: (s) => `${pct(s.attributes.accuracy_value_unit)} · ECE ${num(s.attributes.ece)}`,
    meets: (s) => s.attributes.ece != null && s.attributes.ece < 0.05,
  },
  {
    weight: 20,
    name: "Actualización incremental",
    jury: "Detección precisa de los cambios rev1 → rev2",
    metric: "F1 de cambios por campo",
    target: "F1 ≥ 0,95 en sintéticos",
    value: (s) => pct(s.delta.f1),
    meets: (s) => s.delta.f1 != null && s.delta.f1 >= 0.95,
  },
  {
    weight: 10,
    name: "Arquitectura y escalado",
    jury: "Viabilidad para cientos de equipos y revisiones",
    metric: "Segundos por revisión con modelo",
    target: "< 60 s y < 0,50 € por equipo",
    value: (s) => (s.scale.seconds_per_revision == null ? "—" : `${num(s.scale.seconds_per_revision)} s`),
    meets: (s) => s.scale.seconds_per_revision != null && s.scale.seconds_per_revision < 60,
  },
  {
    weight: 10,
    name: "Innovación técnica",
    jury: "Decisiones sólidas y valor no previsto",
    metric: "Se defiende en la demo",
    target: "—",
    value: () => "—",
  },
];

export function BenchWorkspace() {
  const [source, setSource] = useState<"study" | "legacy">("study");
  return <div className="space-y-5">
    <Segmented label="Fuente de resultados" value={source} onChange={setSource}
      options={[{ value: "study", label: "Estudio actual" }, { value: "legacy", label: "Bench de referencia v1" }]} />
    {source === "study" ? <BenchStudy /> : <LegacyBenchWorkspace />}
  </div>;
}

function LegacyBenchWorkspace() {
  const [extractor, setExtractor] = useState<BenchExtractor>("combinado");
  const [style, setStyle] = useState<BenchStyleId>("plano");
  const { data: report, isPending } = useBench(extractor);

  return (
    <div className="space-y-5">
      <SyntheticNotice>
        {report
          ? `Bench sobre ${report.styles.rotulado.equipment} equipos generados (semilla ${report.seed}) en tres estilos de plano. No es precisión sobre planos de TR.`
          : "Bench sobre equipos generados con verdad conocida. No es precisión sobre planos de TR."}
      </SyntheticNotice>

      <div className="flex flex-wrap items-center gap-3">
        <Segmented<BenchExtractor>
          label="Extractor"
          value={extractor}
          onChange={setExtractor}
          options={[
            { value: "etiquetas", label: "Etiquetas", title: "Extractor del núcleo: líneas ETIQUETA = valor" },
            { value: "combinado", label: "Etiquetas + planos", title: "Añade el lector de tablas, cotas y cajetín" },
          ]}
        />
        <p className="text-xs text-muted">
          {report ? `Generado ${new Date(report.generated_at).toLocaleString("es-ES")} · ` : null}
          Mismos documentos, distinto extractor: así se mide cada mejora.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {STYLES.map((s) => (
          <StyleCard
            key={s.id}
            meta={s}
            data={report?.styles[s.id]}
            selected={style === s.id}
            onSelect={() => setStyle(s.id)}
          />
        ))}
      </div>

      <Panel className="overflow-hidden">
        <PanelHeader
          title="Rúbrica del jurado"
          description="Pesos del reto y la métrica principal con la que medimos cada criterio, por estilo de plano."
        />
        <RubricTable report={report} loading={isPending} />
      </Panel>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel>
          <PanelHeader
            title="Calibración de la confianza"
            description="Si un 0,8 acierta el 80 % de las veces, los puntos caen sobre la diagonal."
            actions={
              report ? <Badge tone="neutral">ECE {num(report.styles[style].attributes.ece)}</Badge> : null
            }
          />
          <div className="px-5 pb-5">
            {report ? (
              <ReliabilityChart points={report.styles[style].attributes.reliability} />
            ) : (
              <Skeleton className="h-[270px] w-full" />
            )}
            <p className="mt-2 text-xs text-muted">
              {STYLES.find((s) => s.id === style)?.name} · el tamaño del punto es el número de valores del tramo.
            </p>
          </div>
        </Panel>
        <Panel>
          <PanelHeader
            title={`Detalle geométrico · ${STYLES.find((s) => s.id === style)?.name}`}
            description="Errores frente a la verdad y frente al IFC de referencia construido con ella."
          />
          {report ? <GeometryDetail data={report.styles[style]} /> : <Skeleton className="mx-5 mb-5 h-56" />}
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Panel className="flex items-start gap-4 p-5">
          <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-sky-soft text-sky">
            <Terminal size={18} strokeWidth={1.5} aria-hidden />
          </span>
          <div className="min-w-0">
            <p className="font-medium text-strong">Reproducir estas cifras</p>
            <p className="mt-0.5 text-[13px] text-muted">Desde la raíz del repositorio:</p>
            <Code className="mt-2 block text-text">uv run python -m synthetic --casos 20 --semilla 2026</Code>
            <Code className="mt-1 block text-text">uv run python -m bench --extractor combinado</Code>
          </div>
        </Panel>
        <Panel className="flex items-start gap-4 p-5">
          <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-violet-soft text-violet">
            <Database size={18} strokeWidth={1.5} aria-hidden />
          </span>
          <div>
            <p className="font-medium text-strong">Dataset de Técnicas Reunidas</p>
            <p className="mt-0.5 text-[13px] text-muted">
              Con los 4 IFC de referencia del reto se medirá con las mismas métricas. Disponible en el hackatón; nunca
              se sube al repositorio.
            </p>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function StyleCard({
  meta,
  data,
  selected,
  onSelect,
}: {
  meta: (typeof STYLES)[number];
  data: BenchStyle | undefined;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "overflow-hidden rounded-[var(--radius-panel)] border bg-surface text-left shadow-[var(--shadow-1)]",
        "transition-[border-color,box-shadow] duration-[var(--dur-fast)] ease-[var(--ease-out)]",
        selected ? "border-accent shadow-[0_0_0_3px_var(--accent-soft)]" : "border-border hover:border-border-strong",
      )}
    >
      {/* Fondo de retícula mientras carga la miniatura (marcador de posición) */}
      <div className="drafting-grid relative aspect-[1.414/1] border-b border-border">
        <Image
          src={`/demo/bench/${meta.id}.webp`}
          alt={`Plano sintético en estilo ${meta.name.toLowerCase()}`}
          fill
          sizes="(min-width: 1024px) 33vw, 100vw"
          className="object-contain p-2"
        />
      </div>
      <div className="p-4">
        <div className="flex items-center justify-between gap-2">
          <p className="font-semibold text-strong">{meta.name}</p>
          {data ? (
            <Badge tone={data.models_built === data.revisions ? "live" : data.models_built ? "warning" : "neutral"}>
              {data.models_built} / {data.revisions} modelos
            </Badge>
          ) : null}
        </div>
        <p className="mt-0.5 text-[13px] text-muted">{meta.description}</p>
        <dl className="mt-3 grid grid-cols-3 gap-3 border-t border-border pt-3 text-[13px]">
          <Stat label="Geometría" value={data ? pct(data.geometry.field_accuracy) : "…"} />
          <Stat label="Atributos" value={data ? pct(data.attributes.accuracy_value_unit) : "…"} />
          <Stat label="F1 cambios" value={data ? pct(data.delta.f1) : "…"} />
        </dl>
      </div>
    </button>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-[15px] font-semibold text-strong">{value}</dd>
    </div>
  );
}

function RubricTable({ report, loading }: { report: BenchReport | undefined; loading: boolean }) {
  const heads = ["Peso", "Criterio", "Qué mide Técnicas Reunidas", "Métrica", "Objetivo", ...STYLES.map((s) => s.name)];
  return (
    <div className="overflow-x-auto px-3 pb-3">
      <table className="w-full border-separate border-spacing-0 text-[13px]">
        <thead>
          <tr className="text-left text-xs text-muted">
            {heads.map((h, i) => (
              <th
                key={h}
                className={cn(
                  "border-y border-border bg-surface-sunken px-3 py-2.5 font-medium",
                  i === 0 && "rounded-l-[var(--radius-control)] border-l",
                  i === heads.length - 1 && "rounded-r-[var(--radius-control)] border-r",
                  i >= 5 && "text-right",
                )}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {CRITERIA.map((c) => (
            <tr key={c.name} className="align-top">
              <td className="border-b border-border px-3 py-3">
                <div className="w-14">
                  <p className="text-[15px] font-semibold text-strong">{c.weight} %</p>
                  <div className="mt-1.5 h-1 rounded-full bg-surface-sunken">
                    <div className="h-full origin-left rounded-full bg-accent" style={{ transform: `scaleX(${c.weight / 35})` }} />
                  </div>
                </div>
              </td>
              <td className="border-b border-border px-3 py-3 font-medium text-text">{c.name}</td>
              <td className="border-b border-border px-3 py-3 text-muted">{c.jury}</td>
              <td className="border-b border-border px-3 py-3 text-muted">{c.metric}</td>
              <td className="border-b border-border px-3 py-3 whitespace-nowrap text-text">{c.target}</td>
              {STYLES.map((s) => {
                const data = report?.styles[s.id];
                const ok = data && c.meets?.(data);
                return (
                  <td key={s.id} className="border-b border-border px-3 py-3 text-right whitespace-nowrap">
                    {loading || !data ? (
                      <Skeleton className="ml-auto h-4 w-14" />
                    ) : (
                      <span className={cn("font-medium", ok ? "text-approved" : "text-text")}>{c.value(data)}</span>
                    )}
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

function GeometryDetail({ data }: { data: BenchStyle }) {
  const g = data.geometry;
  const rows: [string, string][] = [
    ["Campos geométricos encontrados", pct(g.field_coverage)],
    ["Error medio en dimensiones", g.dimension_mae_mm == null ? "—" : `${num(g.dimension_mae_mm)} mm`],
    ["Boquillas detectadas (recall · precisión)", `${pct(g.nozzle_recall)} · ${pct(g.nozzle_precision)}`],
    ["Error de posición de boquilla", g.nozzle_position_mae_mm == null ? "—" : `${num(g.nozzle_position_mae_mm)} mm`],
    ["Error de orientación", g.nozzle_orientation_mae_deg == null ? "—" : `${num(g.nozzle_orientation_mae_deg)}°`],
    ["DN correcto", pct(g.nozzle_dn_accuracy)],
    ["Elementos IFC presentes", pct(g.ifc_element_recall)],
    ["IoU medio de cajas IFC", num(g.ifc_mean_iou)],
    ["Error de centro IFC", g.ifc_center_error_mm == null ? "—" : `${num(g.ifc_center_error_mm)} mm`],
    ["Revisiones por hora (1 proceso)", data.scale.revisions_per_hour == null ? "—" : formatNumber(Math.round(data.scale.revisions_per_hour))],
  ];
  return (
    <dl className="divide-y divide-border px-5 pb-4 text-[13px]">
      {rows.map(([label, value]) => (
        <div key={label} className="flex items-center justify-between gap-4 py-2">
          <dt className="text-muted">{label}</dt>
          <dd className="font-medium text-text">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Diagrama de fiabilidad: diagonal ideal y un punto por tramo de confianza (área ∝ nº de valores). */
function ReliabilityChart({ points }: { points: ReliabilityPoint[] }) {
  const W = 260;
  const H = 200;
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  const max = Math.max(1, ...points.map((p) => p.n));
  const x = (v: number) => v * W;
  const y = (v: number) => H - v * H;
  return (
    <figure className="relative">
      <svg viewBox="0 0 320 252" className="h-[270px] w-full text-muted" role="img" aria-label="Diagrama de fiabilidad">
        <g transform="translate(40 12)">
          {ticks.map((t) => (
            <g key={t}>
              <line x1={0} x2={W} y1={y(t)} y2={y(t)} stroke="var(--border)" />
              <text x={-8} y={y(t) + 4} textAnchor="end" fontSize="10" fill="currentColor">
                {String(t).replace(".", ",")}
              </text>
              <text x={x(t)} y={H + 16} textAnchor="middle" fontSize="10" fill="currentColor">
                {String(t).replace(".", ",")}
              </text>
            </g>
          ))}
          <line x1={0} y1={H} x2={W} y2={0} stroke="var(--accent)" strokeDasharray="4 4" strokeWidth="1.2" />
          {points.map((p) => (
            <g key={p.bin[0]}>
              <line x1={x(p.confidence)} x2={x(p.confidence)} y1={y(p.confidence)} y2={y(p.accuracy)} stroke="var(--revision)" strokeWidth="1.2" />
              <circle
                cx={x(p.confidence)}
                cy={y(p.accuracy)}
                r={4 + 8 * Math.sqrt(p.n / max)}
                fill="var(--revision)"
                fillOpacity="0.25"
                stroke="var(--revision)"
                strokeWidth="1.4"
              >
                <title>{`Confianza ${p.confidence.toFixed(2)} · acierto ${(p.accuracy * 100).toFixed(0)} % · ${p.n} valores`}</title>
              </circle>
            </g>
          ))}
          <text x={W / 2} y={H + 32} textAnchor="middle" fontSize="10.5" fill="currentColor">
            Confianza declarada
          </text>
        </g>
        <text x={10} y={112} fontSize="10.5" fill="currentColor" transform="rotate(-90 10 112)" textAnchor="middle">
          Acierto real
        </text>
      </svg>
      {points.length === 0 ? (
        <figcaption className="absolute top-[34%] left-1/2 -translate-x-1/2 rounded-[var(--radius-control)] border border-border bg-surface px-3 py-1.5 text-[13px] whitespace-nowrap text-muted">
          Sin valores extraídos en este estilo
        </figcaption>
      ) : null}
    </figure>
  );
}
