import { SketchPage } from "@/components/shell/sketch-page";
import { BatchSketch } from "@/features/bocetos/batch-sketch";

export const metadata = { title: "Lote" };

export default function LotePage() {
  return (
    <SketchPage href="/lote">
      <BatchSketch />
    </SketchPage>
  );
}
