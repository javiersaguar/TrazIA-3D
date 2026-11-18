import { PageTransition } from "@/components/shell/page-transition";
import { PipelineResult } from "@/features/pipeline/pipeline-result";

export const metadata = { title: "Resultado del pipeline" };

export default async function ResultPage({ params }: { params: Promise<{ identity: string }> }) {
  const { identity } = await params;
  // El segmento llega codificado en la navegación de Next. El cliente codifica la ruta de la API.
  let revisionId = identity;
  try { revisionId = decodeURIComponent(identity); } catch { /* Conservar el segmento para que la API indique el error. */ }
  return <PageTransition><PipelineResult identity={revisionId} /></PageTransition>;
}
