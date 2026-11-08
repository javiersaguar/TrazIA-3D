"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { SetStateAction } from "react";
import { API_BASE } from "../../lib/api/config";
import type { DrawingFiles, IntentDraft, PartChange, Proposal } from "./api";
import type { Drafts } from "./form";

export type PartForm = {
  action: "add" | "remove"; collection: PartChange["collection"];
  id: string; values: Record<string, string>;
};
export const EMPTY_PART_FORM: PartForm = { action: "add", collection: "nozzles", id: "", values: {} };

type EditorDraft = {
  tag: string; projectId: string; label: string;
  drafts: Drafts; partChanges: PartChange[]; partForm: PartForm;
  detailLevel: 2 | 3 | undefined; reason: string; actor: string | null;
  request: string; useModel: boolean; intent: IntentDraft | null;
  proposal: Proposal | null; signature: string; side: "antes" | "despues";
  choice: { group: string; selection: string | null } | null;
  drawing: DrawingFiles | null;
  pendingJob: {id:string;kind:"preview"|"drawing";revisionId:string} | null;
};
const EMPTY: EditorDraft = {
  tag: "V-101", projectId: "DEMO-PLANT", label: "B", drafts: {}, partChanges: [],
  partForm: EMPTY_PART_FORM, detailLevel: undefined, reason: "", actor: null,
  request: "", useModel: false, intent: null, proposal: null, signature: "", side: "despues",
  choice: null, drawing: null, pendingJob: null,
};
type Cache = {
  entries: Record<string, EditorDraft>;
  update: <K extends keyof EditorDraft>(key: string, field: K, value: SetStateAction<EditorDraft[K]>) => void;
};

/** Sesión del navegador, aislada por API/proyecto/equipo/revisión; no publica ni confirma. */
export const useDraftCache = create<Cache>()(persist((set) => ({
  entries: {},
  update: (key, field, value) => set(state => {
    const previous = state.entries[key] ?? EMPTY;
    const next = typeof value === "function" ? value(previous[field]) : value;
    return { entries: { ...state.entries, [key]: { ...previous, [field]: next } } };
  }),
}), {
  name: "trazia-design-drafts-v1",
  storage: createJSONStorage(() => ({
    getItem: key => { try { return sessionStorage.getItem(key); } catch { return null; } },
    setItem: (key, value) => { try { sessionStorage.setItem(key, value); } catch { /* memoria */ } },
    removeItem: key => { try { sessionStorage.removeItem(key); } catch { /* memoria */ } },
  })),
  partialize: state => ({ entries: state.entries }),
}));

export function draftKey(project: string, tag: string, revision: string) {
  return JSON.stringify([API_BASE, project, tag, revision]);
}
export function useDraftField<K extends keyof EditorDraft>(key: string, field: K) {
  const value = useDraftCache(state => (state.entries[key] ?? EMPTY)[field]);
  const update = useDraftCache(state => state.update);
  return [value, (value: SetStateAction<EditorDraft[K]>) => update(key, field, value)] as const;
}
