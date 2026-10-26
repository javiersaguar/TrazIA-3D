/* Interfaz 3 de docs/COORDINACION-BACKEND.md: generated/estudio/estudio.json (lo produce Lectura). */

export type StudyMetrics = {
  score: number;
  geometry: number;
  attributes: number;
  ece: number | null;
  f1_delta: number | null;
  hallucination_rate: number;
  citation_coverage: number;
  interval_coverage: number | null;
  cost_eur_per_equipment: number;
  seconds_per_revision: number;
};

export type StudyDatasetMetrics = StudyMetrics & {
  equipment?: number;
  revisions?: number;
  models_built?: number;
  geometry_fields_unpenalized?: number;
  poisoning_rate?: number | null;
};

export type StudyVariant = {
  id: string;
  strategy: string;
  providers: string[];
  description?: string;
  metrics: StudyMetrics;
  ci95: Partial<Record<"score" | "geometry" | "attributes" | "f1_delta", [number, number] | null>>;
  by_dataset: Record<string, StudyDatasetMetrics>;
  by_style: Record<string, StudyMetrics>;
  by_degradation: Record<string, StudyMetrics>;
  eligible?: boolean;
  details?: Record<string, unknown>;
};

export type StudyReport = {
  generated_at: string;
  seed: number;
  synthetic?: boolean;
  generator?: string;
  sets?: Record<string, { seed: number; cases: number }>;
  datasets: string[];
  variants: StudyVariant[];
  unmeasured?: { id: string; reason: string }[];
  ablations: { id: string; of?: string; delta_score: number; ci95: [number, number] | null }[];
  pairwise: { a: string; b: string; mcnemar_p: number; only_a?: number; only_b?: number; fields?: number }[];
  pareto: string[];
  recommendation: { vectorial: string | null; escaneado: string | null; rationale: string };
};

/** Respuesta de GET /estudio cuando Lectura aún no ha publicado resultados. */
export type StudyEmpty = { status: "empty"; variants: []; detail: string };

export type StudyResponse = StudyReport | StudyEmpty;

export const isStudyEmpty = (s: StudyResponse): s is StudyEmpty =>
  "status" in s && s.status === "empty";
