"use client";

import * as Dialog from "@radix-ui/react-dialog";
import dynamic from "next/dynamic";

import { Button } from "@/components/ui/primitives";

const IfcViewer = dynamic(() => import("@/features/viewer3d").then((m) => m.IfcViewer), {
  ssr: false,
  loading: () => <p role="status" className="p-4 text-sm text-muted">Cargando visor IFC…</p>,
});

export function SketchModelDialog({ tag, name, ifc }: { tag: string; name: string; ifc: string }) {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <button type="button" aria-label={`Ver 3D de ${tag}`}
          className="text-[12px] text-accent-text underline-offset-2 hover:underline">
          Ver 3D
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-[var(--scrim)]" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-50 flex max-h-[92dvh] w-[min(860px,calc(100%-2rem))] -translate-x-1/2 -translate-y-1/2 flex-col gap-3 overflow-auto rounded-xl border border-border bg-surface p-4 shadow-xl">
          <div className="flex items-start justify-between gap-3">
            <div>
              <Dialog.Title className="font-semibold text-strong">{name}</Dialog.Title>
              <Dialog.Description className="text-sm text-muted">{tag} · IFC4 conceptual sintético · DRAFT</Dialog.Description>
            </div>
            <Dialog.Close asChild><Button size="sm">Cerrar</Button></Dialog.Close>
          </div>
          <div className="relative h-[min(54dvh,520px)] min-h-[280px] overflow-hidden rounded-lg border border-border">
            <IfcViewer ifcUrl={ifc} />
          </div>
          <a href={ifc} download className="self-start text-sm text-accent-text underline-offset-2 hover:underline">
            Descargar IFC
          </a>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
