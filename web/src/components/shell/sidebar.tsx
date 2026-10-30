"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { LogOut, Moon, PanelLeftClose, PanelLeftOpen, Search, Sun, X } from "lucide-react";
import { LayoutGroup, motion } from "motion/react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect } from "react";

import { LogoMark, LogoWordmark } from "@/components/brand/logo";
import { Tip } from "@/components/ui/controls";
import { Icon, Kbd } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { useMounted } from "@/lib/use-mounted";
import { NAV, navItemFor } from "@/lib/nav";
import { endDemoSession, initialsOf, useDemoUser } from "@/lib/session";
import { useUi } from "@/stores/ui";

/** Barra lateral fija desde 1024 px. Por debajo, la misma navegación vive en MobileNav. */
export function Sidebar() {
  const collapsed = useUi((s) => s.sidebarCollapsed);
  return (
    // El fondo ocupa toda la altura de la página; el contenido queda fijo al desplazarse
    <aside
      style={{ width: collapsed ? "var(--sidebar-collapsed)" : "var(--sidebar-width)" }}
      className="hidden shrink-0 border-r border-border bg-sidebar lg:block"
    >
      <div style={{ viewTransitionName: "app-sidebar" }} className="sticky top-0 flex h-dvh flex-col">
        <SidebarBody collapsed={collapsed} />
      </div>
    </aside>
  );
}

/** Panel que entra desde la izquierda en móvil y tableta vertical. */
export function MobileNav() {
  const open = useUi((s) => s.navOpen);
  const setOpen = useUi((s) => s.setNavOpen);

  // Si la ventana crece hasta mostrar la barra fija, el panel se cierra para no bloquear la página
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const onChange = () => mq.matches && setOpen(false);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [setOpen]);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="cmd-overlay fixed inset-0 z-50 bg-[var(--scrim)] lg:hidden" />
        <Dialog.Content
          aria-describedby={undefined}
          className="nav-sheet fixed inset-y-0 left-0 z-50 flex w-[min(300px,86vw)] flex-col border-r border-border bg-sidebar shadow-[var(--shadow-pop)] lg:hidden"
        >
          <Dialog.Title className="sr-only">Navegación</Dialog.Title>
          {/* Grupo propio: la píldora activa no salta desde la barra fija oculta */}
          <LayoutGroup id="nav-movil">
            <SidebarBody collapsed={false} onNavigate={() => setOpen(false)} />
          </LayoutGroup>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function SidebarBody({ collapsed, onNavigate }: { collapsed: boolean; onNavigate?: () => void }) {
  const pathname = usePathname();
  const active = navItemFor(pathname)?.href;
  const toggle = useUi((s) => s.toggleSidebar);
  const setCommandOpen = useUi((s) => s.setCommandOpen);
  const mobile = onNavigate != null;
  const openSearch = () => {
    onNavigate?.();
    setCommandOpen(true);
  };

  return (
    <>
        <div className={cn("flex h-16 shrink-0 items-center gap-2.5 px-4", collapsed && "justify-center px-0")}>
          <Link
            href="/proyecto"
            onClick={onNavigate}
            aria-label="TrazIA 3D · inicio"
            className="flex min-w-0 flex-1 items-center gap-2.5 rounded-[var(--radius-control)]"
          >
            <LogoMark className="size-8" />
            {!collapsed ? (
              <span className="min-w-0 leading-tight">
                <LogoWordmark className="h-[13px] w-auto" title="TrazIA 3D" />
                <span className="mt-1 block truncate font-mono text-[10.5px] text-faint">Técnicas Reunidas · GA2MODEL</span>
              </span>
            ) : null}
          </Link>
          {mobile ? (
            <Dialog.Close
              aria-label="Cerrar navegación"
              className="flex size-9 items-center justify-center rounded-[var(--radius-control)] text-muted hover:bg-surface-raised hover:text-text"
            >
              <Icon icon={X} />
            </Dialog.Close>
          ) : !collapsed ? (
            <Tip content="Plegar barra lateral" shortcut={["["]} side="right">
              <button
                type="button"
                onClick={toggle}
                className="rounded-[6px] p-1.5 text-faint hover:bg-surface-raised hover:text-text"
                aria-label="Plegar barra lateral"
              >
                <Icon icon={PanelLeftClose} />
              </button>
            </Tip>
          ) : null}
        </div>

        <div className={cn("border-b border-border px-3 pb-3", collapsed && "px-2")}>
          {collapsed ? (
            <>
              <Tip content="Desplegar barra lateral" shortcut={["["]} side="right">
                <button
                  type="button"
                  onClick={toggle}
                  className="mx-auto mb-1 flex size-9 items-center justify-center rounded-[var(--radius-control)] text-faint hover:bg-surface-raised hover:text-text"
                  aria-label="Desplegar barra lateral"
                >
                  <Icon icon={PanelLeftOpen} />
                </button>
              </Tip>
              <Tip content="Buscar" shortcut={["Ctrl", "K"]} side="right">
                <button
                  type="button"
                  onClick={openSearch}
                  aria-label="Buscar"
                  className="mx-auto flex size-9 items-center justify-center rounded-[var(--radius-control)] border border-border bg-surface text-muted hover:text-text"
                >
                  <Icon icon={Search} />
                </button>
              </Tip>
            </>
          ) : (
            <button
              type="button"
              onClick={openSearch}
              className="surface-sheen flex h-10 w-full items-center gap-2.5 rounded-[10px] border border-border bg-surface px-3 text-[14px] text-muted transition-colors duration-[var(--dur-fast)] hover:border-border-strong hover:text-text"
            >
              <Icon icon={Search} size={16} />
              Buscar
              {!mobile ? (
                <span className="ml-auto flex gap-1">
                  <Kbd>Ctrl</Kbd>
                  <Kbd>K</Kbd>
                </span>
              ) : null}
            </button>
          )}
        </div>

        <nav aria-label="Navegación principal" className="flex-1 overflow-y-auto px-3 pb-4">
          {NAV.map((group) => (
            <div key={group.label} className="mt-5 first:mt-4">
              {!collapsed ? (
                <p className="px-2.5 pb-2 font-mono text-[11px] text-faint">{group.label}</p>
              ) : (
                <div className="mx-auto mb-2 h-px w-6 bg-border" />
              )}
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const isActive = item.href === active;
                  const content = (
                    <span
                      className={cn(
                        "relative flex h-9 items-center gap-3 rounded-[10px] px-2.5 text-[14px] transition-colors duration-[var(--dur-fast)]",
                        collapsed && "justify-center px-0",
                        isActive ? "text-strong" : "text-muted hover:bg-surface-raised/60 hover:text-text",
                      )}
                    >
                      {isActive ? (
                        <motion.span
                          layoutId="nav-active"
                          className="nav-pill absolute inset-0 rounded-[10px]"
                          transition={{ type: "spring", duration: 0.35, bounce: 0.12 }}
                        />
                      ) : null}
                      <Icon icon={item.icon} className={cn("relative", isActive && "text-accent-text")} size={17} />
                      {!collapsed ? <span className="relative flex-1 truncate">{item.label}</span> : null}
                      {!collapsed && !mobile && item.shortcut ? (
                        <span className="relative font-mono text-[11px] text-faint uppercase">{item.shortcut}</span>
                      ) : null}
                    </span>
                  );
                  return (
                    <li key={item.href}>
                      {collapsed ? (
                        <Tip content={item.label} shortcut={item.shortcut ? ["G", item.shortcut.toUpperCase()] : undefined} side="right">
                          <Link href={item.href} aria-current={isActive ? "page" : undefined} className="block rounded-[10px]">
                            {content}
                          </Link>
                        </Tip>
                      ) : (
                        <Link href={item.href} onClick={onNavigate} aria-current={isActive ? "page" : undefined} className="block rounded-[10px]">
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

        <div className="border-t border-border p-3">
          <DemoNotice collapsed={collapsed} />
          <UserRow collapsed={collapsed} onSignOut={onNavigate} />
        </div>
    </>
  );
}

/** Pie: usuario de la sesión demo con el cambio de tema y la salida a mano. */
function UserRow({ collapsed, onSignOut }: { collapsed: boolean; onSignOut?: () => void }) {
  const user = useDemoUser() ?? "demo";
  const avatar = (
    <span className="inline-flex size-8 shrink-0 items-center justify-center rounded-full border border-border-strong bg-surface-raised font-mono text-[11px] text-text">
      {initialsOf(user)}
    </span>
  );
  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-1">
        <Tip content={`${user} · sesión de demostración`} side="right">
          <span className="flex size-9 items-center justify-center">{avatar}</span>
        </Tip>
        <ThemeToggle />
        <SignOut onDone={onSignOut} />
      </div>
    );
  }
  return (
    <div className="flex items-center gap-2.5 px-1">
      {avatar}
      <span className="min-w-0 flex-1 leading-tight">
        <span className="block truncate text-[13px] text-text">{user}</span>
        <span className="block font-mono text-[10.5px] text-faint">sesión demo</span>
      </span>
      <ThemeToggle />
      <SignOut onDone={onSignOut} />
    </div>
  );
}

const footButton =
  "flex size-8 items-center justify-center rounded-[var(--radius-control)] text-muted transition-colors duration-[var(--dur-fast)] hover:bg-surface-raised hover:text-text";

function SignOut({ onDone }: { onDone?: () => void }) {
  const router = useRouter();
  return (
    <Tip content="Salir" side="top">
      <button
        type="button"
        aria-label="Salir"
        onClick={() => {
          onDone?.();
          endDemoSession();
          router.push("/");
        }}
        className={footButton}
      >
        <Icon icon={LogOut} size={16} />
      </button>
    </Tip>
  );
}

/** Aviso de una línea: la demo usa datos sintéticos; el detalle, en el tooltip. */
function DemoNotice({ collapsed }: { collapsed: boolean }) {
  const text = "Datos sintéticos de V-101 generados por el núcleo de TrazIA-3D. No son del dataset de Técnicas Reunidas.";
  return (
    <Tip content={text} side="right">
      <p
        tabIndex={0}
        className={cn(
          "mb-2 flex h-8 items-center gap-2 rounded-[var(--radius-control)] border border-warning-border bg-warning-bg px-2.5 text-[12px] text-warning",
          collapsed && "mx-auto size-8 justify-center px-0",
        )}
      >
        <span className="size-1.5 shrink-0 rounded-full bg-warning" aria-hidden />
        {!collapsed ? <span className="truncate">Demostración · datos sintéticos</span> : <span className="sr-only">{text}</span>}
      </p>
    </Tip>
  );
}

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useMounted();
  const dark = !mounted || resolvedTheme !== "light";
  const label = dark ? "Modo claro" : "Modo oscuro";
  return (
    <Tip content={label} side="top">
      <button type="button" aria-label={label} onClick={() => setTheme(dark ? "light" : "dark")} className={footButton}>
        <Icon icon={dark ? Sun : Moon} size={16} />
      </button>
    </Tip>
  );
}
