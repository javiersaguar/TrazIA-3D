"use client";

import { BadgeCheck, BookOpenText, PenLine, ShieldAlert, type LucideIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { EASE_OUT } from "@/components/motion/reveal";
import { Segmented } from "@/components/ui/controls";
import { Icon, Panel } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { AUDIT, type AuditEvent } from "@/lib/mock/bocetos";

type Filter = "todo" | AuditEvent["kind"];

const KIND: Record<AuditEvent["kind"], { icon: LucideIcon; ring: string; label: string }> = {
  edición: { icon: PenLine, ring: "border-accent text-accent-text", label: "Edición" },
  aprobación: { icon: BadgeCheck, ring: "border-approved text-approved", label: "Aprobación" },
  invalidación: { icon: ShieldAlert, ring: "border-revision text-revision", label: "Invalidación" },
  lectura: { icon: BookOpenText, ring: "border-border-strong text-muted", label: "Lectura" },
};

export function AuditSketch() {
  const [filter, setFilter] = useState<Filter>("todo");
  const list = AUDIT.filter((e) => filter === "todo" || e.kind === filter);

  return (
    <Panel className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-[60ch] text-[13px] text-muted">
          Cualquier cambio en los datos invalida la aprobación anterior. Aquí queda quién hizo qué, cuándo y sobre qué evidencia.
        </p>
        {/* En móvil las cuatro opciones no caben: el filtro se desplaza en horizontal */}
        <div className="max-w-full overflow-x-auto">
          <Segmented<Filter>
            label="Filtrar eventos"
            value={filter}
            onChange={setFilter}
            options={[
              { value: "todo", label: "Todo" },
              { value: "edición", label: "Ediciones" },
              { value: "aprobación", label: "Aprobaciones" },
              { value: "invalidación", label: "Invalidaciones" },
            ]}
          />
        </div>
      </div>

      <ol className="relative mt-6">
        <span aria-hidden className="absolute top-2 bottom-2 left-[15px] w-px bg-border" />
        <AnimatePresence mode="popLayout" initial={false}>
          {list.map((e, i) => {
            const k = KIND[e.kind];
            return (
              <motion.li
                key={e.at + e.text}
                layout
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0, transition: { duration: 0.35, delay: i * 0.04, ease: EASE_OUT } }}
                exit={{ opacity: 0, transition: { duration: 0.12 } }}
                className="relative flex gap-4 pb-6 last:pb-0"
              >
                <span className={cn("relative z-[1] flex size-8 shrink-0 items-center justify-center rounded-full border bg-surface", k.ring)}>
                  <Icon icon={k.icon} size={15} />
                </span>
                <div className="min-w-0 pt-1">
                  <p className="text-[14px] text-strong">{e.text}</p>
                  {e.detail ? <p className="mt-0.5 text-[13px] text-muted">{e.detail}</p> : null}
                  <p className="mt-1 text-[12px] text-faint tabular-nums">
                    {k.label}, {e.who}, {e.at}
                  </p>
                </div>
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ol>
    </Panel>
  );
}
