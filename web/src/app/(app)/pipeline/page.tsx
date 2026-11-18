import { PageHeader } from "@/components/shell/page-header";
import { PageTransition } from "@/components/shell/page-transition";
import { PipelineWorkspace } from "@/features/pipeline/pipeline-workspace";
import { NAV_ITEMS } from "@/lib/nav";

export const metadata = { title: "Pipeline" };

export default async function PipelinePage({ searchParams }: { searchParams: Promise<{ trabajo?: string | string[] }> }) {
  const { trabajo } = await searchParams;
  const item = NAV_ITEMS.find((i) => i.href === "/pipeline")!;
  return (
    <PageTransition>
      <PageHeader title="Pipeline" description={item.description} />
      <PipelineWorkspace initialJobId={typeof trabajo === "string" ? trabajo : undefined} />
    </PageTransition>
  );
}
