"use client";

import { X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { usePathname, useRouter } from "next/navigation";
import { useState, useSyncExternalStore } from "react";

import { EASE_OUT } from "@/components/motion/reveal";
import { Icon } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";

/*
  Recorrido guiado tras el primer acceso: documento → evidencia → modelo → cambios.
  Se marca como pendiente al iniciar sesión y se da por visto (localStorage) al terminarlo o
  saltarlo, así que no vuelve a salir en este navegador.
*/

const PENDING = "trazia.tour";
const SEEN = "trazia.tour.visto";
const listeners = new Set<() => void>();

const STEPS = [
  { href: "/proyecto", title: "El proyecto", text: "Aquí están los equipos de la planta, su estado y lo que queda por revisar." },
  { href: "/revision", title: "La evidencia de cada campo", text: "Cada valor enseña la zona del plano de la que sale. Lo aceptas o lo corriges con el teclado." },
  { href: "/modelo", title: "El modelo 3D", text: "La geometría sale del IFC que se genera con los campos revisados." },
  { href: "/cambios", title: "Los cambios entre revisiones", text: "Compara A y B: qué cambió, cuánto y dónde, en la lista y en 3D." },
];

function read(): boolean {
  try {
    return window.sessionStorage.getItem(PENDING) === "1" && !window.localStorage.getItem(SEEN);
  } catch {
    return false;
  }
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

/** Lo llama el acceso de la portada: el recorrido saldrá si este navegador aún no lo ha visto. */
export function queueGuidedTour() {
  try {
    window.sessionStorage.setItem(PENDING, "1");
  } catch {
    /* sin almacenamiento: no hay recorrido */
  }
  listeners.forEach((l) => l());
}

function closeTour() {
  try {
    window.sessionStorage.removeItem(PENDING);
    window.localStorage.setItem(SEEN, "1");
  } catch {
    /* nada */
  }
  listeners.forEach((l) => l());
}

export function GuidedTour() {
  const pending = useSyncExternalStore(subscribe, read, () => false);
  const router = useRouter();
  const pathname = usePathname();
  const [step, setStep] = useState(0);
  const current = STEPS[step]!;
  const last = step === STEPS.length - 1;
  const onPage = pathname === current.href;

  function next() {
    if (last) return closeTour();
    const to = STEPS[step + 1]!;
    setStep(step + 1);
    router.push(to.href);
  }

  return (
    <AnimatePresence>
      {pending ? (
        <motion.aside
          key="tour"
          aria-label="Recorrido guiado"
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 8, transition: { duration: 0.15 } }}
          transition={{ duration: 0.32, delay: 0.5, ease: EASE_OUT }}
          className="fixed right-5 bottom-[88px] z-40 w-[min(340px,calc(100vw-40px))] rounded-[14px] border border-border-strong bg-surface-raised p-4 shadow-[var(--shadow-pop)]"
        >
          <div className="flex items-center gap-2">
            <ol className="flex gap-1" aria-label={`Paso ${step + 1} de ${STEPS.length}`}>
              {STEPS.map((s, i) => (
                <li key={s.href} className={cn("h-1 w-6 rounded-full transition-colors duration-300", i <= step ? "bg-accent" : "bg-border-strong")} />
              ))}
            </ol>
            <span className="text-[12px] text-faint">
              {step + 1} de {STEPS.length}
            </span>
            <button type="button" onClick={closeTour} aria-label="Cerrar el recorrido" className="ml-auto rounded-[6px] p-1 text-faint hover:bg-surface-sunken hover:text-text">
              <Icon icon={X} size={15} />
            </button>
          </div>
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={step}
              initial={{ opacity: 0, filter: "blur(2px)" }}
              animate={{ opacity: 1, filter: "blur(0px)" }}
              exit={{ opacity: 0, filter: "blur(2px)" }}
              transition={{ duration: 0.16 }}
              aria-live="polite"
            >
              <h2 className="mt-3 text-[14px] font-semibold text-strong">{current.title}</h2>
              <p className="mt-1 text-[13px] leading-relaxed text-muted">{current.text}</p>
            </motion.div>
          </AnimatePresence>
          <div className="mt-4 flex items-center justify-between">
            <button type="button" onClick={closeTour} className="rounded-[8px] px-2 py-1.5 text-[13px] text-muted hover:text-text">
              Saltar
            </button>
            <div className="flex gap-2">
              {!onPage ? (
                <button
                  type="button"
                  onClick={() => router.push(current.href)}
                  className="h-8 rounded-[8px] border border-border px-3 text-[13px] text-text hover:bg-surface-sunken"
                >
                  Ir aquí
                </button>
              ) : null}
              <button
                type="button"
                onClick={next}
                className="h-8 rounded-[8px] bg-accent px-3 text-[13px] font-semibold text-accent-contrast transition-transform duration-[160ms] active:scale-[0.97]"
              >
                {last ? "Terminar" : "Siguiente"}
              </button>
            </div>
          </div>
        </motion.aside>
      ) : null}
    </AnimatePresence>
  );
}
