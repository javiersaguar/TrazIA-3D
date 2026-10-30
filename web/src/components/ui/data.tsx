"use client";

import type { LucideIcon } from "lucide-react";
import { motion } from "motion/react";
import { useId, type ReactNode } from "react";
import { CountUp } from "@/components/motion/count-up";
import { cn } from "@/lib/cn";
import { IconTile, Panel, Skeleton, type Tone } from "./primitives";

const EASE_OUT = [0.23, 1, 0.32, 1] as const;

/**
 * Micrográfica de área, como en las tarjetas de PIDS. Solo con series reales.
 * Al montarse, la línea se dibuja, el área aparece detrás y el último punto se marca.
 */
export function Sparkline({ points, className }: { points: number[]; className?: string }) {
  const uid = `sp${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  if (points.length < 2) return null;
  const w = 96;
  const h = 40;
  const max = Math.max(...points);
  const min = Math.min(...points);
  const span = max - min || 1;
  const xy = points.map((p, i) => [(i / (points.length - 1)) * w, h - 4 - ((p - min) / span) * (h - 8)] as const);
  const line = xy.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L${w},${h} L0,${h} Z`;
  const [ex, ey] = xy[xy.length - 1]!;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={cn("h-10 w-24 overflow-visible text-accent", className)} aria-hidden>
      <defs>
        <linearGradient id={uid} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="currentColor" stopOpacity="0.28" />
          <stop offset="1" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <motion.path d={area} fill={`url(#${uid})`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.45 }} />
      <motion.path
        d={line}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.7, ease: [0.65, 0, 0.35, 1] }}
      />
      <motion.circle
        cx={ex}
        cy={ey}
        r={2.4}
        fill="currentColor"
        initial={{ opacity: 0, scale: 0.6 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.25, delay: 0.7, ease: EASE_OUT }}
      />
    </svg>
  );
}

/** Anillo de salud 0–100 % (tarjetas de etapa de Albertitos). `null` = sin datos. */
export function HealthRing({ value, size = 76 }: { value: number | null; size?: number }) {
  const stroke = 7;
  const r = (size - stroke) / 2;
  // Arco de 270°, abierto abajo
  const arc = (Math.PI * 2 * r * 270) / 360;
  const pct = value == null ? 0 : Math.max(0, Math.min(1, value));
  const tone = value == null ? "text-faint" : pct >= 0.95 ? "text-live" : pct >= 0.7 ? "text-warning" : "text-danger";
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} className="-rotate-[225deg]" aria-hidden>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${arc} ${Math.PI * 2 * r}`}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="currentColor"
          className={tone}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${arc} ${Math.PI * 2 * r}`}
          initial={{ strokeDashoffset: arc }}
          animate={{ strokeDashoffset: arc * (1 - pct) }}
          transition={{ type: "spring", stiffness: 140, damping: 22 }}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center pt-1 text-[15px] font-semibold text-strong tabular-nums">
        {value == null ? "—" : <CountUp value={Math.round(pct * 100)} suffix=" %" duration={0.8} />}
      </span>
    </div>
  );
}

/** Barra de confianza con su valor; el color indica el tramo (alta ≥ 0,9 · media · baja < 0,6). */
export function ConfidenceBar({ value, className }: { value: number; className?: string }) {
  const tone = value >= 0.9 ? "bg-live-dot" : value >= 0.6 ? "bg-warning" : "bg-danger";
  return (
    <div className={cn("flex items-center gap-2", className)} title={`Confianza ${value.toFixed(2)} · sin calibrar`}>
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-sunken">
        <motion.div
          className={cn("h-full rounded-full", tone)}
          initial={{ width: "0%" }}
          animate={{ width: `${Math.round(value * 100)}%` }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
        />
      </div>
      <span className="w-8 text-xs text-muted">{value.toFixed(2).replace(".", ",")}</span>
    </div>
  );
}

/** Tarjeta KPI: icono en círculo tintado, etiqueta, valor, contexto y micrográfica opcional. */
export function KpiCard({
  icon,
  tone = "accent",
  label,
  value,
  context,
  spark,
  loading,
}: {
  icon: LucideIcon;
  tone?: Tone;
  label: string;
  value: ReactNode;
  context?: ReactNode;
  spark?: number[];
  loading?: boolean;
}) {
  return (
    <Panel className="flex min-h-[108px] items-center gap-4 px-5 py-4">
      <IconTile icon={icon} tone={tone} />
      <div className="min-w-0 flex-1">
        <p className="text-[13px] text-muted">{label}</p>
        {loading ? (
          <Skeleton className="mt-2 h-7 w-24" />
        ) : (
          <p className="mt-0.5 text-[26px] leading-tight font-semibold tracking-tight text-strong tabular-nums">
            {typeof value === "number" ? <CountUp value={value} /> : value}
          </p>
        )}
        {context ? <div className="mt-1 text-xs text-muted">{context}</div> : null}
      </div>
      {spark && !loading ? <Sparkline points={spark} /> : null}
    </Panel>
  );
}
