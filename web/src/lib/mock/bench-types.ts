/*
  Tipos PROVISIONALES del informe del bench (bench/report.py → report.json).
  Cuando el bench publique un esquema JSON se generarán con scripts/gen-types.mjs.
*/

export type BenchStyleId = "rotulado" | "plano" | "escaneado";

export type ReliabilityPoint = { bin: [number, number]; confidence: number; accuracy: number; n: number };

export type BenchStyle = {
  equipment: number;
  revisions: number;
  models_built: number;
  geometry: {
    field_coverage: number | null;
    field_accuracy: number | null;
    dimension_mae_mm: number | null;
    nozzle_recall: number | null;
    nozzle_precision: number | null;
    nozzle_position_mae_mm: number | null;
    nozzle_orientation_mae_deg: number | null;
    nozzle_dn_accuracy: number | null;
    ifc_element_recall: number | null;
    ifc_mean_iou: number | null;
    ifc_center_error_mm: number | null;
  };
  attributes: {
    coverage: number | null;
    accuracy_value_unit: number | null;
    ece: number | null;
    brier: number | null;
    calibration_points: number;
    reliability: ReliabilityPoint[];
  };
  delta: {
    evaluable_equipment: number;
    tp: number;
    fp: number;
    fn: number;
    precision: number | null;
    recall: number | null;
    f1: number | null;
    magnitude_mae: number | null;
  };
  scale: {
    seconds_per_revision: number | null;
    revisions_per_hour: number | null;
    llm_calls: number;
    cost_eur: number;
  };
  failures: string[];
};

export type BenchReport = {
  generated_at: string;
  dataset: string;
  seed: number;
  extractor: string;
  styles: Record<BenchStyleId, BenchStyle>;
};
