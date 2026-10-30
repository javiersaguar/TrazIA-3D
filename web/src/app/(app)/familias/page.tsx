import { SketchPage } from "@/components/shell/sketch-page";
import { FamiliesSketch } from "@/features/bocetos/families-sketch";

export const metadata = { title: "Familias" };

export default function FamiliasPage() {
  return (
    <SketchPage href="/familias" note="Hoy solo existe la familia del recipiente vertical. Las miniaturas son ilustrativas, no proceden del IFC.">
      <FamiliesSketch />
    </SketchPage>
  );
}
