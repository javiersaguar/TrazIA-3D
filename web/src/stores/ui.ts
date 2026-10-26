"use client";

import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";
import type { RevisionId } from "@/lib/mock/api";

/* localStorage puede no existir o lanzar (modo privado): nunca debe romper la UI. */
const safeStorage: StateStorage = {
  getItem: (name) => {
    try {
      return window.localStorage.getItem(name);
    } catch {
      return null;
    }
  },
  setItem: (name, value) => {
    try {
      window.localStorage.setItem(name, value);
    } catch {
      /* sin persistencia */
    }
  },
  removeItem: (name) => {
    try {
      window.localStorage.removeItem(name);
    } catch {
      /* sin persistencia */
    }
  },
};

type UiState = {
  sidebarCollapsed: boolean;
  demoCardHidden: boolean;
  revision: RevisionId;
  commandOpen: boolean;
  shortcutsOpen: boolean;
  copilotOpen: boolean;
  toggleSidebar: () => void;
  hideDemoCard: (hidden: boolean) => void;
  setRevision: (rev: RevisionId) => void;
  setCommandOpen: (open: boolean) => void;
  setShortcutsOpen: (open: boolean) => void;
  setCopilotOpen: (open: boolean) => void;
};

export const useUi = create<UiState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      demoCardHidden: false,
      revision: "A",
      commandOpen: false,
      shortcutsOpen: false,
      copilotOpen: false,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      hideDemoCard: (hidden) => set({ demoCardHidden: hidden }),
      setRevision: (revision) => set({ revision }),
      setCommandOpen: (commandOpen) => set({ commandOpen }),
      setShortcutsOpen: (shortcutsOpen) => set({ shortcutsOpen }),
      setCopilotOpen: (copilotOpen) => set({ copilotOpen }),
    }),
    {
      name: "trazia-ui",
      storage: createJSONStorage(() => safeStorage),
      // Solo preferencias por usuario; los diálogos no se recuerdan
      partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed, demoCardHidden: s.demoCardHidden, revision: s.revision }),
    },
  ),
);
