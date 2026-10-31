"use client";

import { create } from "zustand";
import type { RevisionId } from "@/lib/mock/api";
import { useUi } from "@/stores/ui";
import { ActiveReviewClock } from "./active-clock";

type Session = { id: string; actor: string; revision: RevisionId; clock: ActiveReviewClock };
export const useManualReview = create<{ session: Session | null; setSession: (session: Session | null) => void; busy: boolean; setBusy: (busy: boolean) => void }>((set) => ({
  session: null, setSession: (session) => set({ session }), busy: false, setBusy: (busy) => set({ busy }),
}));

export function reviewTiming(rev: RevisionId) {
  const session = useManualReview.getState().session;
  if (!session || session.revision !== rev) return { actor: "Revisor local" };
  const seconds = session.clock.unaccounted();
  session.clock.block();
  return { actor: session.actor, seconds, reviewSessionId: session.id };
}

export function settleTiming(seconds: number | undefined, saved: boolean) {
  const session = useManualReview.getState().session;
  if (session) {
    if (saved && seconds !== undefined) session.clock.commit(seconds);
    session.clock.unblock();
    if (session.revision === useUi.getState().revision && document.visibilityState === "visible" && document.hasFocus()) session.clock.resume();
  }
}
