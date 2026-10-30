"use client";

import * as ToggleGroup from "@radix-ui/react-toggle-group";
import * as RTooltip from "@radix-ui/react-tooltip";
import { motion } from "motion/react";
import { useId, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Kbd } from "./primitives";

/** Control segmentado (6 h / 12 h / 24 h en PIDS; rev A / rev B / Δ aquí). */
export function Segmented<T extends string>({
  value,
  onChange,
  options,
  label,
  className,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: ReactNode; title?: string }[];
  label: string;
  className?: string;
}) {
  // El indicador se desliza entre opciones (layoutId propio de cada control)
  const indicator = `seg${useId()}`;
  return (
    <ToggleGroup.Root
      type="single"
      value={value}
      onValueChange={(v) => v && onChange(v as T)}
      aria-label={label}
      className={cn("inline-flex h-8 items-center gap-0.5 rounded-[var(--radius-control)] bg-surface-sunken p-0.5", className)}
    >
      {options.map((o) => (
        <ToggleGroup.Item
          key={o.value}
          value={o.value}
          title={o.title}
          className={cn(
            "relative h-7 rounded-[6px] px-2.5 text-[13px] text-muted",
            "transition-colors duration-[var(--dur-fast)] ease-[var(--ease-out)]",
            "hover:text-text data-[state=on]:font-medium data-[state=on]:text-strong",
          )}
        >
          {o.value === value ? (
            <motion.span
              layoutId={indicator}
              className="absolute inset-0 rounded-[6px] border border-border bg-surface shadow-[var(--shadow-1)]"
              transition={{ type: "spring", duration: 0.28, bounce: 0.1 }}
            />
          ) : null}
          <span className="relative">{o.label}</span>
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
}

/** Tooltip con pista de atajo de teclado opcional. */
export function Tip({
  content,
  shortcut,
  side = "top",
  children,
}: {
  content: ReactNode;
  shortcut?: string[];
  side?: "top" | "right" | "bottom" | "left";
  children: ReactNode;
}) {
  return (
    <RTooltip.Root>
      <RTooltip.Trigger asChild>{children}</RTooltip.Trigger>
      <RTooltip.Portal>
        <RTooltip.Content
          side={side}
          sideOffset={6}
          className={cn(
            "z-50 flex items-center gap-2 rounded-[var(--radius-control)] border border-border bg-surface-raised px-2.5 py-1.5 text-xs text-text shadow-[var(--shadow-pop)]",
            "origin-[var(--radix-tooltip-content-transform-origin)] data-[state=delayed-open]:animate-[tip-in_var(--dur-fast)_var(--ease-out)]",
          )}
        >
          <span>{content}</span>
          {shortcut ? (
            <span className="flex gap-0.5">
              {shortcut.map((k) => (
                <Kbd key={k}>{k}</Kbd>
              ))}
            </span>
          ) : null}
        </RTooltip.Content>
      </RTooltip.Portal>
    </RTooltip.Root>
  );
}
