"use client";

import { Maximize, Minimize } from "lucide-react";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode, type RefObject } from "react";

import { Kbd } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { inGSequence, isTyping } from "./global-keys";

/*
  Pantalla completa de las vistas 3D: botón y tecla F en todas.
  Con varias vistas en la página, F actúa sobre la que está bajo el cursor o, si no hay ninguna,
  sobre la más visible. Esc sale (lo hace el navegador).
*/

type Target = { el: () => HTMLElement | null; toggle: () => void; hovered: boolean };
const targets = new Set<Target>();
let listening = false;

function visibleArea(el: HTMLElement) {
  const r = el.getBoundingClientRect();
  const w = Math.max(0, Math.min(r.right, window.innerWidth) - Math.max(r.left, 0));
  const h = Math.max(0, Math.min(r.bottom, window.innerHeight) - Math.max(r.top, 0));
  return w * h;
}

function onKey(e: KeyboardEvent) {
  if (e.key.toLowerCase() !== "f" || e.ctrlKey || e.metaKey || e.altKey || e.repeat || isTyping(e.target) || inGSequence()) return;
  if (document.querySelector("[role=dialog]")) return;
  const all = [...targets].filter((t) => t.el()?.isConnected);
  if (!all.length) return;
  const current = document.fullscreenElement;
  const inside = current && all.find((t) => t.el() === current || current.contains(t.el()!) || t.el()!.contains(current));
  const pick = inside ?? all.find((t) => t.hovered) ?? [...all].sort((a, b) => visibleArea(b.el()!) - visibleArea(a.el()!))[0]!;
  if (!inside && visibleArea(pick.el()!) === 0) return;
  e.preventDefault();
  pick.toggle();
}

export function toggleFullscreen(el: HTMLElement | null) {
  if (document.fullscreenElement) void document.exitFullscreen().catch(() => {});
  else void el?.requestFullscreen().catch(() => {});
}

/**
  Ámbito de pantalla completa: dentro de un marco, los controles del visor (icono y tecla F) amplían
  el marco entero en lugar de su propio lienzo.
*/
export type FullscreenScopeValue = { toggle: () => void; active: boolean };
const Scope = createContext<FullscreenScopeValue | null>(null);
export const FullscreenScope = Scope.Provider;
export function useFullscreenScope() {
  return useContext(Scope);
}

/**
  Registra un elemento para la tecla F. `toggle` sustituye al comportamiento por defecto.
  Con `enabled` a false no se registra (lo hace ya el marco que lo contiene).
*/
export function useFullscreenKey(ref: RefObject<HTMLElement | null>, toggle?: () => void, enabled = true) {
  const toggleRef = useRef(toggle);
  useEffect(() => {
    toggleRef.current = toggle;
  });
  useEffect(() => {
    if (!enabled) return;
    const target: Target = {
      el: () => ref.current,
      toggle: () => (toggleRef.current ? toggleRef.current() : toggleFullscreen(ref.current)),
      hovered: false,
    };
    const el = ref.current;
    const enter = () => (target.hovered = true);
    const leave = () => (target.hovered = false);
    el?.addEventListener("pointerenter", enter);
    el?.addEventListener("pointerleave", leave);
    targets.add(target);
    if (!listening) {
      window.addEventListener("keydown", onKey);
      listening = true;
    }
    return () => {
      el?.removeEventListener("pointerenter", enter);
      el?.removeEventListener("pointerleave", leave);
      targets.delete(target);
      if (!targets.size && listening) {
        window.removeEventListener("keydown", onKey);
        listening = false;
      }
    };
  }, [ref, enabled]);
}

/** true mientras `ref` (o algo dentro de él) está a pantalla completa. */
export function useIsFullscreen(ref: RefObject<HTMLElement | null>) {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const sync = () => setOn(!!document.fullscreenElement && document.fullscreenElement === ref.current);
    document.addEventListener("fullscreenchange", sync);
    return () => document.removeEventListener("fullscreenchange", sync);
  }, [ref]);
  return on;
}

export function FullscreenButton({ active, onClick, className }: { active: boolean; onClick: () => void; className?: string }) {
  const Glyph = active ? Minimize : Maximize;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      aria-keyshortcuts="F"
      title={active ? "Salir de pantalla completa (F o Esc)" : "Pantalla completa (F)"}
      className={cn(
        "inline-flex h-8 shrink-0 items-center gap-2 rounded-[var(--radius-control)] border border-border bg-surface px-2.5 text-[12px] text-muted transition-colors hover:bg-surface-sunken hover:text-text",
        className,
      )}
    >
      <Glyph className="size-3.5" strokeWidth={1.75} aria-hidden />
      {active ? "Salir de pantalla completa" : "Pantalla completa"}
      <span aria-hidden>
        <Kbd>F</Kbd>
      </span>
    </button>
  );
}

/**
  Marco de una vista 3D: cabecera con título y botón, y el contenido, que ocupa toda la pantalla al
  ampliarse. `height` es la altura normal del contenido (clase de Tailwind).
*/
export function FullscreenFrame({
  title,
  description,
  actions,
  height = "h-[600px]",
  className,
  children,
  testId,
}: {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  height?: string;
  className?: string;
  children: ReactNode;
  testId?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const active = useIsFullscreen(ref);
  useFullscreenKey(ref);
  const toggle = () => toggleFullscreen(ref.current);
  return (
    <FullscreenScope value={{ toggle, active }}>
    <section
      ref={ref}
      data-testid={testId}
      data-fullscreen={active || undefined}
      className={cn("flex flex-col gap-3", active && "bg-bg p-4", className)}
    >
      <header className="flex flex-wrap items-end justify-between gap-3">
        {title || description ? (
          <div className="min-w-0">
            {title ? <h2 className="text-lg font-semibold text-strong">{title}</h2> : null}
            {description ? <p className="mt-1 max-w-3xl text-sm text-muted">{description}</p> : null}
          </div>
        ) : (
          <span />
        )}
        <div className="flex flex-wrap items-center gap-2">
          {actions}
          <FullscreenButton active={active} onClick={toggle} />
        </div>
      </header>
      <div className={cn("min-h-0 overflow-hidden rounded-xl border border-border", active ? "flex-1" : height)}>{children}</div>
    </section>
    </FullscreenScope>
  );
}
