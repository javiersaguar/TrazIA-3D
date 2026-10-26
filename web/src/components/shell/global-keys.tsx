"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { NAV_ITEMS } from "@/lib/nav";
import { useUi } from "@/stores/ui";

export function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

/** Atajos globales: Ctrl+K, ?, [ y la secuencia G + número. */
export function GlobalKeys() {
  const router = useRouter();
  const pendingG = useRef<number | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const ui = useUi.getState();
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        ui.setCommandOpen(!ui.commandOpen);
        return;
      }
      if (e.ctrlKey || e.metaKey || e.altKey || isTyping(e.target)) return;
      if (ui.commandOpen || ui.shortcutsOpen) return;

      if (e.key === "?") {
        e.preventDefault();
        ui.setShortcutsOpen(true);
        return;
      }
      if (e.key === "[") {
        ui.toggleSidebar();
        return;
      }
      if (e.key.toLowerCase() === "g") {
        pendingG.current = window.setTimeout(() => (pendingG.current = null), 900);
        return;
      }
      if (pendingG.current != null) {
        const item = NAV_ITEMS.find((i) => i.shortcut === e.key);
        window.clearTimeout(pendingG.current);
        pendingG.current = null;
        if (item) router.push(item.href);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);

  return null;
}
