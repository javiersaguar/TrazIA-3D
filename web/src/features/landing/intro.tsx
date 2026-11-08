"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { LOGO_ASSEMBLE_SECONDS, LogoAssemble } from "@/components/brand/logo-assemble";
import { CollabCross, TrLogoAssemble } from "@/components/brand/tr-logo-assemble";
import { EASE_IN_OUT } from "@/components/motion/reveal";
import { Kbd } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { useMotionPreference } from "@/lib/use-motion-preference";
import styles from "./intro.module.css";

export type IntroPhase = "assembling" | "flying" | "ready";
export const INTRO_FLIGHT_MS = 800;

/** La intro se repite al cargar; movimiento reducido salta directamente al contenido. */
export function useIntro() {
  const reduced = useMotionPreference();
  const [state, setState] = useState<IntroPhase>("assembling");
  if (reduced && state !== "ready") setState("ready");
  const phase = reduced ? "ready" : state;
  const fly = useCallback(() => setState(old => old === "assembling" ? "flying" : old), []);
  const finish = useCallback(() => setState("ready"), []);
  return { phase, fly, finish };
}

const SLOT = {
  trazia: "w-[clamp(182px,30.8vw,280px)] h-[calc(clamp(128px,22vw,200px)+36px+clamp(26px,4.4vw,40px))]",
  cross: "size-[clamp(22px,3.2vw,32px)]",
  tr: "w-[clamp(182px,30.8vw,280px)] aspect-[452/255]",
};
function Lockup({ trazia, cross, tr }: { trazia?: ReactNode; cross?: ReactNode; tr?: ReactNode }) {
  return <div className="-mt-[6vh] flex flex-col items-center gap-[clamp(18px,4.2vw,56px)] sm:flex-row">
    <div className={cn("flex justify-center",SLOT.trazia)}>{trazia}</div>
    <div className={SLOT.cross}>{cross}</div><div className={SLOT.tr}>{tr}</div>
  </div>;
}

/** Dos capas compositoras: se miden una vez y se trasladan sin proyección de layout por frame. */
export function IntroOverlay({ phase, onFly, onReady }: { phase: IntroPhase; onFly:()=>void; onReady:()=>void }) {
  const root = useRef<HTMLDivElement>(null);
  const [earlySkip, setEarlySkip] = useState(false);
  const skip = useCallback(() => { setEarlySkip(true); onFly(); }, [onFly]);
  useEffect(() => {
    if (phase !== "assembling") return;
    const timer = window.setTimeout(onFly,(LOGO_ASSEMBLE_SECONDS+.35)*1000);
    const key = (event: KeyboardEvent) => {
      if (["Escape","Enter"," "].includes(event.key)) { event.preventDefault(); skip(); }
    };
    window.addEventListener("keydown",key);
    return () => { clearTimeout(timer); window.removeEventListener("keydown",key); };
  },[phase,onFly,skip]);

  useLayoutEffect(() => {
    if (phase !== "flying") return;
    let live = true;
    const animations: Animation[] = [];
    const complete = () => { if(live) onReady(); };
    // Leer todos los rectángulos antes de escribir transformaciones: una sola fase de layout.
    const layers = ["mark","word"].map(part => {
      const source = root.current?.querySelector<HTMLElement>(`[data-intro-logo-part="${part}"]`);
      const target = document.querySelector<HTMLElement>(`[data-intro-target="${part}"]`);
      return source && target ? {source,from:source.getBoundingClientRect(),to:target.getBoundingClientRect()} : null;
    });
    try {
      for (const layer of layers) {
        if (!layer || !layer.from.width || !layer.from.height) continue;
        const {source,from,to} = layer;
        animations.push(source.animate([
          {transform:"translate3d(0,0,0) scale(1,1)"},
          {transform:`translate3d(${to.x-from.x}px,${to.y-from.y}px,0) scale(${to.width/from.width},${to.height/from.height})`},
        ],{duration:INTRO_FLIGHT_MS,easing:`cubic-bezier(${EASE_IN_OUT.join(",")})`,fill:"forwards"}));
      }
      void Promise.all(animations.map(animation=>animation.finished)).then(complete,()=>{});
    } catch { complete(); }
    const timer = window.setTimeout(complete,INTRO_FLIGHT_MS+120);
    window.addEventListener("resize",complete,{once:true});
    return () => { live=false;clearTimeout(timer);window.removeEventListener("resize",complete);animations.forEach(animation=>animation.cancel()); };
  },[phase,onReady]);

  if(phase === "ready") return null;
  return <div ref={root} className={styles.root} data-phase={phase} data-early-skip={earlySkip} onClick={phase==="assembling"?skip:undefined}>
    <div className={cn("fixed inset-0 z-[60] bg-bg",styles.backdrop)} aria-hidden>
      <div className="landing-paper absolute inset-0 [mask-image:radial-gradient(60%_60%_at_50%_45%,#000,transparent)]" />
    </div>
    <div className={cn("pointer-events-none fixed inset-0 z-[61] flex items-center justify-center",styles.collab)} aria-hidden>
      <Lockup cross={<CollabCross className="size-full" />} tr={<TrLogoAssemble />} />
    </div>
    <div className="pointer-events-none fixed inset-0 z-[61] flex items-center justify-center" aria-hidden>
      <Lockup trazia={<LogoAssemble />} />
    </div>
    {phase==="assembling" && <button type="button" onClick={skip}
      className={cn("fixed right-5 bottom-5 z-[62] inline-flex h-9 items-center gap-2 rounded-full border border-border bg-surface/80 px-3.5 text-[13px] text-muted backdrop-blur hover:text-text",styles.skip)}>
      Saltar intro <Kbd>Esc</Kbd>
    </button>}
  </div>;
}
