import { PageHeader } from "@/components/shell/page-header";
import { PageTransition } from "@/components/shell/page-transition";
import { EstudioWorkspace } from "@/features/estudio/estudio-workspace";
import { NAV_ITEMS } from "@/lib/nav";

export const metadata = { title: "Estudio" };

export default function EstudioPage() {
  const item = NAV_ITEMS.find((i) => i.href === "/estudio")!;
  return (
    <PageTransition>
      <PageHeader title="Estudio" description={item.description} />
      <EstudioWorkspace />
    </PageTransition>
  );
}
