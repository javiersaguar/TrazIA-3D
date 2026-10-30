"use client";

import { Box, FileSpreadsheet, FileText, MessageSquareWarning, type LucideIcon } from "lucide-react";

import { Tip } from "@/components/ui/controls";
import { Badge, Button, IconTile, Panel, PanelHeader } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { EXPORTS } from "@/lib/mock/bocetos";

const FORMATS: { icon: LucideIcon; title: string; text: string; gated?: boolean }[] = [
  { icon: Box, title: "Modelo IFC", text: "IFC4 con GUID estable por ID. En borrador hasta que se aprueba.", gated: true },
  { icon: MessageSquareWarning, title: "Incidencias BCF", text: "Cambios entre revisiones como incidencias para el visor del cliente." },
  { icon: FileSpreadsheet, title: "Campos en CSV", text: "Valor, unidad, fuente y confianza de cada campo revisado." },
  { icon: FileText, title: "Informe PDF", text: "Resumen de la revisión con sus citas al plano y las cifras del bench." },
];

export function ReportsSketch() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {FORMATS.map((f) => (
          <Panel key={f.title} className="flex flex-col p-4">
            <IconTile icon={f.icon} tone="sky" />
            <p className="mt-3 text-[15px] font-semibold text-strong">{f.title}</p>
            <p className="mt-1 flex-1 text-[13px] text-muted">{f.text}</p>
            {f.gated ? <p className="mt-3 text-[12px] text-warning">El IFC aprobado exige revisión humana y aprobación ligada a la huella de los datos.</p> : null}
            <Tip content="Boceto: la exportación aún no está conectada">
              <span className="mt-4">
                <Button size="sm" disabled className="w-full">
                  Exportar
                </Button>
              </span>
            </Tip>
          </Panel>
        ))}
      </div>

      <Panel>
        <PanelHeader title="Historial de exportaciones" description="Cada fichero guarda la huella de los datos con los que se generó." />
        <div className="overflow-x-auto px-3 pb-3">
          <table className="w-full min-w-[640px] border-separate border-spacing-0 text-[13px]">
            <thead>
              <tr className="text-left text-xs text-muted">
                {["Fecha", "Formato", "Alcance", "Huella", "Estado"].map((h, i, a) => (
                  <th
                    key={h}
                    className={cn(
                      "border-y border-border bg-surface-sunken px-3 py-2.5 font-medium",
                      i === 0 && "rounded-l-[var(--radius-control)] border-l",
                      i === a.length - 1 && "rounded-r-[var(--radius-control)] border-r",
                    )}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {EXPORTS.map((e) => (
                <tr key={e.hash} className="animate-[row-in_var(--dur-slow)_var(--ease-out)]">
                  <td className="border-b border-border px-3 py-2.5 text-muted tabular-nums">{e.date}</td>
                  <td className="border-b border-border px-3 py-2.5 text-text">{e.kind}</td>
                  <td className="border-b border-border px-3 py-2.5">{e.scope}</td>
                  <td className="border-b border-border px-3 py-2.5">
                    <span className="font-mono text-[12px] text-faint">{e.hash}</span>
                  </td>
                  <td className="border-b border-border px-3 py-2.5">
                    <Badge tone={e.state === "Aprobado" ? "approved" : "neutral"}>{e.state}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
