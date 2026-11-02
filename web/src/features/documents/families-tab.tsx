"use client";

import { motion } from "motion/react";

import { EASE_OUT } from "@/components/motion/reveal";
import { Badge, Panel } from "@/components/ui/primitives";
import { FamilyThumb } from "@/features/bocetos/thumb";
import { cn } from "@/lib/cn";
import { familyInfo, useCatalogue } from "./catalogue";
import { projectFamilies } from "./projects-tab";

const TONE = { Disponible: "approved", "En desarrollo": "warning", Planificada: "neutral" } as const;

export function FamiliesTab({ selected, onOpen }: { selected: string; onOpen: (family: string, view: "documentos" | "proyectos") => void }) {
  const catalogue = useCatalogue();
  return (
    <div className="space-y-3">
      <p className="text-[13px] text-muted">
        Las miniaturas son ilustrativas, no proceden del IFC. Hoy el recipiente vertical es la familia con plantilla geométrica completa; las
        familias nuevas sirven para clasificar documentos y su plantilla se revisa por separado.
      </p>
      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-3">
        {catalogue.families.map((f, i) => {
          const info = familyInfo(f.id);
          const documents = catalogue.designs.filter((d) => d.family === f.id).length;
          const projects = catalogue.projects.filter((p) => projectFamilies(p, catalogue.designs).includes(f.id)).length;
          return (
            <motion.li
              key={f.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: i * 0.04, ease: EASE_OUT }}
            >
              <Panel className={cn("flex h-full gap-4 p-4", selected === f.id && "border-accent")}>
                <FamilyThumb kind={f.id} size={104} />
                <div className="flex min-w-0 flex-1 flex-col">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-[15px] font-semibold text-strong">{f.name}</h3>
                    <Badge tone={info ? TONE[info.status] : "neutral"}>{info?.status ?? "Propia"}</Badge>
                  </div>
                  <p className="mt-0.5 text-[12px] text-muted">
                    {info && info.phase !== "—" ? <span className="font-mono text-faint">{info.phase} </span> : null}
                    {info?.fields != null ? `${info.fields} campos de revisión` : "Campos por definir"}
                  </p>
                  <ul className="mt-3 flex flex-wrap gap-1.5">
                    {(info?.parts ?? ["Piezas por definir"]).map((part) => (
                      <li key={part} className="rounded-[6px] border border-border bg-surface-sunken px-2 py-0.5 text-[12px] text-muted">
                        {part}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-auto flex flex-wrap gap-x-4 gap-y-1 pt-3 text-[12px]">
                    <button type="button" className="text-accent-text underline-offset-2 hover:underline" onClick={() => onOpen(f.id, "documentos")}>
                      {documents === 1 ? "1 documento" : `${documents} documentos`}
                    </button>
                    <button type="button" className="text-accent-text underline-offset-2 hover:underline" onClick={() => onOpen(f.id, "proyectos")}>
                      {projects === 1 ? "1 proyecto" : `${projects} proyectos`}
                    </button>
                  </div>
                </div>
              </Panel>
            </motion.li>
          );
        })}
      </ul>
    </div>
  );
}
