"use client";

import { motion } from "motion/react";

import { EASE_OUT } from "@/components/motion/reveal";
import { Badge, Panel } from "@/components/ui/primitives";
import { FAMILIES } from "@/lib/mock/bocetos";
import { FamilyThumb } from "./thumb";

const TONE = { Disponible: "approved", "En desarrollo": "warning", Planificada: "neutral" } as const;

export function FamiliesSketch() {
  return (
    <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {FAMILIES.map((f, i) => (
        <motion.li
          key={f.name}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: i * 0.05, ease: EASE_OUT }}
        >
          <Panel className="flex h-full gap-4 p-4">
            <FamilyThumb kind={f.kind} size={104} />
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <p className="text-[15px] font-semibold text-strong">{f.name}</p>
                <Badge tone={TONE[f.status]}>{f.status}</Badge>
              </div>
              <p className="mt-0.5 text-[12px] text-muted">
                {f.phase !== "—" ? <span className="font-mono text-faint">{f.phase} </span> : null}
                {f.fields != null ? `${f.fields} campos de revisión` : "Campos por definir"}
              </p>
              <ul className="mt-3 flex flex-wrap gap-1.5">
                {f.parts.map((part) => (
                  <li key={part} className="rounded-[6px] border border-border bg-surface-sunken px-2 py-0.5 text-[12px] text-muted">
                    {part}
                  </li>
                ))}
              </ul>
            </div>
          </Panel>
        </motion.li>
      ))}
    </ul>
  );
}
