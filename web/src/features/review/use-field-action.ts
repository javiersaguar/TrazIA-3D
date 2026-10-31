"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { FIELD_STATUS_LABEL } from "@/components/ui/status";
import { apiExportCorrections } from "@/lib/api/client";
import { updateField, undoField, type FieldOptions, type RevisionId } from "@/lib/mock/api";
import { compareRisk, isResolved, type FieldStatus, type ReviewField } from "@/lib/mock/fields";
import { qk } from "@/lib/queries";
import { useReviewLog, type ReviewAction } from "@/stores/review-log";
import { reviewTiming, settleTiming, useManualReview } from "./review-session";

type Vars = { at: number; rev: RevisionId; field: ReviewField; status: FieldStatus; correctedValue?: number | string; id: string; options: FieldOptions; undo?: ReviewAction };

export function useFieldAction(rev: RevisionId) {
  const qc = useQueryClient();
  const busy = useManualReview((s) => s.busy);
  const mutation = useMutation({
    mutationKey: ["review-field", rev],
    mutationFn: (v: Vars) => {
      const update = { rev: v.rev, path: v.field.path, status: v.status, correctedValue: v.correctedValue, idempotencyKey: v.id, expected: v.field.snapshot, ...v.options };
      return v.undo ? undoField(update, v.undo.before, v.undo.auditId) : updateField(update, v.field);
    },
    onMutate: async (v) => {
      await qc.cancelQueries({ queryKey: qk.fields(v.rev) });
      const previous = qc.getQueryData<ReviewField[]>(qk.fields(v.rev));
      qc.setQueryData<ReviewField[]>(qk.fields(v.rev), (old) => old?.map((f) => f.path === v.field.path ? v.undo?.before ?? { ...f, status: v.status, correctedValue: v.correctedValue } : f));
      return { previous };
    },
    onSuccess: (result, v) => {
      qc.setQueryData<ReviewField[]>(qk.fields(v.rev), (old) => old?.map((f) => f.path === result.path ? result : f).sort(compareRisk));
      if (v.undo) {
        useReviewLog.getState().remove(v.undo.id);
        toast(`Deshecho: ${v.field.label}`, { id: `review-${v.field.path}` });
      } else {
        const fields = qc.getQueryData<ReviewField[]>(qk.fields(v.rev)) ?? [];
        const action: ReviewAction = {
          id: v.id, at: v.at, rev: v.rev, path: result.path, label: result.label,
          before: v.field, auditId: result.auditId,
          from: { status: v.field.status, correctedValue: v.field.correctedValue },
          to: { status: result.status, correctedValue: result.correctedValue },
          reviewedAfter: fields.filter(isResolved).length,
        };
        useReviewLog.getState().push(action);
        toast(v.options.action === "reject" ? "Lectura rechazada" : `Campo ${FIELD_STATUS_LABEL[v.status].toLowerCase()}`, {
          id: `review-${result.path}`, description: result.label, duration: 5000,
          action: { label: "Deshacer", onClick: () => undo(action) },
        });
      }
      settleTiming(v.options.seconds, true);
      if (result.saveWarning) toast.warning(result.saveWarning, {
        id: "correcciones-pendientes", duration: Infinity,
        action: { label: "Reintentar exportación", onClick: () => {
          toast.promise(apiExportCorrections().then(() => toast.dismiss("correcciones-pendientes")), {
            loading: "Exportando registro…", success: "Registro actualizado", error: "La exportación sigue pendiente",
          });
        } },
      });
    },
    onError: (error, v, context) => {
      if (context?.previous) qc.setQueryData(qk.fields(v.rev), context.previous);
      settleTiming(v.options.seconds, false);
      toast.error(error.message, { description: `No se guardó «${v.field.label}».` });
    },
    onSettled: (_data, _error, v) => {
      useManualReview.getState().setBusy(false);
      void qc.invalidateQueries({ queryKey: qk.fields(v.rev) });
      void qc.invalidateQueries({ queryKey: qk.revision(v.rev) });
      void qc.invalidateQueries({ queryKey: ["review-validation", v.rev] });
    },
  });

  function undo(action: ReviewAction) {
    if (useManualReview.getState().busy) return;
    const field = qc.getQueryData<ReviewField[]>(qk.fields(action.rev))?.find((f) => f.path === action.path);
    if (!field) return;
    useManualReview.getState().setBusy(true);
    mutation.mutate({ at: Date.now(), rev: action.rev, field, status: action.from.status, id: `undo-${action.id}`, options: reviewTiming(action.rev), undo: action });
  }

  function apply(field: ReviewField, status: FieldStatus, correctedValue?: number | string, options: FieldOptions = {}) {
    if (useManualReview.getState().busy) return;
    if (!options.action && !options.source && !options.explanation && field.status === status && field.correctedValue === correctedValue) return;
    useManualReview.getState().setBusy(true);
    return mutation.mutateAsync({ at: Date.now(), rev, field, status, correctedValue, options: { ...options, ...reviewTiming(rev) }, id: crypto.randomUUID() }).then(() => true).catch(() => false);
  }

  function undoLast() {
    const last = [...useReviewLog.getState().actions].reverse().find((a) => a.rev === rev);
    if (last) undo(last);
  }
  return { apply, undoLast, busy };
}
