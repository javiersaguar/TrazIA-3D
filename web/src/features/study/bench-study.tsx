"use client";

import Link from "next/link";
import { useState } from "react";
import { FlaskConical } from "lucide-react";
import { SyntheticNotice } from "@/components/ui/notice";
import { Badge, Button, Code, EmptyState, Panel, PanelHeader, Skeleton } from "@/components/ui/primitives";
import { isStudyEmpty, type StudyReport } from "@/lib/mock/estudio-types";
import { useStudy } from "@/lib/queries";
import { studyScope } from "./scope";

const num = (value: number | null | undefined, digits = 3) => value == null ? "Sin medir" : value.toFixed(digits).replace(".", ",");
const pct = (value: number | null) => value == null ? "Sin medir" : `${num(value * 100, 1)} %`;

export function BenchStudy() {
  const query = useStudy();
  if (query.isPending) return <Skeleton className="h-80 w-full" />;
  if (query.isError) return <Panel className="p-5"><p role="alert" className="text-warning">No se pudo cargar el estudio: {query.error.message}</p>
    <Button className="mt-3" onClick={() => void query.refetch()}>Reintentar</Button></Panel>;
  if (!query.data || isStudyEmpty(query.data) || !query.data.variants.length) return <Panel>
    <EmptyState icon={FlaskConical} title="Aún no hay resultados del estudio">Publica un informe medido para comparar la rúbrica. El bench de referencia sigue disponible en la pestaña superior.</EmptyState>
    <p className="px-5 pb-5 text-xs text-muted"><Code>uv run python -m bench.estudio</Code></p>
  </Panel>;
  return <MeasuredBench study={query.data} />;
}

function MeasuredBench({ study }: { study: StudyReport }) {
  const [selected, setSelected] = useState(study.variants[0]!.id);
  const variant = study.variants.find(v => v.id === selected) ?? study.variants[0]!;
  const m = variant.metrics;
  const scope = studyScope(study);
  const interval = variant.ci95.score;
  const eligible = variant.eligible ?? (m.hallucination_rate < 0.01 && m.citation_coverage >= 1);
  const criteria = [
    ["35 %", "Fidelidad geométrica", pct(m.geometry), "Campos correctos y penalización por IoU. Sin IFC, geometría cero."],
    ["25 %", "Extracción de atributos", `${pct(m.attributes)} · ECE ${num(m.ece)}`, "Valor y unidad, ajustados por calibración en la puntuación."],
    ["20 %", "Actualización incremental", `F1 ${pct(m.f1_delta)}`, "Cambios entre las dos revisiones del mismo equipo."],
    ["10 %", "Arquitectura y escalado", `${num(m.seconds_per_revision, 2)} s/rev · ${num(m.cost_eur_per_equipment, 4)} €/equipo`, "Coste y tiempo del estudio. El lote con workers se mide por separado."],
    ["10 %", "Innovación técnica", "Convención fija del estudio", "Contribución 0,10 común a todas las variantes. No es una medición."],
  ];
  return <div className="space-y-5" data-testid="study-bench">
    {study.synthetic === true ? <SyntheticNotice>Informe medido en {scope.datasets.join(" + ") || study.datasets.join(" + ")}. No se mezcla con el bench v1.</SyntheticNotice> :
      <Panel className="p-4 text-sm text-muted">Informe local. Comprueba el origen y el alcance de sus datos antes de interpretar las cifras.</Panel>}
    <Panel className="p-5">
      <div className="flex flex-wrap items-end justify-between gap-5">
        <div><label htmlFor="bench-variant" className="mb-2 block text-xs text-muted">Variante medida</label>
          <select id="bench-variant" className="max-w-full rounded-lg border border-border bg-surface-sunken px-3 py-2 text-sm text-text" value={variant.id} onChange={event => setSelected(event.target.value)}>
            {study.variants.map(v => <option key={v.id} value={v.id}>{v.id}</option>)}
          </select><p className="mt-2 text-xs text-muted">{variant.description}</p></div>
        <div><p className="text-xs text-muted">Puntuación GA2MODEL</p><p className="mt-1 text-3xl font-semibold tabular-nums text-strong">{num(m.score)}</p>
          <p className="mt-1 text-xs text-muted">{interval ? `IC 95 % [${num(interval[0])}; ${num(interval[1])}]` : "Intervalo sin medir"}</p></div>
        <Badge tone={eligible ? "approved" : "warning"}>{eligible ? "Cumple restricciones" : "No cumple restricciones"}</Badge>
      </div>
      <p className="mt-4 border-t border-border pt-3 text-xs text-muted">{scope.equipment || "Sin recuento de"} equipos · {scope.vendors} estilos medidos · {scope.degradations} degradaciones · semilla {study.seed}</p>
      <p className="mt-1 text-xs text-faint">Generado {new Date(study.generated_at).toLocaleString("es-ES")} · misma fuente que Estudio</p>
    </Panel>
    <Panel className="overflow-hidden"><PanelHeader title="Rúbrica del estudio" description="Cada cifra corresponde a la variante seleccionada. Los pesos son los del reto." />
      <div className="overflow-x-auto"><table className="w-full text-left text-[13px]"><thead className="bg-surface-sunken text-xs text-muted"><tr>{["Peso", "Criterio", "Resultado medido", "Interpretación"].map(h => <th key={h} className="px-5 py-3 font-medium">{h}</th>)}</tr></thead>
        <tbody>{criteria.map(([weight, name, value, note]) => <tr key={name} className="border-t border-border"><td className="whitespace-nowrap px-5 py-4 text-accent-text">{weight}</td><th scope="row" className="px-5 py-4 font-medium text-strong">{name}</th><td className="px-5 py-4 tabular-nums">{value}</td><td className="min-w-64 px-5 py-4 text-muted">{note}</td></tr>)}</tbody>
      </table></div>
    </Panel>
    <Panel className="p-5"><p className="text-sm text-text">Citas: {pct(m.citation_coverage)} · Valores sin respaldo: {pct(m.hallucination_rate)}</p>
      <p className="mt-2 text-xs text-muted">La elegibilidad exige cita del 100 % y valores sin respaldo por debajo del 1 %. Una variante elegible puede seguir teniendo baja cobertura geométrica.</p>
      <Link href="/estudio" className="mt-4 inline-block text-sm font-medium text-accent-text underline underline-offset-4">Ver variantes, ablaciones y frontera de Pareto</Link>
    </Panel>
  </div>;
}
