import { ArrowUpRight, Layers3, Route } from "lucide-react";
import Link from "next/link";
import { Badge, Icon, Panel } from "@/components/ui/primitives";
import { processAsset, processProjects } from "./catalog";

export function ProcessProjectCards({ query = "", family = "all" }: { query?: string; family?: string }) {
  const matches = processProjects.filter(project =>
    (family === "all" || project.equipment.some(item => item.family === family))
    && `${project.name} ${project.setting} ${project.code}`.toLocaleLowerCase().includes(query));
  if (!matches.length) return null;

  return (
    <section className="space-y-3" aria-label="Proyectos 3D de petróleo y gas">
      <div>
        <h2 className="text-base font-semibold text-strong">Proyectos 3D de petróleo y gas</h2>
        <p className="mt-0.5 text-sm text-muted">Complejos sintéticos con equipos conectados, revisiones y planos por pieza.</p>
      </div>
      <ul className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-4">
        {matches.map(project => (
          <li key={project.id}>
            <Link href={`/proyectos-proceso/${project.id}`} className="group block h-full rounded-[var(--radius-panel)]">
              <Panel className="lift flex h-full flex-col overflow-hidden">
                {/* La miniatura usa el mismo IFC. El visor se carga al abrir el proyecto. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={processAsset(project, "preview.webp")} alt="" loading="lazy" width={720} height={380}
                  className="aspect-[1.9] w-full border-b border-border object-cover" />
                <div className="flex flex-1 flex-col gap-2 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <Badge tone="neutral">{project.setting}</Badge>
                    <Icon icon={ArrowUpRight} size={17} className="text-accent-text" />
                  </div>
                  <h3 className="font-semibold text-strong">{project.name}</h3>
                  <p className="text-sm text-muted">{project.description}</p>
                  <div className="mt-auto flex flex-wrap gap-4 pt-2 text-xs text-muted">
                    <span className="inline-flex items-center gap-1"><Icon icon={Layers3} size={14} /> {project.equipment.length} equipos</span>
                    <span className="inline-flex items-center gap-1"><Icon icon={Route} size={14} /> {project.lines.length} líneas</span>
                  </div>
                </div>
              </Panel>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
