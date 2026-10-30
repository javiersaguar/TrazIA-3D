import { SketchPage } from "@/components/shell/sketch-page";
import { DocumentsSketch } from "@/features/bocetos/documents-sketch";

export const metadata = { title: "Documentos" };

export default function DocumentosPage() {
  return (
    <SketchPage href="/documentos" note="Los PDF que sueltes se quedan en esta pestaña; no se suben a ningún sitio.">
      <DocumentsSketch />
    </SketchPage>
  );
}
