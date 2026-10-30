"use client";

import { Clock, Timer } from "lucide-react";
import { motion } from "motion/react";
import { useId, useState, type ReactNode } from "react";
import { CountUp } from "@/components/motion/count-up";
import { Badge, Panel, PanelHeader } from "@/components/ui/primitives";
import { formatNumber, formatPercent } from "@/lib/format";

/* Cifras del reto (PDF, pág. 5): 300–500 equipos, 3–5 revisiones, 2–4 h por revisión. */
export function RoiCalculator() {
  const [equipment, setEquipment] = useState(400);
  const [revisions, setRevisions] = useState(4);
  const [hours, setHours] = useState(3);
  const [reviewMinutes, setReviewMinutes] = useState<string>("");

  const manual = equipment * revisions * hours;
  const minutes = Number(reviewMinutes.replace(",", "."));
  const measured = reviewMinutes.trim() !== "" && Number.isFinite(minutes) && minutes >= 0;
  const assisted = measured ? (equipment * revisions * minutes) / 60 : null;
  const saved = assisted != null ? manual - assisted : null;
  const max = manual;

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
      <Panel>
        <PanelHeader title="Supuestos" description="Rangos tomados del enunciado del reto. Muévelos para ver tu proyecto." />
        <div className="space-y-5 px-5 pb-5">
          <Range label="Equipos por proyecto" min={300} max={500} step={10} value={equipment} onChange={setEquipment} />
          <Range label="Revisiones de GA por equipo" min={3} max={5} step={1} value={revisions} onChange={setRevisions} />
          <Range label="Horas de modelado manual por revisión" min={2} max={4} step={0.5} value={hours} onChange={setHours} suffix="h" />

          <div className="border-t border-border pt-5">
            <label className="flex items-center justify-between text-[13px] text-text">
              Minutos de revisión asistida por revisión
              <Badge tone="warning">por medir</Badge>
            </label>
            <div className="mt-2 flex h-9 items-center rounded-[var(--radius-control)] border border-border bg-surface transition-[border-color,box-shadow] duration-[var(--dur-fast)] focus-within:border-accent focus-within:shadow-[0_0_0_3px_var(--accent-soft)]">
              <input
                value={reviewMinutes}
                onChange={(e) => setReviewMinutes(e.target.value)}
                inputMode="decimal"
                placeholder="Se mide en el hackatón con el registro de revisión"
                aria-label="Minutos de revisión asistida por revisión"
                className="h-full min-w-0 flex-1 bg-transparent px-3 text-[13px] text-text outline-none placeholder:text-faint"
              />
              <span className="pr-3 text-xs text-muted">min</span>
            </div>
            <p className="mt-2 text-xs text-faint">
              No lo inventamos: el tiempo real sale del registro de acciones de la pantalla Revisión con ingenieros reales.
            </p>
          </div>
        </div>
      </Panel>

      <Panel>
        <PanelHeader
          title="Horas de modelado transcriptivo por proyecto"
          description={`${formatNumber(equipment)} equipos × ${revisions} revisiones × tiempo por revisión`}
        />
        <div className="space-y-6 px-5 pb-6">
          <Bar icon={Clock} label="Modelado manual" value={manual} max={max} tone="bg-border-strong" />
          <Bar icon={Timer} label="Revisión asistida con TrazIA-3D" value={assisted} max={max} tone="bg-approved" />

          <div aria-live="polite" className="grid grid-cols-1 gap-4 border-t border-border pt-5 sm:grid-cols-3">
            <Stat label="Horas manuales" value={<CountUp value={manual} suffix=" h" duration={0.5} />} />
            <Stat
              label="Horas ahorradas"
              value={saved != null ? <CountUp value={Math.round(saved)} suffix=" h" duration={0.5} /> : "Sin medir"}
              muted={saved == null}
            />
            <Stat label="Reducción" value={saved != null ? formatPercent(saved / manual) : "Sin medir"} muted={saved == null} />
          </div>
          <p className="text-xs text-faint">
            El reto estima entre 1.800 y 10.000 h de trabajo transcriptivo por proyecto. Además del ahorro de horas cuentan los
            errores que dejan de llegar tarde a interferencias o a campo.
          </p>
        </div>
      </Panel>
    </div>
  );
}

function Range({
  label,
  min,
  max,
  step,
  value,
  onChange,
  suffix,
}: {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (v: number) => void;
  suffix?: string;
}) {
  const id = useId();
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <label htmlFor={id} className="text-[13px] text-text">
          {label}
        </label>
        <span className="text-[15px] font-semibold text-strong">
          {formatNumber(value)}
          {suffix ? ` ${suffix}` : ""}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 w-full accent-[var(--accent-strong)]"
      />
      <div className="flex justify-between text-[11px] text-faint">
        <span>{formatNumber(min)}</span>
        <span>{formatNumber(max)}</span>
      </div>
    </div>
  );
}

function Bar({ icon: I, label, value, max, tone }: { icon: typeof Clock; label: string; value: number | null; max: number; tone: string }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-[13px]">
        <span className="flex items-center gap-2 text-text">
          <I size={15} strokeWidth={1.5} aria-hidden className="text-muted" />
          {label}
        </span>
        <span className="font-semibold text-strong tabular-nums">{value != null ? <CountUp value={Math.round(value)} suffix=" h" duration={0.5} /> : "Sin medir"}</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-surface-sunken">
        {/* Crece al montarse y sigue a los deslizadores con un muelle suave */}
        <motion.div
          className={`h-full origin-left rounded-full ${tone}`}
          initial={{ scaleX: 0 }}
          animate={{ scaleX: value != null ? Math.min(1, value / max) : 0 }}
          transition={{ type: "spring", duration: 0.5, bounce: 0.12 }}
        />
      </div>
    </div>
  );
}

function Stat({ label, value, muted }: { label: string; value: ReactNode; muted?: boolean }) {
  return (
    <div>
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-0.5 text-[22px] font-semibold tabular-nums ${muted ? "text-faint" : "text-strong"}`}>{value}</p>
    </div>
  );
}
