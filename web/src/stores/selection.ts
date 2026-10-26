"use client";

import { create } from "zustand";

/**
 * Selección compartida entre el plano PDF, el visor 3D y la lista de campos.
 * Los ids son semánticos y estables: "shell", "head-top", "head-bottom", "skirt", "nozzle:N1"…
 * (correspondencia con el IFC en src/lib/mock/fields.ts).
 * `selectedPath` afina la selección a un campo concreto del contrato ("nozzles.N3.elevation").
 */
type SelectionState = {
  selectedId: string | null;
  hoveredId: string | null;
  selectedPath: string | null;
  setSelected: (id: string | null, path?: string | null) => void;
  setHovered: (id: string | null) => void;
};

export const useSelection = create<SelectionState>()((set) => ({
  selectedId: null,
  hoveredId: null,
  selectedPath: null,
  setSelected: (id, path = null) => set({ selectedId: id, selectedPath: path }),
  setHovered: (id) => set({ hoveredId: id }),
}));
