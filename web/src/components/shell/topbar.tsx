"use client";

import { ChevronRight, Database, Menu, TriangleAlert } from "lucide-react";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { CopilotMark } from "@/components/brand/copilot-mark";
import { Tip } from "@/components/ui/controls";
import { Icon, LiveDot, Pill } from "@/components/ui/primitives";
import { apiEnabled } from "@/lib/api/config";
import { useApiSync } from "@/lib/api/use-api-sync";
import { useRevision } from "@/lib/queries";
import { relativeSeconds } from "@/lib/format";
import { navItemFor } from "@/lib/nav";
import { usePipeline } from "@/stores/pipeline";
import { useUi } from "@/stores/ui";

export function Topbar() {
  useApiSync();
  const pathname = usePathname();
  const item = navItemFor(pathname);
  const revision = useUi((s) => s.revision);
  const active = useRevision(revision);
  const setCopilotOpen = useUi((s) => s.setCopilotOpen);
  const setNavOpen = useUi((s) => s.setNavOpen);

  // Fuente de los datos: siempre visible, también en móvil (en corto)
  const source = apiEnabled
    ? active.isError
      ? { long: "API local · sin conexión", short: "Sin conexión" }
      : active.data?.dataset === "real"
        ? { long: "Datos reales · API local", short: "Reales" }
        : { long: "Datos sintéticos · API local", short: "Sintéticos" }
    : { long: "Datos sintéticos · sin backend", short: "Sintéticos" };

  return (
    <header
      style={{ viewTransitionName: "app-topbar" }}
      className="sticky top-0 z-30 flex h-[var(--topbar-height)] items-center gap-2 border-b border-border bg-bg/85 px-3 backdrop-blur-md sm:gap-3 sm:px-5"
    >
      <button
        type="button"
        onClick={() => setNavOpen(true)}
        aria-label="Abrir navegación"
        className="-ml-1 flex size-9 shrink-0 items-center justify-center rounded-[var(--radius-control)] text-muted hover:bg-surface-raised hover:text-text lg:hidden"
      >
        <Icon icon={Menu} size={18} />
      </button>

      <nav aria-label="Ruta" className="flex min-w-0 items-center gap-1.5 text-[13px] whitespace-nowrap">
        {/* El proyecto solo cuando sobra sitio: a 1024 px con barra lateral, la pantalla va antes */}
        <span className="hidden font-mono text-[12px] text-faint xl:inline">DEMO-PLANT</span>
        <Icon icon={ChevronRight} size={14} className="hidden text-faint xl:block" />
        {item ? <Icon icon={item.icon} size={15} className="text-muted" /> : null}
        <span className="truncate font-medium text-text">{item?.label ?? "Inicio"}</span>
      </nav>

      <div className="ml-auto flex items-center gap-2">
        <Tip content="Equipo y revisión activos">
          <span className="hidden md:inline-flex">
            <Pill>
              <Icon icon={Database} size={14} />
              V-101 · rev {revision}
            </Pill>
          </span>
        </Tip>
        <Tip content={apiEnabled ? "Datos y revisiones servidos por la API configurada; los equipos de la demo siguen siendo sintéticos" : "Archivos sintéticos de la demo offline"}>
          <Pill tone="warning" tabIndex={0}>
            <Icon icon={TriangleAlert} size={14} />
            <span className="hidden sm:inline">{source.long}</span>
            <span className="sm:hidden">{source.short}</span>
          </Pill>
        </Tip>
        <span className="hidden md:inline-flex">
          <PipelinePill />
        </span>
        <button type="button" onClick={() => setCopilotOpen(true)} className="hidden rounded-full focus-visible:outline-offset-1 md:block">
          <Pill className="hover:text-text">
            <CopilotMark className="size-3.5" />
            Copiloto
          </Pill>
        </button>
      </div>
    </header>
  );
}

/** "Pipeline: último trabajo hace X s", como la píldora de tiempo real de PIDS. */
function PipelinePill() {
  const running = usePipeline((s) => s.running);
  const error = usePipeline((s) => s.error);
  const lastFinishedAt = usePipeline((s) => s.lastFinishedAt);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const text = error ? "Pipeline: requiere atención" : running
    ? "Pipeline: procesando V-101"
    : lastFinishedAt
      ? `Pipeline: último trabajo ${relativeSeconds((now - lastFinishedAt) / 1000)}`
      : "Pipeline: en espera";

  return (
    <Tip content={apiEnabled ? "Estado del trabajo real y eventos SSE de la API" : "Repetición simulada sobre los documentos sintéticos"}>
      <Pill tone={error ? "warning" : "live"}>
        {running || lastFinishedAt ? <LiveDot /> : <span className="size-2 rounded-full bg-faint" aria-hidden />}
        <span className={running ? "text-live" : undefined}>{text}</span>
      </Pill>
    </Tip>
  );
}
