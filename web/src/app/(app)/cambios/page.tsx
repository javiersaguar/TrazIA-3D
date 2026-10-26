import { PageHeader } from "@/components/shell/page-header";
import { PageTransition } from "@/components/shell/page-transition";
import { ChangesWorkspace } from "@/features/changes/changes-workspace";
import { NAV_ITEMS } from "@/lib/nav";

export const metadata = { title: "Cambios" };

export default function CambiosPage() {
  const item = NAV_ITEMS.find((i) => i.href === "/cambios")!;
  return (
    <PageTransition>
      <PageHeader title="Cambios" description={item.description} />
      <ChangesWorkspace />
    </PageTransition>
  );
}
