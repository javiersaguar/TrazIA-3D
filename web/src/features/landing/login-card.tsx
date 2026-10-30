"use client";

import { Eye, EyeOff, LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Icon } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { startDemoSession } from "@/lib/session";
import { queueGuidedTour } from "@/features/tour/guided-tour";

const field =
  "h-11 w-full rounded-[10px] border border-border bg-surface-sunken px-3.5 text-[15px] text-text placeholder:text-faint " +
  "transition-[border-color,box-shadow] duration-[var(--dur-base)] outline-none " +
  "focus-visible:border-accent focus-visible:shadow-[0_0_0_3px_var(--accent-soft)]";

/**
 * Acceso de la demo. Todavía no hay base de datos: «Iniciar» entra siempre y solo se recuerda el
 * nombre escrito (nunca la contraseña) para saludar en la aplicación.
 */
export function LoginCard({ className }: { className?: string }) {
  const router = useRouter();
  const [user, setUser] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    startDemoSession(user);
    queueGuidedTour();
    setPassword("");
    // Un instante de respuesta antes de cambiar de pantalla
    window.setTimeout(() => router.push("/proyecto"), 420);
  }

  return (
    <form
      onSubmit={submit}
      aria-labelledby="acceso-titulo"
      className={cn("surface-sheen rounded-[16px] border border-border bg-surface p-5 shadow-[var(--shadow-pop)] sm:p-6", className)}
    >
      <h2 id="acceso-titulo" className="text-[15px] font-semibold text-strong">
        Entra en la demo
      </h2>
      <p className="mt-1 text-[13px] text-muted">Cualquier usuario sirve mientras no haya cuentas.</p>

      <div className="mt-5 space-y-3.5">
        <div>
          <label htmlFor="acceso-usuario" className="mb-1.5 block text-[13px] text-muted">
            Usuario
          </label>
          <input
            id="acceso-usuario"
            name="usuario"
            autoComplete="username"
            spellCheck={false}
            value={user}
            onChange={(e) => setUser(e.target.value)}
            placeholder="nombre.apellido"
            className={field}
          />
        </div>
        <div>
          <label htmlFor="acceso-contrasena" className="mb-1.5 block text-[13px] text-muted">
            Contraseña
          </label>
          <div className="relative">
            <input
              id="acceso-contrasena"
              name="contrasena"
              type={show ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={cn(field, "pr-11")}
            />
            <button
              type="button"
              onClick={() => setShow((v) => !v)}
              aria-label={show ? "Ocultar contraseña" : "Mostrar contraseña"}
              aria-pressed={show}
              className="absolute top-1/2 right-1.5 flex size-8 -translate-y-1/2 items-center justify-center rounded-[8px] text-faint transition-colors duration-[var(--dur-fast)] hover:bg-surface-raised hover:text-text"
            >
              <Icon icon={show ? EyeOff : Eye} size={16} />
            </button>
          </div>
        </div>
      </div>

      <button
        type="submit"
        disabled={busy}
        className="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-[10px] bg-accent text-[15px] font-semibold text-accent-contrast transition-[transform,background-color] duration-[160ms] ease-[var(--ease-out)] hover:bg-accent/90 active:scale-[0.98] disabled:opacity-80"
      >
        {busy ? (
          <>
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
            Entrando
          </>
        ) : (
          "Iniciar"
        )}
      </button>
      <p className="mt-3 text-[12px] text-faint" role="note">
        Demo: el acceso aún no comprueba usuario ni contraseña, y la contraseña no se guarda.
      </p>
    </form>
  );
}
