"use client";

import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

import { LOGO_ASSEMBLE_SECONDS, LogoAssemble } from "@/components/brand/logo-assemble";
import { EASE_OUT } from "@/components/motion/reveal";
import { Kbd } from "@/components/ui/primitives";

/*
  La intro se ve una vez por sesión de navegador. Con movimiento reducido no se muestra.
  En el servidor se pinta siempre (cubre la portada desde el primer fotograma); si en el cliente
  ya se vio, se quita al hidratar sin animación.
*/

const KEY = "trazia.intro";
const noSubscribe = () => () => {};

function introAlreadyDone(): boolean {
  try {
    if (window.sessionStorage.getItem(KEY)) return true;
  } catch {
    /* sin almacenamiento: se decide solo por el movimiento reducido */
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function useIntro() {
  const skipped = useSyncExternalStore(noSubscribe, introAlreadyDone, () => false);
  const [finished, setFinished] = useState(false);
  const finish = useCallback(() => {
    try {
      window.sessionStorage.setItem(KEY, "1");
    } catch {
      /* nada */
    }
    setFinished(true);
  }, []);
  return { playing: !skipped && !finished, flew: finished, finish };
}

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
      </AnimatePresence>
      {playing ? (
        <div className="fixed inset-0 z-[61] flex cursor-pointer items-center justify-center" onClick={onFinish} aria-hidden>
          <LogoAssemble markLayoutId="brand-mark" wordLayoutId="brand-word" className="-mt-[6vh]" />
        </div>
      ) : null}
    </>
  );
}
