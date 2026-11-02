"use client";
import { IfcViewer } from "@/components/three";
import { Segmented } from "@/components/ui/controls";
import { DEMO } from "@/lib/mock/api";
import { useSelection } from "@/stores/selection";
import { useUi } from "@/stores/ui";
export function ModelWorkspace(){
 const revision=useUi(s=>s.revision),setRevision=useUi(s=>s.setRevision);
 const selected=useSelection(s=>s.selectedId),select=useSelection(s=>s.setSelected);
 return <section className="space-y-4" data-testid="model-workspace"><div className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-warning">Datos sintéticos · V-101 · IFC DRAFT</p><Segmented label="Revisión del modelo" value={revision} onChange={setRevision} options={[{value:"A",label:"Rev A"},{value:"B",label:"Rev B"}]}/></div><div className="h-[min(75vh,800px)] min-h-[480px] overflow-hidden rounded-xl border border-border"><IfcViewer ifcUrl={DEMO.revisions[revision].ifc} selectedId={selected??undefined} onSelect={select}/></div><p className="text-sm text-muted">La geometría procede del IFC. Selecciona una pieza para consultar sus propiedades; la selección se mantiene al volver a Revisión.</p></section>;
}
