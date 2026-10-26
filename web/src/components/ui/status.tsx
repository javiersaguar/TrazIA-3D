import type { EquipmentRow } from "@/lib/mock/api";
import type { FieldStatus } from "@/lib/mock/fields";
import { Badge } from "./primitives";

export function EquipmentStatus({ status }: { status: EquipmentRow["status"] }) {
  switch (status) {
    case "draft":
      return <Badge tone="neutral">DRAFT</Badge>;
    case "review":
      return <Badge tone="accent">En revisión</Badge>;
    case "approved":
      return <Badge tone="approved">Aprobado</Badge>;
    case "changed":
      return <Badge tone="revision">Con cambios</Badge>;
  }
}

export const FIELD_STATUS_LABEL: Record<FieldStatus, string> = {
  candidate: "Por revisar",
  accepted: "Aceptado",
  corrected: "Corregido",
  assumed: "Supuesto",
};

export function FieldStatusBadge({ status }: { status: FieldStatus }) {
  const tone = status === "accepted" ? "approved" : status === "corrected" ? "accent" : status === "assumed" ? "warning" : "neutral";
  return <Badge tone={tone}>{FIELD_STATUS_LABEL[status]}</Badge>;
}

export function SyntheticBadge() {
  return <Badge tone="warning">ilustrativo</Badge>;
}
