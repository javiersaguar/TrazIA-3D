import { IfcAPI } from "web-ifc";
import { readIfcModel } from "./ifc-parse";
import type { LoadRequest, WorkerReply } from "./ifc-protocol";

const scope = self as unknown as DedicatedWorkerGlobalScope;

function reply(message: WorkerReply, transfer: Transferable[] = []) {
  scope.postMessage(message, transfer);
}

scope.onmessage = async ({ data }: MessageEvent<LoadRequest>) => {
  if (data.type !== "load") return;
  const api = new IfcAPI();
  let modelId: number | undefined;
  let initialized = false;
  try {
    reply({ type: "progress", progress: 0.05, message: "Leyendo IFC" });
    const compressed = data.gzipUrl && typeof DecompressionStream === "function"
      ? await fetch(data.gzipUrl).catch(() => undefined)
      : undefined;
    const response = compressed?.ok && compressed.body ? compressed : await fetch(data.url);
    if (!response.ok) throw new Error(`No se pudo leer el IFC (${response.status})`);
    const buffer = response === compressed && response.body
      ? await new Response(response.body.pipeThrough(new DecompressionStream("gzip"))).arrayBuffer()
      : await response.arrayBuffer();
    if (buffer.byteLength > 25 * 1024 * 1024) throw new Error("El visor de demo admite IFC de hasta 25 MB");
    const start = performance.now();
    api.SetWasmPath(data.wasmPath, true);
    await api.Init(undefined, true);
    initialized = true;
    modelId = api.OpenModel(new Uint8Array(buffer), { COORDINATE_TO_ORIGIN: false, CIRCLE_SEGMENTS: 24 });
    if (modelId < 0) throw new Error("El archivo no se pudo abrir como IFC");
    const model = readIfcModel(api, modelId, { url: data.url, bytes: buffer.byteLength, start,
      onProgress: (progress, message) => reply({ type: "progress", progress, message }) });
    const transfer = model.products.flatMap(p => p.parts.flatMap(part =>
      [part.positions.buffer, part.normals.buffer, part.indices.buffer] as ArrayBuffer[]));
    reply({ type: "ready", model }, transfer);
  } catch (error) {
    reply({ type: "error", message: error instanceof Error ? error.message : "No se pudo cargar el IFC" });
  } finally {
    if (modelId !== undefined && modelId >= 0) api.CloseModel(modelId);
    if (initialized) api.Dispose();
  }
};
