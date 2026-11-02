"use client";

import { Search } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useState } from "react";

import { EASE_OUT } from "@/components/motion/reveal";
import { Segmented } from "@/components/ui/controls";
import { Badge, Icon, Panel } from "@/components/ui/primitives";
import { FamilyThumb } from "@/features/bocetos/thumb";
import { cn } from "@/lib/cn";
import { PROJECT_KINDS, useCatalogue, type Design, type Project, type ProjectStats } from "./catalogue";

type Filter = "todos" | "revision" | "aprobados";
const STATUS_TONE = { "En revisión": "warning", Aprobado: "approved", "Sin empezar": "neutral" } as const;

/** Familias de un proyecto: las de sus documentos y, en los ejemplos, las que declara. */
export function projectFamilies(project: Project, designs: Design[]): string[] {
  const own = designs.filter((d) => d.project === project.id).map((d) => d.family);
  return [...new Set([...own, ...(PROJECT_KINDS[project.id] ?? [])])];
}

function statsOf(project: Project, designs: Design[]): ProjectStats {
  if (project.stats) return project.stats;
  const mine = designs.filter((d) => d.project === project.id);
  const reviewed = mine.filter((d) => d.stage === "revisado").length;
  const equipment = new Set(mine.map((d) => d.tag ?? d.name)).size;
  return {
    equipment,
    withData: mine.length,
    reviewed,
    status: !mine.length ? "Sin empezar" : reviewed === mine.length ? "Aprobado" : "En revisión",
    updated: mine[0]?.received ?? "—",
  };
}

function ProjectCard({ p, kinds, stats, documents, onOpen }: { p: Project; kinds: string[]; stats: ProjectStats; documents: number; onOpen: () => void }) {
  const progress = stats.withData ? stats.reviewed / stats.withData : 0;
  const demo = p.id === "demo";
  const body = (
    <Panel className="lift h-full overflow-hidden">
      <div className="drafting-grid flex h-36 items-center justify-center gap-2 border-b border-border">
        {kinds.length ? kinds.slice(0, 3).map((k) => <FamilyThumb key={k} kind={k} size={88} />) : <p className="text-[12px] text-faint">Sin documentos todavía</p>}
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[15px] font-semibold text-strong">{p.name}</p>
            <p className="font-mono text-[11px] text-faint">{p.code ?? "Proyecto propio"}</p>
          </div>
          <Badge tone={STATUS_TONE[stats.status]}>{stats.status}</Badge>
        </div>
        <div className="mt-4">
          <div className="flex justify-between text-[12px] text-muted">
            <span>Equipos revisados</span>
            <span className="tabular-nums">
              {stats.reviewed} de {stats.withData}
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
        <dl className="mt-4 grid grid-cols-4 gap-2 text-[12px]">
          <div>
            <dt className="text-faint">Equipos</dt>
            <dd className="text-text tabular-nums">{stats.equipment}</dd>
          </div>
          <div>
            <dt className="text-faint">Con datos</dt>
            <dd className="text-text tabular-nums">{stats.withData}</dd>
          </div>
          <div>
            <dt className="text-faint">Documentos</dt>
            <dd className="text-text tabular-nums">{documents}</dd>
          </div>
          <div>
            <dt className="text-faint">Actualizado</dt>
            <dd className="text-text tabular-nums">{stats.updated}</dd>
          </div>
        </dl>
        <p className={cn("mt-3 text-[12px]", demo ? "text-accent-text" : "text-faint")}>
          {demo ? "Abrir el proyecto de la demo" : p.example ? "Proyecto de ejemplo · ver sus documentos" : "Ver sus documentos"}
        </p>
      </div>
    </Panel>
  );
  return demo ? (
    <Link href="/proyecto" className="block h-full rounded-[var(--radius-panel)]">
      {body}
    </Link>
  ) : (
    <button type="button" onClick={onOpen} className="block h-full w-full rounded-[var(--radius-panel)] text-left">
      {body}
    </button>
  );
}

export function ProjectsTab({ family, onOpenProject }: { family: string; onOpenProject: (id: string) => void }) {
  const catalogue = useCatalogue();
  const [filter, setFilter] = useState<Filter>("todos");
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const familyName = catalogue.families.find((f) => f.id === family)?.name;
  const list = catalogue.projects
    .map((p) => ({ p, kinds: projectFamilies(p, catalogue.designs), stats: statsOf(p, catalogue.designs) }))
    .filter(
      ({ p, kinds, stats }) =>
        (family === "all" || kinds.includes(family)) &&
        (filter === "todos" || (filter === "revision" ? stats.status === "En revisión" : stats.status === "Aprobado")) &&
        (!q || p.name.toLowerCase().includes(q) || (p.code ?? "").toLowerCase().includes(q)),
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
        {familyName ? <p className="text-[13px] text-muted">Proyectos con {familyName.toLowerCase()}</p> : null}
      </div>

      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-3">
        <AnimatePresence mode="popLayout" initial={false}>
          {list.map(({ p, kinds, stats }, i) => (
            <motion.li
              key={p.id}
              layout
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0, transition: { duration: 0.4, delay: i * 0.04, ease: EASE_OUT } }}
              exit={{ opacity: 0, scale: 0.98, transition: { duration: 0.15 } }}
            >
              <ProjectCard
                p={p}
                kinds={kinds}
                stats={stats}
                documents={catalogue.designs.filter((d) => d.project === p.id).length}
                onOpen={() => onOpenProject(p.id)}
              />
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>
      {list.length === 0 ? (
        <p className="py-10 text-center text-[13px] text-muted">
          {familyName ? `Ningún proyecto tiene ${familyName.toLowerCase()} todavía. Añade un documento de esta familia a un proyecto.` : "Ningún proyecto coincide con la búsqueda."}
        </p>
      ) : null}
    </div>
  );
}
