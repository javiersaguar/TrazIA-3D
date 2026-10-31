"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/primitives";
import { apiEnabled, apiURL } from "@/lib/api/config";
import type { RevisionId } from "@/lib/mock/api";
import { ActiveReviewClock } from "./active-clock";
import { useManualReview } from "./review-session";

export function ManualSession({ revision }: { revision: RevisionId }) {
  const { session, setSession, busy, setBusy } = useManualReview();
  const [actor, setActor] = useState("");
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<number | null>(null);
  useEffect(() => {
    if (!session) return;
    const clock = session.clock;
    const visible = () => {
      if (document.visibilityState === "visible" && document.hasFocus() && session.revision === revision) clock.resume();
      else clock.pause();
    };
    const activity = () => clock.activity();
    visible();
    document.addEventListener("visibilitychange", visible);
    window.addEventListener("focus", visible);
    window.addEventListener("blur", visible);
    window.addEventListener("pointerdown", activity);
    window.addEventListener("keydown", activity);
    window.addEventListener("scroll", activity, true);
    return () => {
      clock.pause();
      document.removeEventListener("visibilitychange", visible);
      window.removeEventListener("focus", visible);
      window.removeEventListener("blur", visible);
      window.removeEventListener("pointerdown", activity);
      window.removeEventListener("keydown", activity);
      window.removeEventListener("scroll", activity, true);
    };
  }, [session, revision]);

  if (!apiEnabled) return <p className="text-xs text-muted">Sesión manual: conecta la API para guardar tiempos y auditoría.</p>;
  async function submit() {
    setPending(true);
    setBusy(true);
    const clock = session?.clock;
    clock?.block();
    try {
      const response = await fetch(apiURL(session ? `/review-sessions/${session.id}/finish` : "/review-sessions"), {
        method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify(session ? { active_seconds: clock!.seconds() } : { revision_id: revision, actor: actor.trim(), kind: navigator.webdriver ? "test" : "human" }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "No se pudo guardar la sesión");
      if (session) {
        if (data.id !== session.id || typeof data.active_seconds !== "number" || !Number.isFinite(data.active_seconds)) throw new Error("La API no confirmó el tiempo guardado; reintenta finalizar la sesión.");
        setResult(data.active_seconds); setSession(null);
      } else {
        if (typeof data.id !== "string" || typeof data.actor !== "string") throw new Error("La API no confirmó la sesión; vuelve a intentarlo.");
        setResult(null); setSession({ id: data.id, actor: data.actor, revision, clock: new ActiveReviewClock() });
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "No se pudo guardar la sesión");
      clock?.unblock();
      if (document.hasFocus() && document.visibilityState === "visible") clock?.resume();
    } finally { setPending(false); setBusy(false); }
  }

  return <section aria-label="Sesión manual de revisión" className="rounded-lg border border-border bg-surface p-3 text-xs">
    <div className="flex flex-wrap items-center gap-3">
      <strong className="text-strong">Sesión manual · datos sintéticos</strong>
      {session ? <span>{session.actor} · rev {session.revision} · {session.revision === revision ? "tiempo activo en registro" : "pausada al ver otra revisión"}</span> : <label>Revisor <input aria-label="Revisor de la sesión" value={actor} onChange={(e) => setActor(e.target.value)} maxLength={100} className="ml-2 rounded border border-border bg-surface-sunken p-1.5" placeholder="Tu nombre" /></label>}
      <Button size="sm" variant="secondary" disabled={pending || busy || (!session && actor.trim().length < 2)} onClick={submit}>{pending ? "Guardando…" : session ? "Finalizar sesión" : "Iniciar sesión manual"}</Button>
      {result !== null && <span role="status">Sesión guardada: {result.toFixed(1).replace(".", ",")} s activos.</span>}
    </div>
    <p className="mt-2 text-muted">Se pausa al cambiar de pestaña o ventana, durante el guardado y tras 60 s sin interacción. Finaliza antes de salir. La participación humana se declara; las pruebas se registran aparte.</p>
  </section>;
}
