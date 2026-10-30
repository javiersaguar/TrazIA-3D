import { SketchPage } from "@/components/shell/sketch-page";
import { AuditSketch } from "@/features/bocetos/audit-sketch";

export const metadata = { title: "Auditoría" };

export default function AuditoriaPage() {
  return (
    <SketchPage href="/auditoria">
      <AuditSketch />
    </SketchPage>
  );
}
