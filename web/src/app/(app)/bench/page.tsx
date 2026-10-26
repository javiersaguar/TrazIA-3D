import { PageHeader } from "@/components/shell/page-header";
import { PageTransition } from "@/components/shell/page-transition";
import { BenchWorkspace } from "@/features/bench/bench-workspace";
import { NAV_ITEMS } from "@/lib/nav";

export const metadata = { title: "Bench" };

export default function BenchPage() {
  const item = NAV_ITEMS.find((i) => i.href === "/bench")!;
  return (
    <PageTransition>
      <PageHeader title="Bench" description={item.description} />
      <BenchWorkspace />
    </PageTransition>
  );
}
