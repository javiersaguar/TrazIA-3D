"use client";

import { Plus } from "lucide-react";
import { motion } from "motion/react";
import { useState, type ReactNode } from "react";

import { CountUp } from "@/components/motion/count-up";
import { EASE_OUT } from "@/components/motion/reveal";
import { Tip } from "@/components/ui/controls";
import { Badge, Button, Icon, Panel, PanelHeader } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { JOBS, type SketchJob } from "@/lib/mock/bocetos";

const TONE = { "En cola": "neutral", Procesando: "sky", Hecho: "approved", Cancelado: "danger" } as const;

function Stat({ label, value, children }: { label: string; value?: number; children?: ReactNode }) {
  return (
    <Panel className="px-5 py-4">
      <p className="text-[13px] text-muted">{label}</p>
      <p className="mt-0.5 text-[24px] font-semibold text-strong tabular-nums">{children ?? <CountUp value={value ?? 0} />}</p>
    </Panel>
  );
}

export function BatchSketch() {
  const [jobs, setJobs] = useState<SketchJob[]>(JOBS);
  const count = (s: SketchJob["status"]) => jobs.filter((j) => j.status === s).length;
  const cancel = (id: string) => setJobs((js) => js.map((j) => (j.id === id ? { ...j, status: "Cancelado" } : j)));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="En cola" value={count("En cola")} />
        <Stat label="Procesando" value={count("Procesando")} />
        <Stat label="Hechos" value={count("Hecho")} />
        <Stat label="Coste">
          0 € <span className="text-[13px] font-normal text-muted">todo en local</span>
        </Stat>
      </div>

      <Panel>
        <PanelHeader
          title="Cola de trabajos"
          description="Cada lote lee sus documentos con la estrategia elegida. Se puede cancelar mientras no haya terminado."
          actions={
            <Tip content="Boceto: aún no se pueden lanzar lotes">
              <span>
                <Button variant="primary" size="sm" disabled>
                  <Icon icon={Plus} size={14} /> Nuevo lote
                </Button>
              </span>
            </Tip>
          }
        />
        <ul className="divide-y divide-border border-t border-border">
          {jobs.map((j) => {
            const open = j.status === "En cola" || j.status === "Procesando";
            return (
              <li key={j.id} className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-2 px-5 py-3.5 md:grid-cols-[140px_110px_1fr_120px_100px]">
                <span className="font-mono text-[12.5px] text-text">{j.id}</span>
                <span className="text-[13px] text-muted md:order-none">
                  {j.documents} docs · <span className="font-mono">{j.strategy}</span>
                </span>
                <div className="col-span-2 flex items-center gap-3 md:col-span-1">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-sunken">
                    <motion.div
                      className={cn("h-full origin-left rounded-full", j.status === "Cancelado" ? "bg-border-strong" : j.status === "Hecho" ? "bg-approved" : "bg-accent")}
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: j.progress }}
                      transition={{ duration: 0.7, ease: EASE_OUT }}
                    />
                  </div>
                  <span className="w-10 text-right text-[12px] text-muted tabular-nums">{Math.round(j.progress * 100)} %</span>
                </div>
                <Badge tone={TONE[j.status]}>{j.status}</Badge>
                <span className="text-right">
                  {open ? (
                    <Button size="sm" variant="ghost" onClick={() => cancel(j.id)}>
                      Cancelar
                    </Button>
                  ) : (
                    <span className="text-[12px] text-faint tabular-nums">{j.started}</span>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      </Panel>
    </div>
  );
}
