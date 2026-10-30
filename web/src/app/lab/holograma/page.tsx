"use client";
import dynamic from "next/dynamic";
import { useState } from "react";
const HologramToReal = dynamic(() => import("@/features/hologram").then(m => m.HologramToReal), { ssr:false });
export default function HologramLab() {
 const [source,setSource]=useState<"procedural"|"ifc">("procedural");
 const [layout,setLayout]=useState<"side"|"inplace">("side");
 return <main className="mx-auto max-w-[1600px] space-y-4 p-6"><h1 className="text-2xl font-semibold">Holograma y materialización</h1>
  <div className="flex gap-3">{(["procedural","ifc"] as const).map(v=><button className="rounded-lg border border-border px-4 py-2" key={v} onClick={()=>setSource(v)}>{v}</button>)}
  <button className="rounded-lg border border-border px-4 py-2" onClick={()=>setLayout(v=>v==="side"?"inplace":"side")}>Cambiar disposición</button></div>
  <div className="h-[780px] rounded-xl border border-border"><HologramToReal source={source} layout={layout}/></div>
 </main>;
}
