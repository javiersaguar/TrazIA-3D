"use client";

import { Search } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";

import { EASE_OUT } from "@/components/motion/reveal";
import { Badge, Icon, Panel } from "@/components/ui/primitives";
import { FamilyThumb } from "@/features/bocetos/thumb";
import { cn } from "@/lib/cn";
import { familyInfo, industrialFamily, useCatalogue } from "./catalogue";
import { DocumentActions } from "./document-actions";
import { projectFamilies } from "./projects-tab";

const TONE = { Disponible: "approved", "En desarrollo": "warning", Planificada: "neutral" } as const;

function normalizeName(name: string) {
  return name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim().toLowerCase();
}

export function FamiliesTab({ selected, onOpen }: { selected: string; onOpen: (family: string, view: "documentos" | "proyectos") => void }) {
  const catalogue = useCatalogue();
  const [query, setQuery] = useState("");
  const name = normalizeName(query);
  const families = catalogue.families.filter((family) => normalizeName(family.name).includes(name));

  return (
    <div className="space-y-3">
      <label className="relative flex h-9 w-full items-center sm:max-w-[320px]">
        <span className="sr-only">Buscar familias</span>
        <Icon icon={Search} className="pointer-events-none absolute left-3 text-faint" />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Buscar por nombre"
          className="h-full w-full rounded-[var(--radius-control)] border border-border bg-surface pr-3 pl-9 text-[13px] text-text outline-none placeholder:text-faint focus-visible:border-accent"
        />
      </label>
      <p className="text-[13px] text-muted">
        Despliega una familia para consultar sus diseños, abrir los planos y ver los modelos 3D disponibles.
      </p>
      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-3">
        {families.map((f, i) => {
          const info = familyInfo(f.id);
          const industrial = industrialFamily(f.id);
          const designs = catalogue.designs.filter((d) => d.family === f.id);
          const documents = designs.length;
          const projects = catalogue.projects.filter((p) => projectFamilies(p, catalogue.designs).includes(f.id)).length;
          return (
            <motion.li
              key={f.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: i * 0.04, ease: EASE_OUT }}
            >
              <Panel className={cn("p-4", selected === f.id && "border-accent")}>
                <div className="flex gap-4">
                  <FamilyThumb kind={f.id} size={104} />
                  <div className="flex min-w-0 flex-1 flex-col">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-[15px] font-semibold text-strong">{f.name}</h3>
                      <Badge tone={info ? TONE[info.status] : "neutral"}>{industrial ? "Conceptual 3D" : info?.status ?? "Propia"}</Badge>
                    </div>
                    <p className="mt-0.5 text-[12px] text-muted">
                      {info && info.phase !== "—" ? <span className="font-mono text-faint">{info.phase} </span> : null}
                      {industrial ? "Planos e IFC sintéticos" : info?.fields != null ? `${info.fields} campos de revisión` : "Campos por definir"}
                    </p>
                    <ul className="mt-3 flex flex-wrap gap-1.5">
                      {(industrial?.parts ?? info?.parts ?? ["Piezas por definir"]).map((part) => (
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
                </div>
                <details className="mt-4 border-t border-border pt-3">
                  <summary className="cursor-pointer rounded text-sm font-medium text-accent-text">
                    {documents === 1 ? "Ver 1 diseño" : `Ver ${documents} diseños`}
                  </summary>
                  {documents > 0 ? (
                    <ul aria-label={`Diseños de ${f.name}`} className="mt-3 divide-y divide-border rounded-lg border border-border">
                      {designs.map((design) => (
                        <li key={design.id} className="grid min-w-0 gap-1 px-3 py-2">
                          <p className="break-words text-sm font-medium text-strong">{design.name}</p>
                          <p className="flex flex-wrap gap-x-2 text-[11px] text-muted">
                            {design.tag && <span className="font-mono">{design.tag}</span>}
                            {design.rev && <span>Rev. {design.rev}</span>}
                            {design.kind === "Boceto GA" && <span>Boceto sintético</span>}
                          </p>
                          <DocumentActions design={design} />
                        </li>
                      ))}
                    </ul>
                  ) : <p className="mt-2 text-sm text-muted">Todavía no hay diseños en esta familia.</p>}
                </details>
              </Panel>
            </motion.li>
          );
        })}
      </ul>
      {families.length === 0 && (
        <p role="status" className="py-10 text-center text-[13px] text-muted">
          Ninguna familia coincide con la búsqueda.
        </p>
      )}
    </div>
  );
}
