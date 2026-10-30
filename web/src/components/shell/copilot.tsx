"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { MousePointerClick, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { CopilotMark } from "@/components/brand/copilot-mark";
import { CopilotConversation } from "@/features/copilot/conversation";
import { apiEnabled } from "@/lib/api/config";
import { Tip } from "@/components/ui/controls";
import { ConfidenceBar } from "@/components/ui/data";
import { Badge, EmptyState, Icon, Kbd } from "@/components/ui/primitives";
import { formatValue } from "@/lib/format";
import { riskLevel, type ReviewField } from "@/lib/mock/fields";
import { useReviewFields } from "@/lib/queries";
import { useSelection } from "@/stores/selection";
import { useUi } from "@/stores/ui";

/** Consecuencias de un error por grupo de campo (reglas del roadmap, sin modelo de lenguaje). */
const CONSEQUENCE: Record<ReviewField["group"], string> = {
  Identificación: "El tag enlaza el modelo con la lista de equipos y con el resto de disciplinas.",
  Envolvente: "La envolvente fija la posición de las boquillas, las plataformas y la carga sobre la cimentación.",
  Soporte: "El faldón define la cota de las boquillas inferiores y la interfaz con civil.",
  Boquillas: "Una boquilla mal situada se propaga a piping: la tubería llegaría a un punto que no existe.",
  "Datos de diseño": "Los datos de diseño viajan como propiedades del IFC y los consultan mecánica y civil.",
};

export function CopilotLauncher() {
  const setOpen = useUi((s) => s.setCopilotOpen);
  const pathname = usePathname();
  // En Revisión y Cambios taparía la cola de campos y los controles del visor;
  // allí se abre desde la píldora de la barra superior.
  if (pathname.startsWith("/revision") || pathname.startsWith("/cambios")) return null;
  return (
    <Tip content="Copiloto de revisión" side="left">
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Abrir copiloto"
        className="copilot-launcher fixed right-5 bottom-5 z-30 inline-flex size-[52px] items-center justify-center rounded-full border border-border-strong bg-surface-raised shadow-[var(--shadow-pop)]"
      >
        <CopilotMark className="size-[26px]" />
      </button>
    </Tip>
  );
}

export function CopilotPanel() {
  const open = useUi((s) => s.copilotOpen);
  const setOpen = useUi((s) => s.setCopilotOpen);
  const revision = useUi((s) => s.revision);
  const selectedId = useSelection((s) => s.selectedId);
  const selectedPath = useSelection((s) => s.selectedPath);
  const { data: fields } = useReviewFields(revision);

  const field =
    fields?.find((f) => f.path === selectedPath) ?? fields?.find((f) => selectedId != null && f.elementId === selectedId);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen} modal={false}>
      <Dialog.Portal>
        <Dialog.Content
          onInteractOutside={(e) => e.preventDefault()}
          className="sheet-content fixed top-[calc(var(--topbar-height)+12px)] right-3 bottom-3 z-40 flex w-[380px] max-w-[calc(100vw_-_24px)] flex-col rounded-[var(--radius-panel)] border border-border bg-surface-raised shadow-[var(--shadow-pop)]"
        >
          <header className="flex items-start gap-3 border-b border-border px-5 py-4">
            <span className="inline-flex size-9 items-center justify-center rounded-full border border-border-strong bg-surface">
              <CopilotMark className="size-5" />
            </span>
            <div className="min-w-0 flex-1">
              <Dialog.Title className="text-[15px] font-semibold text-strong">Copiloto de revisión</Dialog.Title>
              <Dialog.Description className="text-xs text-muted">{apiEnabled ? "Modelo local · herramientas de lectura y citas" : "Reglas sobre el JSON extraído · modo offline"}</Dialog.Description>
            </div>
            <Dialog.Close className="rounded-[6px] p-1 text-muted hover:bg-surface-sunken hover:text-text" aria-label="Cerrar copiloto">
              <Icon icon={X} />
            </Dialog.Close>
          </header>

          <div className="flex-1 overflow-y-auto px-5 py-4">
            {apiEnabled ? <CopilotConversation key={`${revision}:${field?.path ?? "equipment"}`} revision={revision} field={field} /> : field ? <Explanation field={field} /> : (
              <EmptyState icon={MousePointerClick} title="Selecciona un campo">
                Elige un valor en la cola de revisión, una región del plano o un elemento del modelo para ver de dónde
                sale, qué confianza tiene y qué pasa si está mal.
              </EmptyState>
            )}
          </div>

          <footer className="border-t border-border px-5 py-3 text-xs text-faint">
            {apiEnabled ? "El copiloto propone. Las acciones de revisión siguen en tus manos." : "Reglas de la demo offline. Conecta la API local para consultar Ollama con citas."}
          </footer>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function Explanation({ field }: { field: ReviewField }) {
  const s = field.source;
  const where = s.page ? `página ${s.page}` : s.sheet && s.cell ? `hoja ${s.sheet}, celdas ${s.cell}` : s.locator;
  const level = riskLevel(field);
  return (
    <div className="space-y-5 text-[13px]">
      <div>
        <p className="text-xs text-muted">{field.group}</p>
        <p className="mt-0.5 text-[15px] font-semibold text-strong">{field.label}</p>
        <p className="mt-1 text-[22px] font-semibold text-text">{formatValue(field.correctedValue ?? field.value, field.unit)}</p>
      </div>

      <Section title="De dónde sale">
        Documento <span className="font-medium text-text">{s.document_id}</span>, {where}.
        {s.bbox ? " La región exacta está marcada en el plano." : " Viene de una celda de la hoja de datos."}
      </Section>

      <Section title="Por qué tiene esta confianza">
        <ConfidenceBar value={field.confidence} className="mb-1.5" />
        Lo ha leído el extractor de etiquetas: identifica el valor con una regla. El 0,75 marca que es un candidato, no una
        probabilidad calibrada; la calibración llegará con el bench.
      </Section>

      <Section title="Qué pasa si está mal">
        <Badge tone={level === "alto" ? "danger" : level === "medio" ? "warning" : "neutral"} className="mb-1.5">
          Riesgo {level}
        </Badge>
        <p>{CONSEQUENCE[field.group]}</p>
      </Section>

      <Section title="Qué puedes hacer">
        <ul className="space-y-1.5">
          <li className="flex items-center gap-2"><Kbd>A</Kbd> Aceptar si coincide con el plano.</li>
          <li className="flex items-center gap-2"><Kbd>E</Kbd> Corregir el valor.</li>
          <li className="flex items-center gap-2"><Kbd>S</Kbd> Marcarlo como supuesto si el plano no lo da.</li>
        </ul>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-1.5 text-xs font-medium text-faint">{title}</h3>
      <div className="leading-relaxed text-muted">{children}</div>
    </section>
  );
}
