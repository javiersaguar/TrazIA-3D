import { PencilRuler } from "lucide-react";
import type { ReactNode } from "react";
import { EmptyState, Icon, Panel } from "@/components/ui/primitives";
import { NAV_ITEMS } from "@/lib/nav";
import { PageHeader } from "./page-header";
import { PageTransition } from "./page-transition";

/** Aviso de las secciones en boceto: lo que se ve son datos de ejemplo. */
export function SketchNotice({ children }: { children?: ReactNode }) {
  return (
    <div
      role="note"
      className="mb-5 flex items-start gap-2.5 rounded-[var(--radius-card)] border border-warning-border bg-warning-bg px-4 py-2.5 text-[13px] text-warning"
    >
      <Icon icon={PencilRuler} className="mt-0.5" />
      <p>
        <span className="font-medium">Boceto · datos de ejemplo.</span>{" "}
        <span className="opacity-90">{children ?? "Esta pantalla aún no está conectada con el núcleo de TrazIA-3D."}</span>
      </p>
    </div>
  );
}

/** Página de una sección en boceto: cabecera de la navegación, aviso y contenido de ejemplo. */
export function SketchPage({ href, note, children }: { href: string; note?: ReactNode; children?: ReactNode }) {
  const item = NAV_ITEMS.find((i) => i.href === href);
  if (!item) throw new Error(`Sin entrada de navegación para ${href}`);
  return (
    <PageTransition>
      <PageHeader title={item.label} description={item.description} />
      {children ? (
        <>
          <SketchNotice>{note}</SketchNotice>
          {children}
        </>
      ) : (
        <Panel>
          <EmptyState icon={PencilRuler} title="Boceto en curso">
            Esta sección se está diseñando. Los datos que muestre serán de ejemplo hasta que se conecte con el núcleo.
          </EmptyState>
        </Panel>
      )}
    </PageTransition>
  );
}
