import { PageHeader } from "@/components/shell/page-header";
import { PageTransition } from "@/components/shell/page-transition";
import { ReviewWorkspace } from "@/features/review/review-workspace";
import { NAV_ITEMS } from "@/lib/nav";

export const metadata = { title: "Revisión" };

export default function RevisionPage() {
  const item = NAV_ITEMS.find((i) => i.href === "/revision")!;
  return (
    <PageTransition>
      <PageHeader title="Revisión" description={item.description} />
      <ReviewWorkspace />
    </PageTransition>
  );
}
