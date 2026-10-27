import type { StudyReport } from "@/lib/mock/estudio-types";

export function studyScope(study: StudyReport) {
  const datasets = study.datasets.filter(name => name === "S-dev" || name === "S-reservado");
  const vendors = new Set(study.variants.flatMap(v => Object.keys(v.by_style)));
  const degradations = new Set(study.variants.flatMap(v => Object.keys(v.by_degradation)));
  const equipment = datasets.reduce((sum, name) => sum + (study.sets?.[name]?.cases ?? 0), 0);
  return { datasets, vendors: vendors.size, degradations: degradations.size, equipment };
}
