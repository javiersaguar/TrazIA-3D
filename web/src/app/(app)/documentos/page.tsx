import { Suspense } from "react";
import { DocumentLibrary } from "@/features/documents/document-library";

export const metadata = { title: "Documentos" };

export default function Page() {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted">Cargando catálogo…</p>}>
      <DocumentLibrary />
    </Suspense>
  );
}
