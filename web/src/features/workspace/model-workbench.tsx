"use client";

import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";

import { Segmented } from "@/components/ui/controls";
import { Skeleton } from "@/components/ui/primitives";

const loading = () => <Skeleton className="h-[620px]" />;
const Review = dynamic(() => import("@/features/review/review-workspace").then((m) => m.ReviewWorkspace), { ssr: false, loading });
const Changes = dynamic(() => import("@/features/changes/changes-workspace").then((m) => m.ChangesWorkspace), { ssr: false, loading });
const Model = dynamic(() => import("@/features/hologram/model-workspace").then((m) => m.ModelWorkspace), { ssr: false, loading });
const DesignEdit = dynamic(() => import("@/features/design-edit/design-edit").then((m) => m.DesignEditWorkspace), { ssr: false, loading });

type View = "revision" | "cambios" | "3d" | "editar";
const VIEWS: Record<View, { label: string; description: string }> = {
  revision: {
    label: "Revisión",
    description: "Cada valor con su evidencia en el plano y su elemento en 3D. Todo sale del JSON extraído y del IFC generado.",
  },
  cambios: {
    label: "Cambios",
    description: "Qué cambia de la rev A a la rev B, cuánto, dónde y a qué disciplinas afecta. Datos del delta del núcleo.",
  },
  "3d": {
    label: "Modelo 3D",
    description: "El IFC generado, su paso del holograma al acero y una galería de equipos ilustrativos.",
  },
  editar: {
    label: "Proponer cambios",
    description: "Cambia el diseño de un equipo o boquilla: se valida el lote, se previsualiza el IFC y, al confirmar, nace una revisión DRAFT nueva.",
  },
};

/** Revisión, Cambios y Modelo 3D en una sola pestaña, cada uno con todo su contenido. */
export function ModelWorkbench() {
  const params = useSearchParams();
  const router = useRouter();
  const raw = params.get("vista") as View | null;
  const active: View = raw && raw in VIEWS ? raw : "revision";
  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-strong">Modelo</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted">{VIEWS[active].description}</p>
        </div>
        <Segmented<View>
          label="Espacio del modelo"
          value={active}
          onChange={(value) => router.replace(`/modelo?vista=${value}`, { scroll: false })}
          options={(Object.keys(VIEWS) as View[]).map((value) => ({ value, label: VIEWS[value].label }))}
        />
      </header>
      {active === "revision" ? <Review /> : active === "cambios" ? <Changes /> : active === "editar" ? <DesignEdit /> : <Model />}
    </div>
  );
}
