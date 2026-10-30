"use client";

import { ChevronRight, Database, TriangleAlert } from "lucide-react";
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

  return (
    <header
      style={{ viewTransitionName: "app-topbar" }}
      className="sticky top-0 z-30 flex h-[var(--topbar-height)] items-center gap-3 border-b border-border bg-bg/85 px-5 backdrop-blur-md"
    >
      <nav aria-label="Ruta" className="flex min-w-0 items-center gap-1.5 text-[13px] whitespace-nowrap">
        <span className="font-mono text-[12px] text-faint">DEMO-PLANT</span>
        <Icon icon={ChevronRight} size={14} className="text-faint" />
        {item ? <Icon icon={item.icon} size={15} className="text-muted" /> : null}
        <span className="truncate font-medium text-text">{item?.label ?? "Inicio"}</span>
      </nav>

      <div className="ml-auto flex items-center gap-2">
        <Tip content="Equipo y revisión activos">
          <Pill>
            <Icon icon={Database} size={14} />
            V-101 · rev {revision}
          </Pill>
        </Tip>
        <Tip content={apiEnabled ? "Datos y revisiones servidos por la API configurada; los equipos de la demo siguen siendo sintéticos" : "Archivos sintéticos de la demo offline"}>
          <Pill tone="warning">
            <Icon icon={TriangleAlert} size={14} />
            {apiEnabled ? active.isError ? "API local · sin conexión" : active.data?.dataset === "real" ? "Datos reales · API local" : "Datos sintéticos · API local" : "Datos sintéticos · sin backend"}
          </Pill>
        </Tip>
        <PipelinePill />
        <button type="button" onClick={() => setCopilotOpen(true)} className="rounded-full focus-visible:outline-offset-1">
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
