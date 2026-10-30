import type { LucideIcon } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/cn";

/* Superficie de tarjeta: borde de 1 px, sin sombras grandes (referencias I.2b). */
export function Panel({ className, ...props }: ComponentProps<"section">) {
  return (
    <section
      className={cn(
        "surface-sheen rounded-[var(--radius-panel)] border border-border bg-surface shadow-[var(--shadow-1)]",
        className,
      )}
      {...props}
    />
  );
}

export function PanelHeader({
  title,
  description,
  actions,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("flex items-start justify-between gap-4 px-5 pt-4 pb-3", className)}>
      <div className="min-w-0">
        <h2 className="text-[15px] font-semibold text-strong">{title}</h2>
        {description ? <p className="mt-0.5 text-[13px] text-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </header>
  );
}

/** Icono lucide con el trazo fino común a toda la app. */
export function Icon({ icon: I, className, size = 16 }: { icon: LucideIcon; className?: string; size?: number }) {
  return <I aria-hidden size={size} strokeWidth={1.5} className={cn("shrink-0", className)} />;
}

/** Icono dentro de un círculo o baldosa tintada, como en los KPI de PIDS. */
export function IconTile({
  icon,
  tone = "accent",
  shape = "circle",
  size = "md",
}: {
  icon: LucideIcon;
  tone?: Tone;
  shape?: "circle" | "tile";
  size?: "sm" | "md";
}) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center",
        shape === "circle" ? "rounded-full" : "rounded-[var(--radius-control)]",
        size === "md" ? "size-10" : "size-8",
        TONE_SOFT[tone],
      )}
    >
      <Icon icon={icon} size={size === "md" ? 18 : 16} />
    </span>
  );
}

export type Tone = "accent" | "live" | "sky" | "revision" | "approved" | "danger" | "warning" | "neutral";

const TONE_SOFT: Record<Tone, string> = {
  accent: "bg-accent-soft text-accent-text",
  live: "bg-live-soft text-live",
  sky: "bg-sky-soft text-sky",
  revision: "bg-revision-soft text-revision",
  approved: "bg-approved-soft text-approved",
  danger: "bg-danger-soft text-danger",
  warning: "bg-warning-bg text-warning",
  neutral: "bg-surface-sunken text-muted",
};

/** Insignia de estado ("Al día", "Con errores", "DRAFT"…). */
export function Badge({ tone = "neutral", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex h-[22px] items-center gap-1 rounded-[var(--radius-chip)] px-2 text-xs font-medium whitespace-nowrap",
        TONE_SOFT[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Píldora de la barra superior. */
export function Pill({
  children,
  tone = "neutral",
  className,
  ...props
}: ComponentProps<"span"> & { tone?: "neutral" | "warning" | "live" }) {
  return (
    <span
      className={cn(
        "inline-flex h-7 items-center gap-1.5 rounded-full border px-2.5 text-xs whitespace-nowrap",
        tone === "warning" && "border-warning-border bg-warning-bg text-warning",
        tone === "live" && "border-border bg-surface text-text",
        tone === "neutral" && "border-border bg-surface text-muted",
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}

export function LiveDot({ className }: { className?: string }) {
  return (
    <span className={cn("relative inline-flex size-2", className)} aria-hidden>
      <span className="absolute inset-0 rounded-full bg-live-dot opacity-60 motion-safe:animate-ping" />
      <span className="relative inline-flex size-2 rounded-full bg-live-dot" />
    </span>
  );
}

export function Kbd({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <kbd
      className={cn(
        "inline-flex h-5 min-w-5 items-center justify-center rounded-[5px] border border-border bg-surface-sunken px-1 font-mono text-[11px] text-muted",
        className,
      )}
    >
      {children}
    </kbd>
  );
}

/** Código corto en mono: id de etapa, GUID, hash. Nunca para datos generales. */
export function Code({ children, className }: { children: ReactNode; className?: string }) {
  return <code className={cn("font-mono text-[12px] text-faint", className)}>{children}</code>;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton", className)} aria-hidden />;
}

export function EmptyState({
  icon,
  title,
  children,
  action,
  className,
}: {
  icon: LucideIcon;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center px-6 py-10 text-center", className)}>
      <span className="mb-3 text-accent-text">
        <Icon icon={icon} size={22} />
      </span>
      <p className="font-medium text-strong">{title}</p>
      {children ? <div className="mt-1 max-w-[46ch] text-[13px] text-muted">{children}</div> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function Button({
  variant = "secondary",
  size = "md",
  className,
  ...props
}: ComponentProps<"button"> & { variant?: "primary" | "secondary" | "ghost" | "danger"; size?: "sm" | "md" }) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-[var(--radius-control)] font-medium whitespace-nowrap",
        "transition-[background-color,color,border-color,transform] duration-[var(--dur-fast)] ease-[var(--ease-out)]",
        "active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50",
        size === "md" ? "h-9 px-3.5 text-[13px]" : "h-7 px-2.5 text-xs",
        variant === "primary" && "bg-accent font-semibold text-accent-contrast hover:bg-accent/90",
        variant === "secondary" && "border border-border bg-surface text-text hover:bg-surface-sunken",
        variant === "ghost" && "text-muted hover:bg-surface-sunken hover:text-text",
        variant === "danger" && "bg-danger-soft text-danger hover:bg-danger-soft/80",
        className,
      )}
      {...props}
    />
  );
}
