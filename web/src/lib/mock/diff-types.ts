/*
  Tipos PROVISIONALES del informe de cambios (generated/changes.json).
  El núcleo todavía no publica un esquema JSON del delta; cuando exista,
  estos tipos se sustituyen por otros generados con scripts/gen-types.mjs.
*/
import type { Source } from "@/lib/types/revision";

export type DiffValue = { value: number | string; unit: string };

export type FieldChange = {
  path: string;
  operation: "added" | "removed" | "modified" | "renamed";
  before: DiffValue | null;
  after: DiffValue | null;
  affects_geometry: boolean;
  impact: string;
  before_source: Source | null;
  after_source: Source | null;
};

export type DocumentSnapshot = {
  id: string;
  filename: string;
  revision: string;
  sha256: string;
  page_count: number | null;
};

export type DiffReport = {
  project_id: string;
  equipment_id: string;
  from_revision: string;
  to_revision: string;
  summary: {
    changes: number;
    geometry_changes: number;
    provenance_changes: number;
    document_changes: number;
  };
  changes: FieldChange[];
  provenance_changes: unknown[];
  document_changes: { id: string; before: DocumentSnapshot | null; after: DocumentSnapshot | null }[];
  before_sha256: string;
  after_sha256: string;
};
