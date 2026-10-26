import { PageHeader } from "@/components/shell/page-header";
import { PageTransition } from "@/components/shell/page-transition";
import { RoiCalculator } from "@/features/impact/roi-calculator";
import { NAV_ITEMS } from "@/lib/nav";

export const metadata = { title: "Impacto" };

export default function ImpactoPage() {
  const item = NAV_ITEMS.find((i) => i.href === "/impacto")!;
  return (
    <PageTransition>
      <PageHeader title="Impacto" description={item.description} />
      <RoiCalculator />
    </PageTransition>
  );
}
