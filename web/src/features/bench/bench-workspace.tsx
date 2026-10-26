"use client";

import { Database, FlaskConical, Grid3x3 } from "lucide-react";
import { Badge, EmptyState, Panel, PanelHeader } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";

/* Rúbrica del reto (PDF, pág. 14) y métricas del roadmap (sección G). Sin resultados todavía. */
const CRITERIA = [
  {
    weight: 35,
    name: "Fidelidad geométrica",
    jury: "Dimensiones principales y boquillas frente al IFC de referencia",
    metric: "Error en mm por dimensión · posición 3D y orientación de cada boquilla · IoU y Hausdorff de la malla",
    target: "Por fijar con el mentor",
  },
  {
    weight: 25,
    name: "Extracción de atributos",
    jury: "Acierto de valor + unidad y calibración de la confianza",
    metric: "Exactitud valor+unidad · cobertura · abstención · ECE y diagrama de fiabilidad",
    target: "ECE < 0,05",
  },
  {
    weight: 20,
    name: "Actualización incremental",
    jury: "Detección precisa de los cambios rev1 → rev2",
    metric: "Precisión, recall y F1 de cambios · error en la magnitud · falsos cambios por ruido",
    target: "F1 ≥ 0,95 en sintéticos",
  },
  {
    weight: 10,
    name: "Arquitectura y escalado",
    jury: "Viabilidad para cientos de equipos y revisiones",
    metric: "Segundos y euros por equipo · equipos por hora en lote · aciertos de caché",
    target: "< 60 s y < 0,50 € por equipo",
  },
  {
    weight: 10,
    name: "Innovación técnica",
    jury: "Decisiones sólidas y valor no previsto",
    metric: "Se defiende en la demo: comprobación de citas, cola por riesgo, aprobación dentro del IFC",
    target: "—",
  },
];

export function BenchWorkspace() {
  return (
    <div className="space-y-5">
      <Panel className="overflow-hidden">
        <PanelHeader
          title="Rúbrica del jurado"
          description="Los pesos son los del reto. Cada fila dice qué mediremos nosotros con el mismo criterio."
          actions={<Badge tone="neutral">Sin medir todavía</Badge>}
        />
        <div className="overflow-x-auto px-3 pb-3">
          <table className="w-full border-separate border-spacing-0 text-[13px]">
            <thead>
              <tr className="text-left text-xs text-muted">
                {["Peso", "Criterio", "Qué mide Técnicas Reunidas", "Cómo lo medimos", "Objetivo", "Resultado"].map((h, i, all) => (
                  <th
                    key={h}
                    className={cn(
                      "border-y border-border bg-surface-sunken px-3 py-2.5 font-medium",
                      i === 0 && "rounded-l-[var(--radius-control)] border-l",
                      i === all.length - 1 && "rounded-r-[var(--radius-control)] border-r",
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
                    <div className="w-16">
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
                  <td className="border-b border-border px-3 py-3 whitespace-nowrap text-faint">Sin medir</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel>
          <PanelHeader title="Calibración de la confianza" description="Si un 0,8 acierta el 80 % de las veces, los puntos caen sobre la diagonal." />
          <div className="px-5 pb-5">
            <ReliabilityFrame />
          </div>
        </Panel>
        <Panel>
          <PanelHeader title="Error geométrico en 3D" description="Distancia de nuestra malla a la del IFC de referencia, en color sobre el modelo." />
          <EmptyState icon={Grid3x3} title="Sin IFC de referencia todavía" className="min-h-[300px]">
            Técnicas Reunidas entrega 4 IFC de referencia con el dataset. El mapa de calor aparece cuando el bench los compare
            con nuestros modelos.
          </EmptyState>
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Panel className="flex items-start gap-4 p-5">
          <span className="inline-flex size-10 items-center justify-center rounded-full bg-sky-soft text-sky">
            <FlaskConical size={18} strokeWidth={1.5} aria-hidden />
          </span>
          <div>
            <p className="font-medium text-strong">Conjunto sintético</p>
            <p className="mt-0.5 text-[13px] text-muted">Recipientes generados con su verdad conocida, limpios y escaneados. Pendiente del generador (tarea 1.4).</p>
          </div>
        </Panel>
        <Panel className="flex items-start gap-4 p-5">
          <span className="inline-flex size-10 items-center justify-center rounded-full bg-violet-soft text-violet">
            <Database size={18} strokeWidth={1.5} aria-hidden />
          </span>
          <div>
            <p className="font-medium text-strong">Dataset de Técnicas Reunidas</p>
            <p className="mt-0.5 text-[13px] text-muted">GA rev1 y rev2, hojas de datos, VESOR e IFC de referencia. Disponible en el hackatón; nunca se sube al repositorio.</p>
          </div>
        </Panel>
      </div>
    </div>
  );
}

/** Marco del diagrama de fiabilidad: ejes y diagonal ideal, sin puntos inventados. */
function ReliabilityFrame() {
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  return (
    <figure className="relative">
      <svg viewBox="0 0 320 252" className="h-[270px] w-full text-muted" role="img" aria-label="Diagrama de fiabilidad vacío">
        <g transform="translate(40 12)">
          {ticks.map((t) => (
            <g key={t}>
              <line x1={0} x2={260} y1={200 - t * 200} y2={200 - t * 200} stroke="var(--border)" />
              <text x={-8} y={204 - t * 200} textAnchor="end" fontSize="10" fill="currentColor">
                {t.toString().replace(".", ",")}
              </text>
              <text x={t * 260} y={216} textAnchor="middle" fontSize="10" fill="currentColor">
                {t.toString().replace(".", ",")}
              </text>
            </g>
          ))}
          <line x1={0} y1={200} x2={260} y2={0} stroke="var(--accent)" strokeDasharray="4 4" strokeWidth="1.2" />
          <text x={130} y={232} textAnchor="middle" fontSize="10.5" fill="currentColor">
            Confianza declarada
          </text>
        </g>
        <text x={10} y={112} fontSize="10.5" fill="currentColor" transform="rotate(-90 10 112)" textAnchor="middle">
          Acierto real
        </text>
      </svg>
      <figcaption className="absolute top-[34%] left-1/2 -translate-x-1/2 rounded-[var(--radius-control)] border border-border bg-surface px-3 py-1.5 text-[13px] whitespace-nowrap text-muted">
        Sin datos de calibración todavía
      </figcaption>
    </figure>
  );
}
