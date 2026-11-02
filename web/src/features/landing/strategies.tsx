"use client";
import { useState } from "react";
import { ChevronDown } from "lucide-react";
import study from "@/lib/data/study-summary.json";
const rows=[
 {id:"A",variant:"a_geometria",name:"Visión + 3D",text:"Geometría desde los trazos, escala desde cotas y cruce de alzado y planta.",scope:"Variante geométrica sin modelo multimodal; Qwen se midió en otro subconjunto."},
 {id:"B",variant:"b_reglas+ocr",name:"Datos + reglas",text:"Texto, tablas, cotas, cajetín y hoja de datos, con OCR para los escaneados.",scope:"B con OCR en CPU."},
 {id:"C",variant:"c_rag",name:"RAG",text:"Recupera una plantilla y busca la evidencia en el documento actual.",scope:"Recuperación por huella ligera; ColQwen2 permanece desactivado."},
 {id:"D",variant:"d_hibrido",name:"Híbrido",text:"Combina reglas, recuperación, geometría y memoria con fusión aprendida.",scope:"Fusión aprendida y calibración v6."},
];
const fmt=(v:number|null|undefined,d=3)=>v==null?"Sin medir":v.toLocaleString("es-ES",{minimumFractionDigits:d,maximumFractionDigits:d});
const pct=(v:number|null|undefined)=>v==null?"Sin medir":`${fmt(v*100,1)} %`;
export function Strategies(){
 const [hovered,setHovered]=useState<string|null>(null);
 const [focused,setFocused]=useState<string|null>(null);
 const active=hovered??focused;
 return <section id="estrategias" aria-labelledby="estrategias-titulo" className="relative z-[2] mx-auto w-full max-w-[1240px] scroll-mt-20 px-5 py-24 md:px-8 md:py-32">
  <div className="grid gap-6 lg:grid-cols-2"><h2 id="estrategias-titulo" className="landing-display text-[clamp(32px,4.2vw,56px)] leading-none text-strong">Cuatro maneras de leer un plano</h2><div><p className="text-base leading-relaxed text-muted">Las mismas entradas, cuatro enfoques. Explora cada opción para consultar sus métricas y el alcance de la medición.</p><p className="mt-3 text-xs text-warning">{study.study} · {study.generated_at.slice(0,10).split("-").reverse().join("/")} · Datos sintéticos · no planos de TR</p></div></div>
  <div className="mt-10 divide-y divide-border overflow-hidden rounded-2xl border border-border bg-surface">{rows.map(row=>{
   const v=study.variants.find(v=>v.id===row.variant)!,m=v.metrics,expanded=active===row.id;
   return <div key={row.id} onMouseEnter={()=>setHovered(row.id)} onMouseLeave={()=>setHovered(null)} onFocus={()=>setFocused(row.id)} onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget))setFocused(null);}} onKeyDown={e=>{if(e.key==="Escape"){setHovered(null);setFocused(null);}}} className={expanded?"bg-surface-raised":""}>
    <button type="button" aria-expanded={expanded} aria-controls={`metrics-${row.id}`} onClick={()=>setFocused(row.id)} className="flex w-full items-start gap-5 p-5 text-left md:items-center md:p-7"><span className="flex size-11 shrink-0 items-center justify-center rounded-full border border-accent font-mono text-accent-text">{row.id}</span><span className="min-w-0 flex-1"><strong className="text-base text-strong">{row.name}</strong><span className="mt-1 block text-sm leading-relaxed text-muted">{row.text}</span></span><span className="text-right"><span className="block text-xs text-muted">Puntuación</span><strong className="font-mono text-xl text-strong">{fmt(m.score)}</strong></span><ChevronDown className="mt-1 size-4 shrink-0 text-muted"/></button>
    <div id={`metrics-${row.id}`} hidden={!expanded} className="border-t border-border px-6 py-5 md:pl-[100px]"><dl className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-6">{[["Atributos",pct(m.attributes)],["Geometría",pct(m.geometry)],["Alucinación",pct(m.hallucination_rate)],["Cita correcta",pct(m.citation_coverage)],["F1 de cambios",fmt(m.f1_delta)],["Cobertura de intervalos",pct(m.interval_coverage)],["API · €/equipo",fmt(m.cost_eur_per_equipment,4)],["ECE",fmt(m.ece)],["Segundos/revisión",fmt(m.seconds_per_revision,2)]].map(([label,value])=><div key={label}><dt className="text-xs text-muted">{label}</dt><dd className="mt-1 font-mono text-lg text-strong">{value}</dd></div>)}</dl><p className="mt-4 text-xs text-muted">IC95 de puntuación: [{fmt(v.ci95.score[0])}; {fmt(v.ci95.score[1])}]. {row.scope} Conjuntos: {study.datasets.join(", ")}. La puntuación geométrica no es el porcentaje de IFC aprobados. El coste de proveedores excluye cómputo y revisión.</p></div>
   </div>;
  })}</div>
 </section>;
}
