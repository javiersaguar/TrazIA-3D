import { PageHeader } from "@/components/shell/page-header";
import { PageTransition } from "@/components/shell/page-transition";
import { ProjectWorkspace } from "@/features/project/project-workspace";
import { NAV_ITEMS } from "@/lib/nav";

export const metadata = { title: "Resumen" };

export default function ProyectoPage() {
  const item = NAV_ITEMS.find((i) => i.href === "/proyecto")!;
  return (
    <PageTransition>
      <PageHeader title="Resumen" description={item.description} />
      <ProjectWorkspace />
    </PageTransition>
  );
}
