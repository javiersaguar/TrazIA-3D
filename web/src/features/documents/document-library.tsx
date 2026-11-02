"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { FolderOpen, Plus, Shapes, FileUp } from "lucide-react";
import { toast } from "sonner";
import { Badge, Button, Icon, Panel, PanelHeader } from "@/components/ui/primitives";
import { useMounted } from "@/lib/use-mounted";
import { useCatalogue, saveDocument, loadDocument } from "./catalogue";

const inputClass="w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm text-text";
export function DocumentLibrary() {
 const catalogue=useCatalogue(), mounted=useMounted();
 const [family,setFamily]=useState("all"),[project,setProject]=useState("all"),[query,setQuery]=useState("");
 const [form,setForm]=useState<"family"|"project"|"design"|null>(null),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 const designs=mounted?catalogue.designs:[];
 const relevant=designs.filter(d=>family==="all"||d.family===family);
 const projects=catalogue.projects.filter(p=>relevant.some(d=>d.project===p.id));
 const visible=relevant.filter(d=>(project==="all"||d.project===project)&&`${d.name} ${d.filename??""}`.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
 async function submit(event:FormEvent<HTMLFormElement>) {
  event.preventDefault();const element=event.currentTarget,data=new FormData(element),name=String(data.get("name")??"").trim();
  if(!name)return;setError("");setBusy(true);
  try {
   if(form==="family"){const id=catalogue.addFamily(name);setFamily(id);setProject("all");}
   if(form==="project"){catalogue.addProject(name);setProject("all");}
   if(form==="design"){
    const file=data.get("file");if(!(file instanceof File)||!file.size)throw new Error("Selecciona un documento para el diseño.");
    if(file.size>50*1024*1024)throw new Error("El documento supera 50 MB. Selecciona un archivo más pequeño.");
    const id=crypto.randomUUID();await saveDocument(id,file);
    catalogue.addDesign({id,name,family:String(data.get("family")),project:String(data.get("project")),filename:file.name,size:file.size});
    setFamily(String(data.get("family")));setProject("all");
   }
   setForm(null);toast.success("Guardado en este navegador");
  }catch(e){setError(e instanceof Error?e.message:"No se pudo guardar. Comprueba el espacio disponible del navegador.");}finally{setBusy(false);}
 }
 async function download(id:string,name:string){
  try {const blob=await loadDocument(id);if(!blob)throw new Error("El documento no está disponible en este navegador. Vuelve a añadirlo.");
   const url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }catch(e){toast.error(e instanceof Error?e.message:"No se pudo abrir el documento");}
 }
 if(!mounted)return <p role="status" className="p-6 text-sm text-muted">Cargando catálogo…</p>;
 return <div className="space-y-6">
  <header className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-2xl font-semibold text-strong">Documentos</h1><p className="mt-2 max-w-2xl text-sm text-muted">Organiza cada diseño por familia y proyecto. Los archivos se conservan en este navegador y no se envían a servicios externos.</p></div>
   <div className="flex flex-wrap gap-2"><Button onClick={()=>{setForm("family");setError("");}}><Icon icon={Shapes}/> Nueva familia</Button><Button onClick={()=>{setForm("project");setError("");}}><Icon icon={FolderOpen}/> Nuevo proyecto</Button><Button variant="primary" onClick={()=>{setForm("design");setError("");}}><Icon icon={FileUp}/> Añadir diseño</Button></div>
  </header>
  {form?<Panel className="p-5"><form onSubmit={submit} className="grid gap-4 sm:grid-cols-2" aria-label={form==="family"?"Nueva familia":form==="project"?"Nuevo proyecto":"Añadir diseño"}>
   <h2 className="text-lg font-semibold sm:col-span-2">{form==="family"?"Nueva familia":form==="project"?"Nuevo proyecto":"Añadir diseño"}</h2>
   <label className="space-y-2 text-sm">Nombre<input name="name" required maxLength={120} className={inputClass}/></label>
   {form==="design"?<><label className="space-y-2 text-sm">Documento<input type="file" name="file" required accept=".pdf,.xlsx,.xls,.ifc,.png,.jpg,.jpeg" className={inputClass}/></label>
    <label className="space-y-2 text-sm">Familia<select aria-label="Familia" name="family" defaultValue={family==="all"?"vertical":family} className={inputClass}>{catalogue.families.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select></label>
    <label className="space-y-2 text-sm">Proyecto<select aria-label="Proyecto" name="project" defaultValue={project==="all"?"demo":project} className={inputClass}>{catalogue.projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label></>:null}
   {form==="family"?<p className="text-sm text-muted">Puedes clasificar documentos en una familia nueva. La creación de una plantilla geométrica se revisa por separado.</p>:null}
   {error?<p role="alert" className="text-sm text-danger sm:col-span-2">{error}</p>:null}
   <div className="flex gap-2 sm:col-span-2"><Button type="submit" variant="primary" disabled={busy}><Icon icon={Plus}/>{busy?"Guardando…":"Guardar"}</Button><Button onClick={()=>setForm(null)}>Cancelar</Button></div>
  </form></Panel>:null}
  <div className="grid gap-5 xl:grid-cols-[230px_minmax(0,1fr)]">
   <Panel className="h-fit p-3"><h2 className="px-2 py-2 text-sm font-semibold">Familias</h2><nav aria-label="Familias de documentos" className="space-y-1">{[{id:"all",name:"Todas las familias"},...catalogue.families].map(f=><button key={f.id} onClick={()=>{setFamily(f.id);setProject("all");}} aria-pressed={family===f.id} className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm ${family===f.id?"bg-accent-soft text-accent-text":"text-muted hover:bg-surface-raised"}`}><span>{f.name}</span><span className="font-mono text-xs">{designs.filter(d=>f.id==="all"||d.family===f.id).length}</span></button>)}</nav></Panel>
   <div className="min-w-0 space-y-4"><Panel><PanelHeader title="Proyectos" description="Proyectos que contienen diseños de la familia seleccionada."/><div className="flex flex-wrap gap-2 px-5 pb-4"><Button onClick={()=>setProject("all")} aria-pressed={project==="all"}>Todos</Button>{projects.map(p=><Button key={p.id} onClick={()=>setProject(p.id)} aria-pressed={project===p.id}>{p.name}</Button>)}{!projects.length?<p className="text-sm text-muted">Esta familia aún no tiene diseños. Añade uno para asociar su proyecto.</p>:null}</div></Panel>
    <Panel><PanelHeader title="Diseños y documentos" actions={<input type="search" aria-label="Buscar diseños" placeholder="Buscar diseño o archivo" value={query} onChange={e=>setQuery(e.target.value)} className={inputClass}/>}/>
     <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-y border-border text-muted"><tr>{["Diseño","Familia","Proyecto","Documento"].map(h=><th key={h} className="px-5 py-3 font-medium">{h}</th>)}</tr></thead><tbody>{visible.map(d=><tr key={d.id} className="border-b border-border last:border-0"><td className="px-5 py-4"><span className="block font-medium">{d.name}</span>{d.demo?<Badge tone="warning">Datos sintéticos</Badge>:<span className="text-xs text-muted">Guardado localmente</span>}</td><td className="px-5 py-4"><select aria-label={`Familia de ${d.name}`} className={inputClass} value={d.family} onChange={e=>catalogue.assign(d.id,e.target.value,d.project)}>{catalogue.families.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select></td><td className="px-5 py-4"><select aria-label={`Proyecto de ${d.name}`} className={inputClass} value={d.project} onChange={e=>catalogue.assign(d.id,d.family,e.target.value)}>{catalogue.projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></td><td className="px-5 py-4">{d.demo?<Link className="text-accent-text underline underline-offset-4" href="/modelo">Abrir V-101</Link>:<button className="text-accent-text underline underline-offset-4" onClick={()=>download(d.id,d.filename!)}>{d.filename}</button>}</td></tr>)}</tbody></table></div>
     {!visible.length?<p className="p-6 text-sm text-muted">No hay diseños con estos filtros. Añade un diseño o elige otra familia.</p>:null}
    </Panel></div>
  </div>
 </div>;
}
