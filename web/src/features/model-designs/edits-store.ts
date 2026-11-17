"use client";

import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

import type { DesignEdits } from "./parametric";

/* Cambios de cada diseño, guardados en este navegador. localStorage puede fallar (modo privado). */
const storage: StateStorage = {
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

type Dimension = "width" | "height" | "depth";
type EditsState = {
  edits: Record<string, DesignEdits>;
  setDimension(tag: string, dimension: Dimension, value: number | undefined): void;
  setPart(tag: string, part: string, patch: { scale?: number; hidden?: boolean }): void;
  reset(tag: string): void;
};

export const useDesignEdits = create<EditsState>()(
  persist(
    (set) => ({
      edits: {},
      setDimension: (tag, dimension, value) =>
        set((state) => {
          const current = state.edits[tag] ?? {};
          return { edits: { ...state.edits, [tag]: { ...current, size: { ...current.size, [dimension]: value } } } };
        }),
      setPart: (tag, part, patch) =>
        set((state) => {
          const current = state.edits[tag] ?? {};
          const parts = { ...current.parts, [part]: { ...current.parts?.[part], ...patch } };
          return { edits: { ...state.edits, [tag]: { ...current, parts } } };
        }),
      reset: (tag) =>
        set((state) => {
          const edits = { ...state.edits };
          delete edits[tag];
          return { edits };
        }),
    }),
    { name: "trazia-design-edits", storage: createJSONStorage(() => storage), version: 1 },
  ),
);
