"use client";

import { ChevronRight, Database, MessageSquareText, Search, TriangleAlert } from "lucide-react";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Tip } from "@/components/ui/controls";
import { Icon, Kbd, LiveDot, Pill } from "@/components/ui/primitives";
import { relativeSeconds } from "@/lib/format";
import { navItemFor } from "@/lib/nav";
import { usePipeline } from "@/stores/pipeline";
import { useUi } from "@/stores/ui";

export function Topbar() {
  const pathname = usePathname();
  const item = navItemFor(pathname);
  const revision = useUi((s) => s.revision);
  const setCommandOpen = useUi((s) => s.setCommandOpen);
  const setCopilotOpen = useUi((s) => s.setCopilotOpen);

  return (
    <header
      style={{ viewTransitionName: "app-topbar" }}
      className="sticky top-0 z-30 flex h-[var(--topbar-height)] items-center gap-3 border-b border-border bg-surface-sunken/95 px-5 backdrop-blur-[2px]"
    >
      <nav aria-label="Ruta" className="flex min-w-0 items-center gap-1.5 text-[13px] whitespace-nowrap">
        <span className="text-muted">DEMO-PLANT</span>
        <Icon icon={ChevronRight} size={14} className="text-faint" />
        <span className="truncate font-medium text-text">{item?.label ?? "Inicio"}</span>
      </nav>

      <div className="ml-auto flex items-center gap-2">
        <Tip content="Equipo y revisión activos">
          <Pill>
            <Icon icon={Database} size={14} />
            V-101 · rev {revision}
          </Pill>
        </Tip>
        <Tip content="Todo lo que se ve sale de archivos sintéticos de la demo; todavía no hay API">
          <Pill tone="warning">
            <Icon icon={TriangleAlert} size={14} />
            Datos sintéticos · sin backend
          </Pill>
        </Tip>
        <PipelinePill />
        <button type="button" onClick={() => setCopilotOpen(true)} className="rounded-full focus-visible:outline-offset-1">
          <Pill className="hover:text-text">
            <Icon icon={MessageSquareText} size={14} />
            Copiloto
          </Pill>
        </button>
        <button
          type="button"
          onClick={() => setCommandOpen(true)}
          className="flex h-7 items-center gap-2 rounded-[var(--radius-control)] border border-border bg-surface pr-1 pl-2.5 text-xs text-muted hover:text-text"
        >
          <Icon icon={Search} size={14} />
          Buscar
          <Kbd>Ctrl K</Kbd>
        </button>
      </div>
    </header>
  );
}

/** "Pipeline: último trabajo hace X s", como la píldora de tiempo real de PIDS. */
function PipelinePill() {
  const running = usePipeline((s) => s.running);
  const lastFinishedAt = usePipeline((s) => s.lastFinishedAt);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const text = running
    ? "Pipeline: procesando V-101"
    : lastFinishedAt
      ? `Pipeline: último trabajo ${relativeSeconds((now - lastFinishedAt) / 1000)}`
      : "Pipeline: en espera";

  return (
    <Tip content="Repetición simulada sobre los documentos sintéticos">
      <Pill tone="live">
        {running || lastFinishedAt ? <LiveDot /> : <span className="size-2 rounded-full bg-faint" aria-hidden />}
        <span className={running ? "text-live" : undefined}>{text}</span>
      </Pill>
    </Tip>
  );
}
