"use client";

import Link from "next/link";
import { toast } from "sonner";

import { Badge } from "@/components/ui/primitives";
import { loadDocument, sketchAssets, type Design } from "./catalogue";
import { SketchModelDialog } from "./sketch-model-dialog";

const action = "text-[12px] text-accent-text underline-offset-2 hover:underline";

async function download(id: string, filename: string) {
  try {
    const blob = await loadDocument(id);
    if (!blob) throw new Error("El documento no está disponible en este navegador. Vuelve a añadirlo.");
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    toast.error(error instanceof Error ? error.message : "No se pudo abrir el documento");
  }
}

export function DocumentActions({ design }: { design: Design }) {
  if (design.demo) return <Link className={action} href="/modelo">Abrir en Modelo</Link>;

  const assets = sketchAssets(design.id);
  if (assets) {
    const tag = design.tag ?? design.name;
    return (
      <span className="flex flex-wrap gap-x-3 gap-y-1">
        <a href={assets.pdf} target="_blank" rel="noopener" className={action}
          aria-label={`Abrir PDF de ${tag} (pestaña nueva)`}>
          Abrir PDF
        </a>
        {assets.ifc && <SketchModelDialog tag={tag} name={design.name} ifc={assets.ifc} />}
        {design.tag && <Link className={action} href={`/modelo?vista=disenos&diseno=${encodeURIComponent(design.tag)}`}
          aria-label={`Abrir ${tag} en Modelo › Diseños`}>
          Editar en Modelo
        </Link>}
      </span>
    );
  }
  if (design.example) return <Badge tone="warning">ejemplo</Badge>;

  const { id, filename } = design;
  if (!filename) return null;
  return (
    <button type="button" className={`max-w-full truncate font-mono ${action}`}
      onClick={() => void download(id, filename)}>
      {filename}
    </button>
  );
}
