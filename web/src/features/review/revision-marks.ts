import { useQuery } from "@tanstack/react-query";
import { apiEnabled, apiURL } from "@/lib/api/config";
import type { RevisionId } from "@/lib/mock/api";

export type RevisionMark = {
  id: string; document_id: string; kind: "delta" | "cloud"; page: number;
  bbox: [number, number, number, number]; label: string | null; method: "vector"; candidate: true;
};
export type MarkDocument = {
  document_id: string; filename: string; status: string; marks: RevisionMark[];
  unread_pages: number[]; pages_truncated?: boolean;
};
export type MarkReport = {
  status: string; documents: MarkDocument[]; unmarked_changes: {path: string; document_id: string}[];
  marks_without_change: RevisionMark[]; unlocated_changes: string[];
  is_design_validation: false; coordinate_frame: "after-page";
};

export function useRevisionMarks(revision: RevisionId, version: number) {
  return useQuery({
    queryKey: ["revision-marks", revision, version], enabled: apiEnabled && revision === "B" && version > 0,
    queryFn: async ({ signal }) => {
      const response = await fetch(apiURL("/diff?from=A&to=B&marks=true"), { signal });
      if (!response.ok) throw new Error("No se pudieron leer las marcas de los originales");
      const body = await response.json();
      const marks = body?.layers?.revision_marks as MarkReport | undefined;
      if (!marks || !Array.isArray(marks.documents) || !Array.isArray(marks.unmarked_changes)) {
        throw new Error("La API no ha devuelto el cruce de marcas");
      }
      return marks;
    },
  });
}
