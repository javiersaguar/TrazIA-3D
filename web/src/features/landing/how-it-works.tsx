"use client";
import { motion, useScroll, useTransform, type MotionValue } from "motion/react";
import { useMotionPreference } from "@/lib/use-motion-preference";
import { useRef } from "react";
import { DrawPath } from "@/components/motion/draw-path";
const steps=[
 {title:"Plano",text:"Sube el plano GA y sus hojas de datos. Se leen texto, tablas y cotas; el OCR entra cuando el documento está escaneado."},
 {title:"Evidencia",text:"Cada valor conserva unidad, página, región y confianza. Puedes volver al recorte que explica la lectura."},
 {title:"Modelo",text:"La geometría IFC queda como borrador. Una persona contrasta los campos y resuelve lo que falta antes de aprobar."},
 {title:"Cambios",text:"Una nueva revisión muestra dónde cambia el equipo, cuánto cambia y qué disciplinas se ven afectadas."},
];
const vessel="M70 34 C70 12 126 12 126 34 L126 100 C126 122 70 122 70 100 Z";
function Art({step}:{step:number}) {
 const color=step===2?"var(--accent)":"var(--sheet-ink)";
 return <svg viewBox="0 0 220 150" className="h-full w-full" role="img" aria-label={["Plano de recipiente acotado","Cota conectada a su lectura","Recipiente IFC con boquillas","Dos revisiones y una variación de altura"][step]}>
  <g fill="none" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
   {step===0?<><rect x="12" y="10" width="196" height="130" stroke="var(--sheet-thin)"/><path d="M12 118H208M140 118V140M175 118V140M140 129H208" stroke="var(--sheet-thin)"/></>:null}
   {step<3?<><DrawPath inView d={vessel} stroke={color} fill={step===2?"var(--accent-soft)":"none"} duration={.8}/><DrawPath inView d="M70 95V123H126V95M62 123H134M126 65H148V56H153V74H148M70 84H52V78H47V91H52" stroke={color} duration={.8} delay={.15}/><path d="M98 9V130" stroke="var(--sheet-thin)" strokeDasharray="6 3 1 3"/></>:null}
   {step===0||step===1?<><path d="M70 25V9M126 25V9M70 14H126M64 14L70 12V16ZM132 14L126 12V16Z" stroke="var(--accent)"/><text x="98" y="8" fill="var(--text)" stroke="none" fontSize="8" textAnchor="middle">Ø2000</text></>:null}
   {step===1?<><rect x="64" y="3" width="68" height="19" rx="3" stroke="var(--accent)" strokeDasharray="3 2"/><DrawPath inView d="M132 14C172 14 150 52 168 52" stroke="var(--accent)" delay={.3}/><rect x="146" y="53" width="66" height="42" rx="6" stroke="var(--border-strong)" fill="var(--surface)"/><text x="179" y="70" fill="var(--text)" stroke="none" fontSize="9" textAnchor="middle">2000 mm</text><path d="M154 82H202" stroke="var(--accent)" strokeWidth="3"/></>:null}
   {step===2?<><path d="M70 34C70 44 126 44 126 34M70 100C70 110 126 110 126 100" stroke="var(--accent)"/><text x="164" y="133" fill="var(--text-muted)" stroke="none" fontSize="9">IFC4</text><circle cx="151" cy="65" r="7" stroke="var(--accent)"/></>:null}
   {step===3?<><DrawPath inView d="M36 50C36 32 88 32 88 50V119H36ZM31 119H93" stroke="var(--sheet-ink)"/><DrawPath inView d="M132 30C132 12 184 12 184 30V119H132ZM127 119H189" stroke="var(--revision)" delay={.2}/><path d="M90 30H123M90 50H123M115 30V50M111 34L115 30L119 34M111 46L115 50L119 46" stroke="var(--revision)"/><text x="97" y="71" fill="var(--revision)" stroke="none" fontSize="9">+500 mm</text><text x="62" y="136" fill="var(--text-muted)" stroke="none" fontSize="10">A</text><text x="158" y="136" fill="var(--revision)" stroke="none" fontSize="10">B</text></>:null}
  </g>
 </svg>;
}
function Step({index,progress}:{index:number;progress:MotionValue<number>}) {
 const reduce=useMotionPreference(),opacity=useTransform(progress,[index*.13,index*.13+.22],[.15,1]);
 const transform=useTransform(progress,[index*.13,index*.13+.22],["translateY(18px)","translateY(0px)"]);
 const step=steps[index]!;
 return <li className="process-step relative min-w-0"><span className="relative z-[2] flex size-8 items-center justify-center rounded-full border border-accent bg-bg font-mono text-sm text-accent-text">{index+1}</span><h3 className="mt-5 text-lg font-semibold text-strong">{step.title}</h3><p className="mt-2 min-h-[100px] text-sm leading-relaxed text-muted">{step.text}</p><motion.div style={{opacity:reduce?1:opacity,transform:reduce?"none":transform}} className="drafting-grid mt-5 max-lg:max-w-[520px] aspect-[22/15] overflow-hidden rounded-xl border border-border"><Art step={index}/></motion.div></li>;
}
export function HowItWorks(){
 const ref=useRef<HTMLElement>(null),reduce=useMotionPreference();
 const {scrollYProgress}=useScroll({target:ref,offset:["start 90%","end 70%"]});
 return <section ref={ref} id="como-funciona" aria-labelledby="como-titulo" className="relative z-[2] mx-auto w-full max-w-[1240px] scroll-mt-20 px-5 py-24 md:px-8 md:py-32"><h2 id="como-titulo" className="landing-display text-[clamp(32px,4.2vw,56px)] leading-none text-strong">Cómo funciona</h2><p className="mt-4 text-base text-muted">Cuatro pasos, del PDF al modelo que revisa una persona.</p><div className="relative mt-14"><div aria-hidden className="absolute top-4 right-[calc(25%-40px)] left-4 hidden h-px bg-border-strong lg:block"><motion.div className="absolute inset-0 origin-left bg-accent" style={{scaleX:reduce?1:scrollYProgress}}/></div><ol className="grid gap-12 lg:grid-cols-4 lg:gap-8">{steps.map((s,i)=><Step key={s.title} index={i} progress={scrollYProgress}/>)}</ol></div></section>;
}
