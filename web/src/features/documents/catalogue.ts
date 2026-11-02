import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Family = { id: string; name: string; custom?: boolean };
export type Project = { id: string; name: string };
export type Design = { id: string; name: string; family: string; project: string; filename?: string; demo?: boolean; size?: number };
export const FAMILIES: Family[] = [
  {id:"vertical",name:"Recipientes verticales"},{id:"horizontal",name:"Recipientes horizontales"},
  {id:"column",name:"Columnas"},{id:"exchanger",name:"Intercambiadores"},{id:"tank",name:"Tanques"},
  {id:"pump",name:"Bombas"},{id:"compressor",name:"Compresores"},{id:"generic",name:"Envolventes de reserva"},
];
type Catalogue = {
 families: Family[]; projects: Project[]; designs: Design[];
 addFamily(name: string): string; addProject(name: string): string;
 addDesign(design: Design): void; assign(id: string, family: string, project: string): void;
};
export const useCatalogue = create<Catalogue>()(persist((set) => ({
 families:FAMILIES, projects:[{id:"demo",name:"DEMO-PLANT"}],
 designs:[{id:"demo-v101",name:"V-101 · revisiones A/B",family:"vertical",project:"demo",demo:true}],
 addFamily: name => {const id=crypto.randomUUID();set(s=>({families:[...s.families,{id,name:name.trim(),custom:true}]}));return id;},
 addProject: name => {const id=crypto.randomUUID();set(s=>({projects:[...s.projects,{id,name:name.trim()}]}));return id;},
 addDesign: design => set(s=>({designs:[...s.designs,design]})),
 assign: (id,family,project) => set(s=>({designs:s.designs.map(d=>d.id===id?{...d,family,project}:d)})),
}), { name:"trazia.catalogue.v1", version:1 }));

async function database() {
 return new Promise<IDBDatabase>((resolve,reject)=>{
  const request=indexedDB.open("trazia.documents.v1",1);
  request.onupgradeneeded=()=>request.result.createObjectStore("files");
  request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);
 });
}
export async function saveDocument(id: string, file: File) {
 const db=await database();
 try { await new Promise<void>((resolve,reject)=>{
  const tx=db.transaction("files","readwrite");tx.objectStore("files").put(file,id);
  tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);
 }); } finally { db.close(); }
}
export async function loadDocument(id: string): Promise<Blob | undefined> {
 const db=await database();
 try {return await new Promise((resolve,reject)=>{
  const request=db.transaction("files","readonly").objectStore("files").get(id);
  request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);
 });} finally { db.close(); }
}
