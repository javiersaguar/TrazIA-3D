"use client";

import dynamic from "next/dynamic";

import { FullscreenFrame } from "@/components/shell/fullscreen";

const Signature = dynamic(() => import("@/features/viewer3d/signature").then((m) => m.Signature), { ssr: false });

export default function SignatureLab() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-strong">Del plano al modelo</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted">
          Prototipo con el PDF y el IFC sintéticos de V-101. Las regiones iluminadas vienen del JSON. La secuencia se inicia a petición y
          admite pausa y salto; con movimiento reducido, muestra el modelo final directamente.
        </p>
      </div>
      <FullscreenFrame height="h-[calc(100dvh-230px)] min-h-[560px]" testId="signature-frame">
        <Signature />
      </FullscreenFrame>
    </div>
  );
}
