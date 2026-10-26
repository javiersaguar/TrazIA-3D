"use client";

import { create } from "zustand";
import type { RevisionId } from "@/lib/mock/api";
import type { FieldStatus } from "@/lib/mock/fields";

/** Registro de acciones de revisión de la sesión: alimenta "Deshacer" y la serie de progreso. */
export type ReviewAction = {
  id: string;
  at: number;
  rev: RevisionId;
  path: string;
  label: string;
  from: { status: FieldStatus; correctedValue?: number | string };
  to: { status: FieldStatus; correctedValue?: number | string };
  /** Campos revisados tras la acción (para la micrográfica). */
  reviewedAfter: number;
};

type ReviewLogState = {
  actions: ReviewAction[];
  push: (a: ReviewAction) => void;
  remove: (id: string) => void;
};

export const useReviewLog = create<ReviewLogState>()((set) => ({
  actions: [],
  push: (a) => set((s) => ({ actions: [...s.actions, a] })),
  remove: (id) => set((s) => ({ actions: s.actions.filter((a) => a.id !== id) })),
}));
