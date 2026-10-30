"use client";

import { motion, type Variants } from "motion/react";
import Link from "next/link";
import { useCallback, type ComponentProps } from "react";

import { LogoMark, LogoWordmark } from "@/components/brand/logo";
import { EASE_IN_OUT, EASE_OUT } from "@/components/motion/reveal";
import { Spotlight } from "@/components/motion/spotlight";
import { LiveDot } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { DemoDialog } from "./demo-dialog";
import { DrawingSheet } from "./drawing-sheet";
import { HologramSection } from "./hologram-section";
import { HowItWorks } from "./how-it-works";
import { IntroOverlay, useIntro } from "./intro";
import { LandingFooter } from "./landing-footer";
import { LoginCard } from "./login-card";
import { RotatingLine } from "./rotating-line";
import { Strategies } from "./strategies";

const LINKS = [
  { href: "#como-funciona", label: "Cómo funciona" },
  { href: "#estrategias", label: "Estrategias" },
  { href: "#equipo", label: "Equipo" },
];

const hero: Variants = {
  hidden: {},
  shown: { transition: { staggerChildren: 0.07, delayChildren: 0.15 } },
};
const rise: Variants = {
  hidden: { opacity: 0, y: 16 },
  shown: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE_OUT } },
};

/** Lleva al formulario de acceso y pone el foco en el usuario. */
function focusLogin() {
  const input = document.getElementById("acceso-usuario");
  input?.scrollIntoView({ behavior: "smooth", block: "center" });
  window.setTimeout(() => input?.focus({ preventScroll: true }), 350);
}

function LandingHeader({ flew }: { flew: boolean }) {
  const flight = { duration: 0.8, ease: EASE_IN_OUT };
  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-bg/75 backdrop-blur-md">
      <div className="mx-auto flex h-16 w-full max-w-[1240px] items-center gap-6 px-5 md:px-8">
        <Link href="/" aria-label="TrazIA 3D, inicio" className="flex items-center gap-3 rounded-[8px]">
          <motion.span key={flew ? "mark-flown" : "mark"} layoutId={flew ? "brand-mark" : undefined} transition={flight} className="block size-9">
            <LogoMark className="size-9" />
          </motion.span>
          <motion.span key={flew ? "word-flown" : "word"} layoutId={flew ? "brand-word" : undefined} transition={flight} className="block h-[15px]">
            <LogoWordmark className="h-[15px] w-auto" />
          </motion.span>
        </Link>
        <nav aria-label="Secciones" className="ml-auto hidden items-center gap-1 md:flex">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className="rounded-[8px] px-3 py-2 text-[14px] text-muted transition-colors duration-[var(--dur-fast)] hover:text-text">
              {l.label}
            </a>
          ))}
        </nav>
        <button
          type="button"
          onClick={focusLogin}
          className="ml-auto inline-flex h-9 items-center rounded-[10px] border border-border-strong bg-surface-raised px-3.5 text-[14px] text-text transition-[transform,border-color] duration-[160ms] hover:border-accent/60 active:scale-[0.97] md:ml-2"
        >
          Iniciar sesión
        </button>
      </div>
    </header>
  );
}

function BracketButton({ className, ...props }: ComponentProps<"button">) {
  return (
    <button
      type="button"
      className={cn(
        "group inline-flex h-11 items-center gap-3 rounded-[10px] px-2 text-[14.5px] text-text transition-transform duration-[160ms] active:scale-[0.98]",
        className,
      )}
      {...props}
    >
      <span aria-hidden className="font-mono text-[17px] text-accent transition-transform duration-200 ease-[var(--ease-out)] group-hover:-translate-x-1">
        [
      </span>
      Ver el recorrido de la demo
      <span aria-hidden className="font-mono text-[17px] text-accent transition-transform duration-200 ease-[var(--ease-out)] group-hover:translate-x-1">
        ]
      </span>
    </button>
  );
}

export function LandingPage({ fontClassName }: { fontClassName?: string }) {
  const { playing, flew, finish } = useIntro();
  const play = !playing;
  const start = useCallback(() => focusLogin(), []);

  return (
    <div className={cn("min-h-dvh bg-bg text-text", fontClassName)}>
      <IntroOverlay playing={playing} flew={flew} onFinish={finish} />
      <LandingHeader flew={flew} />

      <main>
        <section aria-labelledby="hero-titulo" className="relative overflow-hidden">
          <Spotlight size={680} />
          <div
            aria-hidden
            className="landing-paper pointer-events-none absolute inset-0 opacity-70 [mask-image:radial-gradient(65%_70%_at_72%_35%,#000,transparent)]"
          />
          <div className="relative mx-auto grid w-full max-w-[1240px] gap-12 px-5 pt-10 pb-20 md:px-8 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-12 lg:pt-14 lg:pb-28">
            <motion.div variants={hero} initial="hidden" animate={play ? "shown" : "hidden"} className="flex min-w-0 flex-col">
              <motion.p variants={rise} className="flex items-center gap-2.5 text-[13px] text-muted">
                <LiveDot /> Reto GA2MODEL de Técnicas Reunidas
              </motion.p>
              <motion.h1 variants={rise} id="hero-titulo" className="landing-display mt-5 text-[clamp(46px,6.4vw,88px)] leading-[0.94] text-strong">
                Del plano al modelo 3D,
                <RotatingLine play={play} className="mt-3 block text-[clamp(22px,2.5vw,34px)] leading-tight text-muted" />
              </motion.h1>
              <motion.p variants={rise} className="mt-6 max-w-[50ch] text-[16px] leading-relaxed text-muted">
                TrazIA-3D lee los planos de disposición general de recipientes, genera el modelo IFC y guarda de qué parte
                del plano sale cada dato. Cuando llega una revisión, enseña qué ha cambiado.
              </motion.p>
              <motion.div variants={rise} className="mt-8 w-full max-w-[440px]">
                <LoginCard />
              </motion.div>
              <motion.div variants={rise} className="mt-3">
                <DemoDialog>
                  <BracketButton />
                </DemoDialog>
              </motion.div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 18 }}
              animate={play ? { opacity: 1, y: 0 } : { opacity: 0, y: 18 }}
              transition={{ duration: 0.8, delay: 0.1, ease: EASE_OUT }}
              className="min-w-0 lg:pt-2"
            >
              <DrawingSheet play={play} className="h-[clamp(460px,74vh,700px)]" />
            </motion.div>
          </div>
        </section>

        <HologramSection />
        <HowItWorks />
        <Strategies />
      </main>

      <LandingFooter onStart={start} />
    </div>
  );
}
