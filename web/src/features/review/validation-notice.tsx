"use client";

import { useQuery } from "@tanstack/react-query";
import { apiEnabled, apiURL } from "@/lib/api/config";
import type { RevisionId } from "@/lib/mock/api";

type Issue = { path: string; message: string; action: string };
export function ValidationNotice({ revision, onSelect }: { revision: RevisionId; onSelect: (path: string) => void }) {
  const { data, error } = useQuery({
    queryKey: ["review-validation", revision], enabled: apiEnabled,
    queryFn: async () => {
      const response = await fetch(apiURL(`/revisions/${revision}/validation`));
      if (!response.ok) throw new Error("No se pudieron consultar las comprobaciones");
      return response.json() as Promise<{ issues: Issue[] }>;
    },
  });
  if (!apiEnabled) return null;
  if (error) return <p role="alert" className="text-xs text-warning">{error.message}</p>;
  if (!data?.issues.length) return null;
  return <details className="rounded-lg border border-border bg-surface p-3 text-xs">
    <summary className="cursor-pointer text-warning">Comprobaciones de la revisión · {data.issues.length} avisos</summary>
    <ul className="mt-2 space-y-2">{data.issues.map((issue, i) => <li key={`${issue.path}-${i}`}>
      <button type="button" onClick={() => onSelect(issue.path)} className="text-left text-accent-text underline underline-offset-2">{issue.path}: {issue.message}</button>
      <p className="text-muted">{issue.action}</p>
    </li>)}</ul>
    <p className="mt-2 text-muted">Estas comprobaciones ayudan a revisar; no certifican conformidad normativa.</p>
  </details>;
}
