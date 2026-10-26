"use client";

import { LogOut, Moon, PanelLeftClose, PanelLeftOpen, Sun } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";

import { Tip } from "@/components/ui/controls";
import { Icon } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { useMounted } from "@/lib/use-mounted";
import { NAV, navItemFor } from "@/lib/nav";
import { useUi } from "@/stores/ui";
import { LogoMark } from "./logo";

export function Sidebar() {
  const pathname = usePathname();
  const active = navItemFor(pathname)?.href;
  const collapsed = useUi((s) => s.sidebarCollapsed);
  const toggle = useUi((s) => s.toggleSidebar);

  return (
    // El fondo ocupa toda la altura de la página; el contenido queda fijo al desplazarse
    <aside
      style={{ width: collapsed ? "var(--sidebar-collapsed)" : "var(--sidebar-width)" }}
      className="shrink-0 border-r border-border bg-sidebar"
    >
      <div style={{ viewTransitionName: "app-sidebar" }} className="sticky top-0 flex h-dvh flex-col">
      <div className={cn("flex h-16 items-center gap-3 px-3.5", collapsed && "justify-center px-0")}>
        <LogoMark />
        {!collapsed ? (
          <div className="min-w-0 flex-1 leading-tight">
            <p className="truncate text-[15px] font-semibold text-strong">TrazIA-3D</p>
            <p className="text-xs leading-snug text-muted">Técnicas Reunidas · GA2MODEL</p>
          </div>
        ) : null}
        {!collapsed ? (
          <Tip content="Plegar barra lateral" shortcut={["["]} side="right">
            <button
              type="button"
              onClick={toggle}
              className="rounded-[6px] p-1.5 text-muted hover:bg-surface-sunken hover:text-text"
              aria-label="Plegar barra lateral"
            >
              <Icon icon={PanelLeftClose} />
            </button>
          </Tip>
        ) : null}
      </div>

      {collapsed ? (
        <Tip content="Desplegar barra lateral" shortcut={["["]} side="right">
          <button
            type="button"
            onClick={toggle}
            className="mx-auto mb-2 rounded-[6px] p-1.5 text-muted hover:bg-surface-sunken hover:text-text"
            aria-label="Desplegar barra lateral"
          >
            <Icon icon={PanelLeftOpen} />
          </button>
        </Tip>
      ) : null}

      <nav aria-label="Navegación principal" className="flex-1 overflow-y-auto px-2.5 pb-4">
        {NAV.map((group) => (
          <div key={group.label} className="mt-4 first:mt-1">
            {!collapsed ? (
              <p className="px-2.5 pb-1.5 text-[11px] font-medium tracking-[0.06em] text-faint uppercase">{group.label}</p>
            ) : (
              <div className="mx-auto mb-2 h-px w-6 bg-border" />
            )}
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const isActive = item.href === active;
                const content = (
                  <span
                    className={cn(
                      "relative flex h-9 items-center gap-3 rounded-[var(--radius-control)] px-2.5 text-[14px]",
                      collapsed && "justify-center px-0",
                      item.soon ? "cursor-default text-faint" : isActive ? "font-medium text-accent-text" : "text-muted hover:bg-surface-sunken hover:text-text",
                    )}
                  >
                    {isActive ? (
                      <motion.span
                        layoutId="nav-active"
                        className="absolute inset-0 rounded-[var(--radius-control)] bg-accent-soft"
                        transition={{ type: "spring", stiffness: 520, damping: 40 }}
                      />
                    ) : null}
                    <Icon icon={item.icon} className="relative" size={17} />
                    {!collapsed ? <span className="relative flex-1 truncate">{item.label}</span> : null}
                    {!collapsed && item.soon ? (
                      <span className="relative font-mono text-[11px] text-faint">{item.soon}</span>
                    ) : null}
                  </span>
                );
                return (
                  <li key={item.href}>
                    {item.soon ? (
                      <Tip content={`${item.label} · llega en la fase ${item.soon.slice(1)}`} side="right">
                        <span aria-disabled tabIndex={0} className="block rounded-[var(--radius-control)]">
                          {content}
                        </span>
                      </Tip>
                    ) : collapsed ? (
                      <Tip content={item.label} shortcut={item.shortcut ? ["G", item.shortcut] : undefined} side="right">
                        <Link href={item.href} aria-current={isActive ? "page" : undefined} className="block rounded-[var(--radius-control)]">
                          {content}
                        </Link>
                      </Tip>
                    ) : (
                      <Link href={item.href} aria-current={isActive ? "page" : undefined} className="block rounded-[var(--radius-control)]">
                        {content}
                      </Link>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-border p-2.5">
        {!collapsed ? <DemoCard /> : null}
        <ThemeToggle collapsed={collapsed} />
        <Tip content="La demo no tiene sesiones de usuario" side="right">
          <span
            aria-disabled
            tabIndex={0}
            className={cn(
              "flex h-9 cursor-default items-center gap-3 rounded-[var(--radius-control)] px-2.5 text-[14px] text-faint",
              collapsed && "justify-center px-0",
            )}
          >
            <Icon icon={LogOut} size={17} />
            {!collapsed ? "Salir" : null}
          </span>
        </Tip>
      </div>
      </div>
    </aside>
  );
}

function DemoCard() {
  const hidden = useUi((s) => s.demoCardHidden);
  const hide = useUi((s) => s.hideDemoCard);
  return (
    <div className="mb-2 rounded-[var(--radius-card)] border border-border bg-surface">
      <div className="flex items-center justify-between px-3 py-2.5">
        <p className="flex items-center gap-2 text-[13px] font-medium text-text">
          <span className="size-2 rounded-full bg-warning" aria-hidden />
          Demostración
        </p>
        <button type="button" onClick={() => hide(!hidden)} className="text-xs text-muted hover:text-text">
          {hidden ? "Mostrar" : "Ocultar"}
        </button>
      </div>
      {!hidden ? (
        <div className="border-t border-border px-3 py-2.5 text-xs leading-relaxed text-muted">
          Datos sintéticos de V-101 generados por el núcleo de TrazIA-3D. No son del dataset de Técnicas Reunidas.
          <p className="mt-1.5 text-faint">Dataset real: disponible en el hackatón.</p>
        </div>
      ) : null}
    </div>
  );
}

function ThemeToggle({ collapsed }: { collapsed: boolean }) {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useMounted();
  const dark = !mounted || resolvedTheme !== "light";
  const label = dark ? "Modo claro" : "Modo oscuro";
  const button = (
    <button
      type="button"
      onClick={() => setTheme(dark ? "light" : "dark")}
      className={cn(
        "flex h-9 w-full items-center gap-3 rounded-[var(--radius-control)] px-2.5 text-[14px] text-muted hover:bg-surface-sunken hover:text-text",
        collapsed && "justify-center px-0",
      )}
    >
      <Icon icon={dark ? Sun : Moon} size={17} />
      {!collapsed ? label : null}
    </button>
  );
  return collapsed ? (
    <Tip content={label} side="right">
      {button}
    </Tip>
  ) : (
    button
  );
}
