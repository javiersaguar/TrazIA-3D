import { SketchPage } from "@/components/shell/sketch-page";
import { ReportsSketch } from "@/features/bocetos/reports-sketch";

export const metadata = { title: "Informes" };

export default function InformesPage() {
  return (
    <SketchPage href="/informes">
      <ReportsSketch />
    </SketchPage>
  );
}
