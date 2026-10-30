"use client";

import { useIsMutating, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Stamp } from "lucide-react";
import { toast } from "sonner";
import { Button, Icon } from "@/components/ui/primitives";
import { apiEnabled } from "@/lib/api/config";
import { ApiError } from "@/lib/api/client";
import { flattenRevision, type ReviewField } from "@/lib/mock/fields";
import type { RevisionId } from "@/lib/mock/api";
import { qk } from "@/lib/queries";
import { approveRevision } from "./approval";

export function ApprovalButton({
  revision,
  fields,
}: {
  revision: RevisionId;
  fields?: ReviewField[];
}) {
  const qc = useQueryClient(),
    writes = useIsMutating();
  const dialog = useRef<HTMLDialogElement>(null),
    key = useRef<string | null>(null);
  const [reviewer, setReviewer] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<string | null>(null),
    [stale, setStale] = useState(false);
  const pending =
    fields?.filter((f) => f.status !== "accepted" && f.status !== "corrected")
      .length ?? 0;
  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      key.current ??= crypto.randomUUID();
      const result = await approveRevision(revision, reviewer, key.current);
      qc.setQueryData(qk.revision(revision), result);
      qc.setQueryData(qk.fields(revision), flattenRevision(result));
      dialog.current?.close();
      toast.success(`Revisión ${revision} aprobada`, {
        description: `Aprobación vinculada a la huella de datos · ${result.approval?.reviewer ?? reviewer}`,
      });
    } catch (e) {
      if (e instanceof ApiError && (e.status === 412 || e.status === 409)) {
        setStale(true);
        setError(
          e.status === 412
            ? "La revisión cambió en otra sesión. Recarga y comprueba los campos antes de aprobar."
            : e.message,
        );
      } else
        setError(
          e instanceof Error
            ? e.message
            : "No se pudo guardar. Comprueba la conexión y reintenta.",
        );
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <Button
        variant="primary"
        disabled={!fields || pending > 0 || writes > 0 || busy}
        title={
          pending
            ? `Faltan ${pending} campos por aceptar o corregir`
            : undefined
        }
        onClick={() => {
          if (!apiEnabled) {
            toast("La demo no firma una aprobación", {
              description:
                "Conecta la API para guardar la revisión humana vinculada a su huella.",
            });
            return;
          }
          key.current = null;
          setError(null);
          setStale(false);
          dialog.current?.showModal();
        }}
      >
        <Icon icon={Stamp} size={15} />
        Aprobar revisión
      </Button>
      <dialog
        ref={dialog}
        className="m-auto w-[min(440px,calc(100%-32px))] rounded-xl border border-border bg-surface p-6 text-text backdrop:bg-black/70"
        aria-labelledby="approval-title"
        onCancel={(e) => {
          if (busy) e.preventDefault();
        }}
      >
        <h2 id="approval-title" className="text-lg font-semibold">
          Aprobar revisión {revision}
        </h2>
        <p className="mt-2 text-sm text-muted">
          Registra tu revisión humana de los originales y vincula la aprobación
          a esta versión. Estos documentos de demostración son sintéticos.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <label className="mt-4 block text-sm">
            Nombre del revisor
            <input
              autoFocus
              required
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              className="mt-2 w-full rounded-md border border-border bg-surface-sunken px-3 py-2"
            />
          </label>
          {error ? (
            <p role="alert" className="mt-3 text-sm text-danger">
              {error}
            </p>
          ) : null}
          <div className="mt-5 flex justify-end gap-2">
            <Button
              type="button"
              disabled={busy}
              onClick={() => dialog.current?.close()}
            >
              Cancelar
            </Button>
            {stale ? (
              <Button
                type="button"
                onClick={async () => {
                  await qc.invalidateQueries({ queryKey: qk.fields(revision) });
                  await qc.invalidateQueries({
                    queryKey: qk.revision(revision),
                  });
                  dialog.current?.close();
                }}
              >
                Recargar campos
              </Button>
            ) : (
              <Button
                type="submit"
                variant="primary"
                disabled={busy || !reviewer.trim() || writes > 0}
              >
                {busy
                  ? "Guardando…"
                  : error
                    ? "Reintentar"
                    : "Guardar aprobación"}
              </Button>
            )}
          </div>
        </form>
      </dialog>
    </>
  );
}
