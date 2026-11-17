import { IfcAPI } from "web-ifc";

import { designMeshes, type DesignSpec } from "../features/model-designs/parametric";
import { renderableParts, writeDesignIfc } from "../features/model-designs/ifc-writer";

/*
  Genera el IFC de un diseño paramétrico fuera del hilo principal. Mantiene WebIFC iniciado entre
  peticiones para que cada cambio tarde milisegundos; solo responde a la última petición.
*/

export type BuildRequest = { type: "build"; requestId: number; design: DesignSpec; edited: boolean; wasmPath: string };
export type BuildReply =
  | { type: "built"; requestId: number; bytes: ArrayBuffer; filename: string; parts: number; ms: number }
  | { type: "error"; requestId: number; message: string };

const scope = self as unknown as DedicatedWorkerGlobalScope;
let api: Promise<IfcAPI> | null = null;
let latest = 0;

function ready(wasmPath: string) {
  api ??= (async () => {
    const instance = new IfcAPI();
    instance.SetWasmPath(wasmPath, true);
    await instance.Init(undefined, true);
    return instance;
  })();
  return api;
}

scope.onmessage = async ({ data }: MessageEvent<BuildRequest>) => {
  if (data.type !== "build") return;
  latest = data.requestId;
  const start = performance.now();
  try {
    const ifc = await ready(data.wasmPath);
    if (data.requestId !== latest) return;
    const meshes = designMeshes(data.design);
    const { bytes, filename } = await writeDesignIfc(ifc, data.design, meshes, data.edited);
    const check = renderableParts(ifc, bytes);
    if (check.products !== meshes.length || check.rendered !== meshes.length) {
      throw new Error(`${check.rendered} de ${meshes.length} piezas con geometría en el IFC generado`);
    }
    const buffer = bytes.slice().buffer;
    const reply: BuildReply = { type: "built", requestId: data.requestId, bytes: buffer, filename,
      parts: meshes.length, ms: performance.now() - start };
    scope.postMessage(reply, [buffer]);
  } catch (error) {
    scope.postMessage({ type: "error", requestId: data.requestId, message: (error as Error).message } satisfies BuildReply);
  }
};
