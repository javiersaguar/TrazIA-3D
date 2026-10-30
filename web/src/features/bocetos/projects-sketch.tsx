"use client";

import { Plus, Search } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useState } from "react";

import { EASE_OUT } from "@/components/motion/reveal";
import { Segmented, Tip } from "@/components/ui/controls";
import { Badge, Button, Icon, Panel } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { PROJECTS, type SketchProject } from "@/lib/mock/bocetos";
import { FamilyThumb } from "./thumb";

type Filter = "todos" | "revision" | "aprobados";

const STATUS_TONE = { "En revisión": "warning", Aprobado: "approved", "Sin empezar": "neutral" } as const;

function ProjectCard({ p }: { p: SketchProject }) {
  const progress = p.withData ? p.reviewed / p.withData : 0;
  const body = (
    <Panel className={cn("h-full overflow-hidden", !p.example && "lift")}>
      <div className="drafting-grid flex h-36 items-center justify-center gap-2 border-b border-border">
        {p.kinds.slice(0, 3).map((k) => (
          <FamilyThumb key={k} kind={k} size={88} />
        ))}
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[15px] font-semibold text-strong">{p.name}</p>
            <p className="font-mono text-[11px] text-faint">{p.code}</p>
          </div>
          <Badge tone={STATUS_TONE[p.status]}>{p.status}</Badge>
        </div>
        <div className="mt-4">
          <div className="flex justify-between text-[12px] text-muted">
            <span>Equipos revisados</span>
            <span className="tabular-nums">
              {p.reviewed} de {p.withData}
            </span>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-sunken">
            <motion.div
              className="h-full origin-left rounded-full bg-accent"
              initial={{ scaleX: 0 }}
              animate={{ scaleX: progress }}
              transition={{ duration: 0.7, delay: 0.15, ease: EASE_OUT }}
            />
          </div>
        </div>
        <dl className="mt-4 grid grid-cols-3 gap-2 text-[12px]">
          <div>
            <dt className="text-faint">Equipos</dt>
            <dd className="text-text tabular-nums">{p.equipment}</dd>
          </div>
          <div>
            <dt className="text-faint">Con datos</dt>
            <dd className="text-text tabular-nums">{p.withData}</dd>
          </div>
          <div>
            <dt className="text-faint">Actualizado</dt>
            <dd className="text-text tabular-nums">{p.updated}</dd>
          </div>
        </dl>
        {p.example ? <p className="mt-3 text-[12px] text-faint">Proyecto de ejemplo</p> : <p className="mt-3 text-[12px] text-accent-text">Abrir el proyecto de la demo</p>}
      </div>
    </Panel>
  );
  return p.example ? body : (
    <Link href="/proyecto" className="block h-full rounded-[var(--radius-panel)]">
      {body}
    </Link>
  );
}

export function ProjectsSketch() {
  const [filter, setFilter] = useState<Filter>("todos");
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const list = PROJECTS.filter(
    (p) =>
      (filter === "todos" || (filter === "revision" ? p.status === "En revisión" : p.status === "Aprobado")) &&
      (!q || p.name.toLowerCase().includes(q) || p.code.toLowerCase().includes(q)),
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <label className="relative flex h-9 min-w-[220px] flex-1 items-center sm:max-w-[320px]">
          <span className="sr-only">Buscar proyectos</span>
          <Icon icon={Search} className="pointer-events-none absolute left-3 text-faint" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar por nombre o código"
            className="h-full w-full rounded-[var(--radius-control)] border border-border bg-surface pr-3 pl-9 text-[13px] text-text outline-none placeholder:text-faint focus-visible:border-accent"
          />
        </label>
        <Segmented<Filter>
          label="Filtrar proyectos"
          value={filter}
          onChange={setFilter}
          options={[
            { value: "todos", label: "Todos" },
            { value: "revision", label: "En revisión" },
            { value: "aprobados", label: "Aprobados" },
          ]}
        />
        <Tip content="Boceto: aún no se pueden crear proyectos">
          <span className="ml-auto">
            <Button variant="primary" disabled>
              <Icon icon={Plus} size={15} /> Nuevo proyecto
            </Button>
          </span>
        </Tip>
      </div>

      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        <AnimatePresence mode="popLayout" initial={false}>
          {list.map((p, i) => (
            <motion.li
              key={p.code}
              layout
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0, transition: { duration: 0.4, delay: i * 0.04, ease: EASE_OUT } }}
              exit={{ opacity: 0, scale: 0.98, transition: { duration: 0.15 } }}
            >
              <ProjectCard p={p} />
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>
      {list.length === 0 ? <p className="py-10 text-center text-[13px] text-muted">Ningún proyecto coincide con la búsqueda.</p> : null}
    </div>
  );
}
