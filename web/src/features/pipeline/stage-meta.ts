import {
  Box,
  Eye,
  FileInput,
  FolderTree,
  Merge,
  ScanText,
  Shapes,
  Sheet,
  ShieldCheck,
  Table2,
  Tags,
  type LucideIcon,
} from "lucide-react";
import type { StageId } from "@/lib/mock/pipeline";

export const STAGE_ICON: Record<StageId, LucideIcon> = {
  ingest: FileInput,
  classify: FolderTree,
  extract_labels: Tags,
  extract_tables: Table2,
  extract_ocr: ScanText,
  extract_vision: Eye,
  extract_hdm: Sheet,
  reconcile: Merge,
  family: Shapes,
  ifc: Box,
  validate: ShieldCheck,
  extract_detector: ScanText,
  geometry2d: Shapes,
  rag: FileInput,
  memory: FolderTree,
  calibrate: ShieldCheck,
};
