import { PageHeader } from "@/components/shell/page-header";
import { PageTransition } from "@/components/shell/page-transition";
import { PipelineWorkspace } from "@/features/pipeline/pipeline-workspace";
import { NAV_ITEMS } from "@/lib/nav";

export const metadata = { title: "Pipeline" };

export default function PipelinePage() {
  const item = NAV_ITEMS.find((i) => i.href === "/pipeline")!;
  return (
    <PageTransition>
      <PageHeader title="Pipeline" description={item.description} />
      <PipelineWorkspace />
    </PageTransition>
  );
}
