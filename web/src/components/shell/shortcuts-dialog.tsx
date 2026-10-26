"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { Icon, Kbd } from "@/components/ui/primitives";
import { useUi } from "@/stores/ui";

export const SHORTCUTS: { group: string; items: { keys: string[]; label: string }[] }[] = [
  {
    group: "General",
    items: [
      { keys: ["Ctrl", "K"], label: "Menú de comandos" },
      { keys: ["?"], label: "Ver estos atajos" },
      { keys: ["["], label: "Plegar o desplegar la barra lateral" },
      { keys: ["G", "1–7"], label: "Ir a Proyecto, Pipeline, Revisión, Cambios, Bench, Impacto o Estudio" },
    ],
  },
  {
    group: "Revisión de campos",
    items: [
      { keys: ["J"], label: "Siguiente campo" },
      { keys: ["K"], label: "Campo anterior" },
      { keys: ["A"], label: "Aceptar el valor" },
      { keys: ["E"], label: "Corregir el valor" },
      { keys: ["S"], label: "Marcar como supuesto" },
      { keys: ["Ctrl", "Z"], label: "Deshacer la última acción" },
    ],
  },
  {
    group: "Cambios",
    items: [{ keys: ["Espacio"], label: "Reproducir o pausar los cambios" }],
  },
];

export function ShortcutsDialog() {
  const open = useUi((s) => s.shortcutsOpen);
  const setOpen = useUi((s) => s.setShortcutsOpen);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="cmd-overlay fixed inset-0 z-50 bg-[var(--scrim)]" />
        <Dialog.Content className="cmd-content fixed top-[12vh] left-1/2 z-50 w-[min(560px,calc(100vw-32px))] -translate-x-1/2 rounded-[var(--radius-panel)] border border-border bg-surface-raised p-5 shadow-[var(--shadow-pop)]">
          <div className="flex items-center justify-between">
            <Dialog.Title className="text-[15px] font-semibold text-strong">Atajos de teclado</Dialog.Title>
            <Dialog.Close className="rounded-[6px] p-1 text-muted hover:bg-surface-sunken hover:text-text" aria-label="Cerrar">
              <Icon icon={X} />
            </Dialog.Close>
          </div>
          <Dialog.Description className="mt-1 text-[13px] text-muted">
            Los atajos de una letra no actúan mientras escribes en un campo.
          </Dialog.Description>
          <div className="mt-4 space-y-5">
            {SHORTCUTS.map((g) => (
              <section key={g.group}>
                <h3 className="mb-2 text-xs font-medium text-faint">{g.group}</h3>
                <ul className="divide-y divide-border rounded-[var(--radius-card)] border border-border">
                  {g.items.map((s) => (
                    <li key={s.label} className="flex items-center justify-between px-3 py-2 text-[13px]">
                      <span className="text-text">{s.label}</span>
                      <span className="flex gap-1">
                        {s.keys.map((k) => (
                          <Kbd key={k}>{k}</Kbd>
                        ))}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
