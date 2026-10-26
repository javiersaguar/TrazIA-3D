"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { toast } from "sonner";
import { FIELD_STATUS_LABEL } from "@/components/ui/status";
import { formatValue } from "@/lib/format";
import { updateField, type RevisionId } from "@/lib/mock/api";
import type { FieldStatus, ReviewField } from "@/lib/mock/fields";
import { qk } from "@/lib/queries";
import { useReviewLog, type ReviewAction } from "@/stores/review-log";

type Vars = { field: ReviewField; status: FieldStatus; correctedValue?: number | string; idempotencyKey: string };

const VERB: Record<FieldStatus, string> = {
  accepted: "Campo aceptado",
  corrected: "Campo corregido",
  assumed: "Marcado como supuesto",
  candidate: "Campo devuelto a revisión",
};

/**
 * Acciones de revisión con actualización optimista: la UI cambia al instante, se revierte si
 * la petición falla y cada acción ofrece "Deshacer" durante unos segundos.
 */
export function useFieldAction(rev: RevisionId) {
  const qc = useQueryClient();
  const push = useReviewLog((s) => s.push);
  const remove = useReviewLog((s) => s.remove);

  const { mutate } = useMutation({
    mutationFn: ({ field, status, correctedValue, idempotencyKey }: Vars) =>
      updateField({ rev, path: field.path, status, correctedValue, idempotencyKey }, field),
    onMutate: async ({ field, status, correctedValue }) => {
      await qc.cancelQueries({ queryKey: qk.fields(rev) });
      const previous = qc.getQueryData<ReviewField[]>(qk.fields(rev));
      qc.setQueryData<ReviewField[]>(qk.fields(rev), (old) =>
        old?.map((f) => (f.path === field.path ? { ...f, status, correctedValue: status === "corrected" ? correctedValue : undefined } : f)),
      );
      return { previous };
    },
    onError: (_err, { field }, ctx) => {
      if (ctx?.previous) qc.setQueryData(qk.fields(rev), ctx.previous);
      toast.error(`No se guardó «${field.label}». Vuelve a intentarlo.`);
    },
  });

  const undo = useCallback(
    (action: ReviewAction) => {
      const fields = qc.getQueryData<ReviewField[]>(qk.fields(action.rev)) ?? [];
      const field = fields.find((f) => f.path === action.path);
      if (!field) return;
      mutate({
        field,
        status: action.from.status,
        correctedValue: action.from.correctedValue,
        idempotencyKey: `undo-${action.id}`,
      });
      remove(action.id);
      toast(`Deshecho: ${action.label}`, { id: `review-${action.path}`, duration: 2500 });
    },
    [mutate, qc, remove],
  );

  const apply = useCallback(
    (field: ReviewField, status: FieldStatus, correctedValue?: number | string) => {
      if (field.status === status && field.correctedValue === correctedValue) return;
      const idempotencyKey = crypto.randomUUID();
      mutate({ field, status, correctedValue, idempotencyKey });

      const fields = qc.getQueryData<ReviewField[]>(qk.fields(rev)) ?? [];
      const action: ReviewAction = {
        id: idempotencyKey,
        at: Date.now(),
        rev,
        path: field.path,
        label: field.label,
        from: { status: field.status, correctedValue: field.correctedValue },
        to: { status, correctedValue },
        reviewedAfter: fields.filter((f) => (f.path === field.path ? status : f.status) !== "candidate").length,
      };
      push(action);

      const value = formatValue(correctedValue ?? field.value, field.unit);
      toast(VERB[status], {
        id: `review-${field.path}`,
        description: `${field.label} · ${status === "corrected" ? value : FIELD_STATUS_LABEL[status].toLowerCase()}`,
        duration: 5000,
        action: { label: "Deshacer", onClick: () => undo(action) },
      });
    },
    [mutate, push, qc, rev, undo],
  );

  const undoLast = useCallback(() => {
    const last = [...useReviewLog.getState().actions].reverse().find((a) => a.rev === rev);
    if (last) undo(last);
  }, [rev, undo]);

  return { apply, undoLast };
}
