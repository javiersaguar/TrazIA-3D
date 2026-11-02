"use client";
import { useSyncExternalStore } from "react";
const subscribe = (listener: () => void) => {
 const query=window.matchMedia("(prefers-reduced-motion: reduce)");
 query.addEventListener("change",listener);
 return ()=>query.removeEventListener("change",listener);
};
const snapshot=()=>window.matchMedia("(prefers-reduced-motion: reduce)").matches;
/** Mismo primer render en servidor e hidratación; después refleja el ajuste del dispositivo. */
export function useMotionPreference(){ return useSyncExternalStore(subscribe,snapshot,()=>false); }
