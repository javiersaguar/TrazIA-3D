import { Logo } from "@/components/brand/logo";

const AUTHORS = ["Javier Saguar Antona", "Iria Lozano Carrasco", "Miguel Vera del Castillo", "Alejandro Cuevas Cid"];

export function LandingFooter({ onStart }: { onStart: () => void }) {
  return (
    <footer id="equipo" className="scroll-mt-20 border-t border-border">
      <div className="mx-auto grid w-full max-w-[1240px] gap-14 px-5 py-20 md:px-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <div>
          <p className="landing-display max-w-[16ch] text-[clamp(30px,3.6vw,48px)] leading-[1.02] text-strong">Abre la demo con el recipiente V-101.</p>
          <button
            type="button"
            onClick={onStart}
            className="mt-8 inline-flex h-11 items-center rounded-[10px] bg-accent px-5 text-[15px] font-semibold text-accent-contrast transition-transform duration-[160ms] ease-[var(--ease-out)] active:scale-[0.98]"
          >
            Iniciar
          </button>
        </div>
        <div>
          <h2 className="text-[13px] text-faint">Equipo</h2>
          <ul className="mt-3 space-y-2 text-[15px] text-text">
            {AUTHORS.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
          <p className="mt-8 max-w-[44ch] text-[13px] leading-relaxed text-muted">
            Hecho para el reto GA2MODEL de Técnicas Reunidas en IndesIAhack 2026. Los planos y cifras de la demo son
            sintéticos.
          </p>
        </div>
      </div>
      <div className="mx-auto flex w-full max-w-[1240px] items-center justify-between gap-4 border-t border-border px-5 py-6 md:px-8">
        <Logo className="h-9 w-auto" />
        <span className="text-[12px] text-faint">2026</span>
      </div>
    </footer>
  );
}
