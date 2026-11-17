"use client";

import { useEffect, useRef, useState } from "react";

import type { BuildReply, BuildRequest } from "@/workers/design-ifc.worker";
import type { DesignSpec } from "./parametric";

export type DesignIfc = {
  /** IFC que lee el visor: el publicado si no hay cambios, o el generado en este navegador. */
  url: string | null;
  filename: string | null;
  generated: boolean;
  building: boolean;
  parts: number | null;
  ms: number | null;
  error: string | null;
};

type Built = { design: DesignSpec; url: string; filename: string; parts: number; ms: number };
type Failed = { design: DesignSpec; message: string };

const DEBOUNCE_MS = 90;

/**
 * Regenera el IFC del diseño cada vez que cambia, en un worker y con WebIFC ya iniciado. Mientras
 * se escribe el nuevo, el anterior sigue disponible; las URL antiguas se liberan con retraso para
 * que el visor termine de leerlas.
 */
export function useDesignIfc(design: DesignSpec, edited: boolean): DesignIfc {
  const published = !edited && design.ifc ? design.ifc : null;
  const [built, setBuilt] = useState<Built | null>(null);
  const [failed, setFailed] = useState<Failed | null>(null);
  const worker = useRef<Worker | null>(null);
  const request = useRef(0);
  const requested = useRef<DesignSpec | null>(null);
  const urls = useRef<string[]>([]);

  useEffect(() => {
    const instance = new Worker(new URL("../../workers/design-ifc.worker.ts", import.meta.url), { type: "module" });
    worker.current = instance;
    instance.onmessage = ({ data }: MessageEvent<BuildReply>) => {
      const target = requested.current;
      if (data.requestId !== request.current || !target) return;
      if (data.type === "error") {
        setFailed({ design: target, message: data.message });
        return;
      }
      const url = URL.createObjectURL(new Blob([data.bytes], { type: "application/x-step" }));
      urls.current.push(url);
      for (const old of urls.current.splice(0, Math.max(0, urls.current.length - 3))) {
        setTimeout(() => URL.revokeObjectURL(old), 5000);
      }
      setBuilt({ design: target, url, filename: data.filename, parts: data.parts, ms: data.ms });
    };
    const created = urls.current;
    return () => {
      instance.terminate();
      worker.current = null;
      for (const url of created.splice(0)) URL.revokeObjectURL(url);
    };
  }, []);

  useEffect(() => {
    const id = ++request.current;
    if (published) return;
    const timer = setTimeout(() => {
      requested.current = design;
      const message: BuildRequest = { type: "build", requestId: id, design, edited,
        wasmPath: new URL("/wasm/", window.location.href).href };
      worker.current?.postMessage(message);
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [design, edited, published]);

  if (published) {
    return { url: published, filename: `${design.tag}-A.ifc`, generated: false, building: false,
      parts: design.parts.length, ms: null, error: null };
  }
  const error = failed?.design === design ? failed.message : null;
  const current = built?.design === design;
  return {
    url: built?.url ?? null,
    filename: built?.filename ?? null,
    generated: !!built,
    building: !current && !error,
    parts: built?.parts ?? null,
    ms: built?.ms ?? null,
    error,
  };
}
