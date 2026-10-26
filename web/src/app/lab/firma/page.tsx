"use client";

import dynamic from "next/dynamic";
import Link from "next/link";

const Signature = dynamic(() => import("@/features/viewer3d/signature").then(m => m.Signature), { ssr: false });

export default function SignatureLab() {
  return <main className="mx-auto max-w-[1500px] space-y-5 p-6">
    <header className="flex items-center justify-between gap-4">
      <div><h1 className="text-2xl font-semibold">Del plano al acero</h1>
        <p className="mt-2 text-sm text-muted">Prototipo con el PDF y el IFC sintéticos de V-101. Las regiones iluminadas vienen del JSON.</p></div>
      <Link href="/lab/3d" className="text-sm text-accent-text">Volver al laboratorio</Link>
    </header>
    <div className="h-[calc(100dvh-180px)] min-h-[600px]"><Signature /></div>
    <p className="text-xs text-muted">La secuencia se inicia a petición, admite pausa y salto. Con movimiento reducido, muestra el modelo final directamente.</p>
  </main>;
}
