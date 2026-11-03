"use client";

import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useState, useSyncExternalStore, type ReactNode } from "react";

import { LOGO_ASSEMBLE_SECONDS, LogoAssemble } from "@/components/brand/logo-assemble";
import { CollabCross, TrLogoAssemble } from "@/components/brand/tr-logo-assemble";
import { EASE_OUT } from "@/components/motion/reveal";
import { Kbd } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";

/*
  La intro se ve cada vez que se carga la portada. Con movimiento reducido no se muestra.
  En el servidor se pinta siempre (cubre la portada desde el primer fotograma); con movimiento
  reducido se quita al hidratar sin animación.
*/

const noSubscribe = () => () => {};
const prefersReducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function useIntro() {
  const skipped = useSyncExternalStore(noSubscribe, prefersReducedMotion, () => false);
  const [finished, setFinished] = useState(false);
  const finish = useCallback(() => setFinished(true), []);
  return { playing: !skipped && !finished, flew: finished, finish };
}

/*
  «TrazIA 3D × Técnicas Reunidas». Se pinta en dos capas con la misma rejilla de huecos fijos:
  la de TrazIA se desmonta al terminar para que su logo viaje a la cabecera (layoutId) y la del
  aspa y Técnicas Reunidas se desvanece. Los huecos vacíos mantienen las dos capas alineadas.
*/
const SLOT = {
  trazia: "w-[clamp(182px,30.8vw,280px)] h-[calc(clamp(128px,22vw,200px)+36px+clamp(26px,4.4vw,40px))]",
  cross: "size-[clamp(22px,3.2vw,32px)]",
  tr: "w-[clamp(182px,30.8vw,280px)] aspect-[452/255]",
};

function Lockup({ trazia, cross, tr }: { trazia?: ReactNode; cross?: ReactNode; tr?: ReactNode }) {
  return (
    <div className="-mt-[6vh] flex flex-col items-center gap-[clamp(18px,4.2vw,56px)] sm:flex-row">
      <div className={cn("flex justify-center", SLOT.trazia)}>{trazia}</div>
      <div className={SLOT.cross}>{cross}</div>
      <div className={SLOT.tr}>{tr}</div>
    </div>
  );
}

const collab = {
  exit: (animated: boolean) => ({ opacity: 0, scale: animated ? 0.98 : 1, transition: { duration: animated ? 0.35 : 0, ease: EASE_OUT } }),
};

const backdrop = {
  exit: (animated: boolean) => ({ opacity: 0, transition: { duration: animated ? 0.6 : 0, ease: EASE_OUT } }),
};

export function IntroOverlay({ playing, flew, onFinish }: { playing: boolean; flew: boolean; onFinish: () => void }) {
  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(onFinish, (LOGO_ASSEMBLE_SECONDS + 0.35) * 1000);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" || e.key === "Enter" || e.key === " ") onFinish();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("keydown", onKey);
    };
  }, [playing, onFinish]);

  return (
    <>
      <AnimatePresence custom={flew}>
        {playing ? (
          <motion.div key="intro-backdrop" custom={flew} variants={backdrop} exit="exit" className="fixed inset-0 z-[60] bg-bg" aria-hidden>
            <div className="landing-paper absolute inset-0 [mask-image:radial-gradient(60%_60%_at_50%_45%,#000,transparent)]" />
          </motion.div>
        ) : null}
        {playing ? (
          <motion.button
            key="intro-skip"
            type="button"
            onClick={onFinish}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { delay: 0.6, duration: 0.3 } }}
            exit={{ opacity: 0, transition: { duration: 0.15 } }}
            className="fixed right-5 bottom-5 z-[62] inline-flex h-9 items-center gap-2 rounded-full border border-border bg-surface/80 px-3.5 text-[13px] text-muted backdrop-blur hover:text-text"
          >
            Saltar intro <Kbd>Esc</Kbd>
          </motion.button>
        ) : null}
        {playing ? (
          <motion.div
            key="intro-collab"
            custom={flew}
            variants={collab}
            exit="exit"
            className="pointer-events-none fixed inset-0 z-[61] flex items-center justify-center"
            aria-hidden
          >
            <Lockup cross={<CollabCross className="size-full" />} tr={<TrLogoAssemble />} />
          </motion.div>
        ) : null}
      </AnimatePresence>
      {playing ? (
        <div className="fixed inset-0 z-[61] flex cursor-pointer items-center justify-center" onClick={onFinish} aria-hidden>
          <Lockup trazia={<LogoAssemble markLayoutId="brand-mark" wordLayoutId="brand-word" />} />
        </div>
      ) : null}
    </>
  );
}
