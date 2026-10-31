import type { PropertySets } from "../../workers/ifc-protocol";
import type { Annotation } from "./types";
type Trace = { value: number | string; unit: string; state?: string; source: NonNullable<Annotation["source"]> & { confidence: number } };
export function ifcTraces(psets: PropertySets): Record<string, Trace> {
  const raw = psets.TrazIA_Traceability?.FieldsJSON;
  if (typeof raw !== "string") return {};
  try {
    const data: unknown = JSON.parse(raw);
    if (!data || typeof data !== "object" || Array.isArray(data)) return {};
    return Object.fromEntries(Object.entries(data).filter((pair): pair is [string, Trace] => {
      const field = pair[1];
      return !!field && typeof field === "object" && (typeof field.value === "number" || typeof field.value === "string")
        && typeof field.unit === "string" && !!field.source && typeof field.source === "object"
        && typeof field.source.document_id === "string" && typeof field.source.confidence === "number"
        && Number.isFinite(field.source.confidence) && field.source.confidence >= 0 && field.source.confidence <= 1;
    }));
  } catch { return {}; }
}
