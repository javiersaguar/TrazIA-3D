import { Matrix3, Matrix4, Vector3 } from "three";
import { IfcAPI } from "web-ifc";
import { semanticId } from "../features/viewer3d/semantic";
import type { Bounds, IfcModel, IfcPart, IfcProduct, LoadRequest, PropertySets, WorkerReply } from "./ifc-protocol";

type StepValue = { value?: string | number | boolean };
type StepLine = { GlobalId?: StepValue; Name?: StepValue; type: number };
type Pset = { Name?: StepValue; HasProperties?: { Name?: StepValue; NominalValue?: StepValue }[] };
const scope = self as unknown as DedicatedWorkerGlobalScope;
const emptyBounds = (): Bounds => ({ min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] });

function include(bounds: Bounds, x: number, y: number, z: number) {
  bounds.min = [Math.min(bounds.min[0], x), Math.min(bounds.min[1], y), Math.min(bounds.min[2], z)];
  bounds.max = [Math.max(bounds.max[0], x), Math.max(bounds.max[1], y), Math.max(bounds.max[2], z)];
}

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
    const response = await fetch(data.url);
    if (!response.ok) throw new Error(`No se pudo leer el IFC (${response.status})`);
    const buffer = await response.arrayBuffer();
    if (buffer.byteLength > 25 * 1024 * 1024) throw new Error("El visor de demo admite IFC de hasta 25 MB");
    const start = performance.now();
    api.SetWasmPath(data.wasmPath, true);
    await api.Init(undefined, true);
    initialized = true;
    modelId = api.OpenModel(new Uint8Array(buffer), { COORDINATE_TO_ORIGIN: false, CIRCLE_SEGMENTS: 24 });
    if (modelId < 0) throw new Error("El archivo no se pudo abrir como IFC");
    const products: IfcProduct[] = [];
    const bounds = emptyBounds();
    const matrix = new Matrix4();
    const normalMatrix = new Matrix3();
    const point = new Vector3();
    const normal = new Vector3();
    let triangles = 0;
    api.StreamAllMeshes(modelId, (mesh, index, total) => {
      const line = api.GetLine(modelId!, mesh.expressID) as StepLine;
      const productBounds = emptyBounds();
      const parts: IfcPart[] = [];
      for (let i = 0; i < mesh.geometries.size(); i++) {
        const placed = mesh.geometries.get(i);
        const geometry = api.GetGeometry(modelId!, placed.geometryExpressID);
        try {
          const interleaved = api.GetVertexArray(geometry.GetVertexData(), geometry.GetVertexDataSize());
          const indices = new Uint32Array(api.GetIndexArray(geometry.GetIndexData(), geometry.GetIndexDataSize()));
          const positions = new Float32Array(interleaved.length / 2);
          const normals = new Float32Array(positions.length);
          matrix.fromArray(placed.flatTransformation);
          normalMatrix.getNormalMatrix(matrix);
          for (let j = 0; j < interleaved.length / 6; j++) {
            point.fromArray(interleaved, j * 6).applyMatrix4(matrix);
            normal.fromArray(interleaved, j * 6 + 3).applyNormalMatrix(normalMatrix);
            // web-ifc ya incorpora la conversión IFC Z → Y en flatTransformation.
            positions.set([point.x, point.y, point.z], j * 3);
            normals.set([normal.x, normal.y, normal.z], j * 3);
            include(productBounds, point.x, point.y, point.z);
            include(bounds, point.x, point.y, point.z);
          }
          parts.push({ positions, normals, indices,
            color: [placed.color.x, placed.color.y, placed.color.z, placed.color.w] });
          triangles += indices.length / 3;
        } finally {
          geometry.delete();
        }
      }
      if (parts.length) {
        const center = productBounds.min.map((v, i) => (v + productBounds.max[i]!) / 2) as [number, number, number];
        for (const part of parts) {
          for (let j = 0; j < part.positions.length; j += 3) {
            part.positions[j]! -= center[0];
            part.positions[j + 1]! -= center[1];
            part.positions[j + 2]! -= center[2];
          }
        }
        const name = String(line.Name?.value ?? `#${mesh.expressID}`);
        const ifcType = api.GetNameFromTypeCode(line.type);
        products.push({ expressId: mesh.expressID, globalId: String(line.GlobalId?.value ?? ""),
          name, ifcType, semanticId: semanticId(name, ifcType), psets: {}, center,
          bounds: productBounds, parts });
      }
      if (index % 4 === 0) reply({ type: "progress", progress: 0.2 + 0.6 * (index + 1) / Math.max(1, total), message: "Leyendo geometría y propiedades" });
    }, true);
    if (!products.length) throw new Error("El IFC no contiene productos con geometría visible");
    if (new Set(products.map(product => product.globalId)).size !== products.length || products.some(product => !product.globalId)) {
      throw new Error("El IFC contiene GlobalId vacíos o duplicados; revisa su identidad antes de compararlo");
    }
    for (const product of products) {
      const sets = await api.properties.getPropertySets(modelId, product.expressId, true) as Pset[];
      const psets: PropertySets = {};
      for (const set of sets) {
        const properties: PropertySets[string] = {};
        for (const prop of set.HasProperties ?? []) {
          properties[String(prop.Name?.value ?? "")] = prop.NominalValue?.value ?? null;
        }
        psets[String(set.Name?.value ?? "")] = properties;
      }
      product.psets = psets;
      product.semanticId = semanticId(product.name, product.ifcType, psets);
    }
    const model: IfcModel = { url: data.url, schema: api.GetModelSchema(modelId), products, bounds,
      triangles, bytes: buffer.byteLength, parseMs: performance.now() - start };
    const transfer = products.flatMap(p => p.parts.flatMap(part =>
      [part.positions.buffer, part.normals.buffer, part.indices.buffer] as ArrayBuffer[]));
    reply({ type: "ready", model }, transfer);
  } catch (error) {
    reply({ type: "error", message: error instanceof Error ? error.message : "No se pudo cargar el IFC" });
  } finally {
    if (modelId !== undefined && modelId >= 0) api.CloseModel(modelId);
    if (initialized) api.Dispose();
  }
};
