"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Check, LoaderCircle, RotateCcw, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactElement } from "react";

import { EASE_OUT } from "@/components/motion/reveal";
import { Icon } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { startDemoSession } from "@/lib/session";

/*
  «Ver demo»: recorre las etapas reales del producto sobre V-101 (datos sintéticos).
  Los tiempos son de la animación, no medidos; por eso no se muestran.
*/

const STAGES = [
  { title: "Ingesta del PDF", detail: "Plano GA de V-101, revisión B" },
  { title: "Lectura con A, B, C y D", detail: "22 campos con su valor, unidad, fuente y confianza" },
  { title: "Reconciliación", detail: "Por campo, gana el valor con mejor evidencia" },
  { title: "Modelo IFC", detail: "Geometría con GUID estable por ID, en borrador" },
  { title: "Cambios de A a B", detail: "8 cambios, 7 de geometría: altura 6000 → 6500 mm" },
];

const STEP_MS = 900;

function Stages() {
  const [done, setDone] = useState(0);

  useEffect(() => {
    if (done >= STAGES.length) return;
    const t = window.setTimeout(() => setDone(done + 1), STEP_MS);
    return () => window.clearTimeout(t);
  }, [done]);

  return (
    <ol className="relative mt-5 space-y-1" aria-live="polite">
      {STAGES.map((s, i) => {
        const state = i < done ? "done" : i === done ? "running" : "pending";
        return (
          <li key={s.title} className="relative flex gap-3 rounded-[10px] px-2 py-2.5">
            {i < STAGES.length - 1 ? (
              <span aria-hidden className="absolute top-9 bottom-[-10px] left-[19px] w-px overflow-hidden bg-border">
                <motion.span
                  className="block h-full w-full origin-top bg-accent"
                  initial={{ scaleY: 0 }}
                  animate={{ scaleY: state === "done" ? 1 : 0 }}
                  transition={{ duration: 0.35, ease: EASE_OUT }}
                />
              </span>
            ) : null}
            <span
              className={cn(
                "relative flex size-6 shrink-0 items-center justify-center rounded-full border transition-colors duration-300",
                state === "done" && "border-accent bg-accent text-accent-contrast",
                state === "running" && "border-accent text-accent",
                state === "pending" && "border-border-strong text-faint",
              )}
            >
              <AnimatePresence mode="wait" initial={false}>
                {state === "done" ? (
                  <motion.span key="ok" initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: "spring", duration: 0.35, bounce: 0.3 }}>
                    <Check className="size-3.5" strokeWidth={3} aria-hidden />
                  </motion.span>
                ) : state === "running" ? (
                  <motion.span key="run" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    <LoaderCircle className="size-3.5 animate-spin" aria-hidden />
                  </motion.span>
                ) : (
                  <span key="wait" className="font-mono text-[10px]">
                    {i + 1}
                  </span>
                )}
              </AnimatePresence>
            </span>
            <span className="min-w-0">
              <span className={cn("block text-[14px] transition-colors duration-300", state === "pending" ? "text-muted" : "text-strong")}>{s.title}</span>
              <span className="block text-[13px] text-muted">{s.detail}</span>
            </span>
            <span className="sr-only">{state === "done" ? "hecho" : state === "running" ? "en curso" : "pendiente"}</span>
          </li>
        );
      })}
    </ol>
  );
}

export function DemoDialog({ children }: { children: ReactElement }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [run, setRun] = useState(0);

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (o) setRun((r) => r + 1);
      }}
    >
      <Dialog.Trigger asChild>{children}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="cmd-overlay fixed inset-0 z-50 bg-[var(--scrim)] backdrop-blur-[2px]" />
        <Dialog.Content className="cmd-content fixed top-1/2 left-1/2 z-50 w-[min(520px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 rounded-[16px] border border-border bg-surface-raised p-5 shadow-[var(--shadow-pop)] sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="text-[16px] font-semibold text-strong">Del plano al modelo, paso a paso</Dialog.Title>
              <Dialog.Description className="mt-1 text-[13px] text-muted">
                El recorrido que hace TrazIA-3D con el recipiente V-101 de la demo. Datos sintéticos.
              </Dialog.Description>
            </div>
            <Dialog.Close className="rounded-[8px] p-1.5 text-muted hover:bg-surface-sunken hover:text-text" aria-label="Cerrar">
              <Icon icon={X} />
            </Dialog.Close>
          </div>
          <Stages key={run} />
          <div className="mt-5 flex items-center justify-between gap-3 border-t border-border pt-4">
            <button
              type="button"
              onClick={() => setRun((r) => r + 1)}
              className="inline-flex h-9 items-center gap-2 rounded-[10px] px-3 text-[13px] text-muted transition-colors hover:bg-surface-sunken hover:text-text"
            >
              <Icon icon={RotateCcw} size={15} /> Repetir
            </button>
            <button
              type="button"
              onClick={() => {
                startDemoSession("demo");
                router.push("/proyecto");
              }}
              className="inline-flex h-9 items-center rounded-[10px] bg-accent px-4 text-[13px] font-semibold text-accent-contrast transition-transform duration-[160ms] active:scale-[0.98]"
            >
              Abrir la demo
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
