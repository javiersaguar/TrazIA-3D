import * as mock from "../mock/api";
import { apiEnabled } from "./config";
import { apiBench, apiChanges, apiEquipment, apiFields, apiRevision } from "./client";

export type { RevisionId, BenchExtractor, FieldUpdate, EquipmentRow } from "../mock/api";
export { apiEnabled } from "./config";
export const getRevision = (rev: mock.RevisionId) => apiEnabled ? apiRevision(rev) : mock.getRevision(rev);
export const getReviewFields = (rev: mock.RevisionId) => apiEnabled ? apiFields(rev) : mock.getReviewFields(rev);
export const getChanges = () => apiEnabled ? apiChanges() : mock.getChanges();
export const getEquipment = () => apiEnabled ? apiEquipment() : mock.getEquipment();
export const getBench = (extractor: mock.BenchExtractor) => apiEnabled ? apiBench(extractor) : mock.getBench(extractor);
