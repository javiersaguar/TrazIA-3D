import { Suspense } from "react";
import { ModelWorkbench } from "@/features/workspace/model-workbench";
export default function Page(){ return <Suspense fallback={<p>Cargando el modelo…</p>}><ModelWorkbench /></Suspense>; }
