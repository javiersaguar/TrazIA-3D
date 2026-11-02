"use client";

import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { Skeleton } from "@/components/ui/primitives";
import { Segmented } from "@/components/ui/controls";

const loading = () => <Skeleton className="h-[620px]" />;
const Review = dynamic(() => import("@/features/review/review-workspace").then(m => m.ReviewWorkspace), { ssr: false, loading });
const Changes = dynamic(() => import("@/features/changes/changes-workspace").then(m => m.ChangesWorkspace), { ssr: false, loading });
const Model = dynamic(() => import("@/features/hologram/model-workspace").then(m => m.ModelWorkspace), { ssr: false, loading });

export function ModelWorkbench() {
  const params = useSearchParams(), router = useRouter();
  const view = params.get("vista") ?? "revision";
  const active = ["revision", "cambios", "3d"].includes(view) ? view : "revision";
  return <div className="space-y-5">
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div><h1 className="text-2xl font-semibold text-strong">Modelo</h1><p className="mt-2 text-sm text-muted">Evidencia, revisiones y geometría IFC del equipo activo.</p></div>
      <Segmented label="Espacio del modelo" value={active} onChange={value => router.replace(`/modelo?vista=${value}`, { scroll: false })}
        options={[{value:"revision",label:"Revisión"},{value:"cambios",label:"Cambios"},{value:"3d",label:"Modelo 3D"}]} />
    </header>
    {active === "revision" ? <Review /> : active === "cambios" ? <Changes /> : <Model />}
  </div>;
}
