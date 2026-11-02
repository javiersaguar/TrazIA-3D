"use client";

import { Command } from "cmdk";
import { CircleDot, Download, Keyboard, MessageSquareText, Moon, Ruler, Sun, type LucideIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import type { ReactNode } from "react";
import { Icon, Kbd } from "@/components/ui/primitives";
import { DEMO } from "@/lib/mock/api";
import { NAV_ITEMS } from "@/lib/nav";
import { useReviewFields } from "@/lib/queries";
import { formatValue } from "@/lib/format";
import { useSelection } from "@/stores/selection";
import { useUi } from "@/stores/ui";

export function CommandMenu() {
  const open = useUi((s) => s.commandOpen);
  const setOpen = useUi((s) => s.setCommandOpen);
  const revision = useUi((s) => s.revision);
  const setShortcutsOpen = useUi((s) => s.setShortcutsOpen);
  const setCopilotOpen = useUi((s) => s.setCopilotOpen);
  const setSelected = useSelection((s) => s.setSelected);
  const { data: fields } = useReviewFields(revision);
  const router = useRouter();
  const { resolvedTheme, setTheme } = useTheme();

  const run = (fn: () => void) => {
    setOpen(false);
    fn();
  };

  const nozzles = [...new Set((fields ?? []).filter((f) => f.group === "Boquillas").map((f) => f.elementId))];

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Menú de comandos"
      loop
      overlayClassName="cmd-overlay fixed inset-0 z-50 bg-[var(--scrim)]"
      contentClassName="cmd-content fixed top-[14vh] left-1/2 z-50 w-[min(640px,calc(100vw-32px))] -translate-x-1/2 overflow-hidden rounded-[var(--radius-panel)] border border-border bg-surface-raised shadow-[var(--shadow-pop)]"
    >
      <div className="flex items-center gap-2 border-b border-border px-4">
        <Command.Input
          placeholder="Ir a una pantalla, boquilla o campo…"
          className="h-12 flex-1 bg-transparent text-[15px] text-text outline-none placeholder:text-faint"
        />
        <Kbd>Esc</Kbd>
      </div>
      <Command.List className="max-h-[min(420px,60vh)] overflow-y-auto p-2">
        <Command.Empty className="px-3 py-8 text-center text-[13px] text-muted">
          Nada coincide. Prueba con «N3», «faldón» o «cambios».
        </Command.Empty>

        <Group heading="Pantallas">
          {NAV_ITEMS.map((item) => (
            <Item key={item.href} icon={item.icon} value={`pantalla ${item.label}`} onSelect={() => run(() => router.push(item.href))} hint={item.shortcut ? ["G", item.shortcut] : undefined}>
              {item.label}
            </Item>
          ))}
        </Group>

        {nozzles.length ? (
          <Group heading="Boquillas">
            {nozzles.map((id) => (
              <Item
                key={id}
                icon={CircleDot}
                value={`boquilla ${id.replace("nozzle:", "")}`}
                onSelect={() =>
                  run(() => {
                    setSelected(id);
                    router.push("/revision");
                  })
                }
              >
                Boquilla {id.replace("nozzle:", "")}
              </Item>
            ))}
          </Group>
        ) : null}

        {fields?.length ? (
          <Group heading={`Campos · rev ${revision}`}>
            {fields.map((f) => (
              <Item
                key={f.path}
                icon={Ruler}
                value={`campo ${f.label} ${f.path}`}
                onSelect={() =>
                  run(() => {
                    setSelected(f.elementId, f.path);
                    router.push("/revision");
                  })
                }
                trailing={<span className="text-xs text-muted">{formatValue(f.value, f.unit)}</span>}
              >
                {f.label}
              </Item>
            ))}
          </Group>
        ) : null}

        <Group heading="Acciones">
          <Item icon={resolvedTheme === "light" ? Moon : Sun} value="tema claro oscuro" onSelect={() => run(() => setTheme(resolvedTheme === "light" ? "dark" : "light"))}>
            {resolvedTheme === "light" ? "Cambiar a modo oscuro" : "Cambiar a modo claro"}
          </Item>
          <Item icon={MessageSquareText} value="abrir copiloto" onSelect={() => run(() => setCopilotOpen(true))}>
            Abrir el copiloto
          </Item>
          <Item icon={Keyboard} value="atajos teclado" onSelect={() => run(() => setShortcutsOpen(true))} hint={["?"]}>
            Ver atajos de teclado
          </Item>
          {(["A", "B"] as const).map((rev) => (
            <Item key={`ifc-${rev}`} icon={Download} value={`descargar ifc rev ${rev}`} onSelect={() => run(() => download(DEMO.revisions[rev].ifc))}>
              Descargar IFC DRAFT · rev {rev}
            </Item>
          ))}
          {(["A", "B"] as const).map((rev) => (
            <Item key={`json-${rev}`} icon={Download} value={`descargar json rev ${rev}`} onSelect={() => run(() => download(DEMO.revisions[rev].json))}>
              Descargar JSON · rev {rev}
            </Item>
          ))}
        </Group>
      </Command.List>
    </Command.Dialog>
  );
}

function download(href: string) {
  const a = document.createElement("a");
  a.href = href;
  a.download = href.split("/").at(-1) ?? "archivo";
  a.click();
}

function Group({ heading, children }: { heading: string; children: ReactNode }) {
  return (
    <Command.Group
      heading={heading}
      className="mb-1 [&_[cmdk-group-heading]]:px-2.5 [&_[cmdk-group-heading]]:pt-2 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-faint"
    >
      {children}
    </Command.Group>
  );
}

function Item({
  icon,
  value,
  onSelect,
  children,
  hint,
  trailing,
}: {
  icon: LucideIcon;
  value: string;
  onSelect: () => void;
  children: ReactNode;
  hint?: string[];
  trailing?: ReactNode;
}) {
  return (
    <Command.Item
      value={value}
      onSelect={onSelect}
      className="flex h-10 cursor-default items-center gap-3 rounded-[var(--radius-control)] px-2.5 text-[14px] text-text data-[selected=true]:bg-accent-soft data-[selected=true]:text-accent-text"
    >
      <Icon icon={icon} className="text-muted" />
      <span className="flex-1 truncate">{children}</span>
      {trailing}
      {hint ? (
        <span className="flex gap-0.5">
          {hint.map((k) => (
            <Kbd key={k}>{k}</Kbd>
          ))}
        </span>
      ) : null}
    </Command.Item>
  );
}
