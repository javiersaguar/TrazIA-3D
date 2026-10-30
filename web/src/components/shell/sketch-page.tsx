import { PencilRuler } from "lucide-react";
import type { ReactNode } from "react";
import { EmptyState, Panel } from "@/components/ui/primitives";
import { NAV_ITEMS } from "@/lib/nav";
import { PageHeader } from "./page-header";
import { PageTransition } from "./page-transition";

/** Página de una sección en boceto: cabecera de la navegación y un contenido de ejemplo. */
export function SketchPage({ href, children }: { href: string; children?: ReactNode }) {
  const item = NAV_ITEMS.find((i) => i.href === href);
  if (!item) throw new Error(`Sin entrada de navegación para ${href}`);
  return (
    <PageTransition>
      <PageHeader title={item.label} description={item.description} />
      {children ?? (
        <Panel>
          <EmptyState icon={PencilRuler} title="Boceto en curso">
            Esta sección se está diseñando. Los datos que muestre serán de ejemplo hasta que se conecte con el núcleo.
          </EmptyState>
        </Panel>
      )}
    </PageTransition>
  );
}
