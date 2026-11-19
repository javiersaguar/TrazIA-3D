import { Matrix3, Matrix4, Vector3 } from "three";
import type { IfcAPI } from "web-ifc";
import { semanticId } from "../features/viewer3d/semantic";
import type { Bounds, IfcAssembly, IfcModel, IfcPart, IfcProduct, PropertySets, PropertyValue, Vec3 } from "./ifc-protocol";

/*
  Lectura de un IFC ya abierto con web-ifc: geometría por producto, Psets, estilos por geometría y
  agregación entre elementos. Sin dependencias del worker para poder probarla en Node con el WASM
  de web-ifc. Solo importa tipos de web-ifc: los códigos de clase se piden al propio IfcAPI.
*/

type StepValue = { value?: string | number | boolean | null } | null | undefined;
type Handle = { value?: number } | null | undefined;
type StepLine = { type: number; GlobalId?: StepValue; Name?: StepValue; Tag?: StepValue; Description?: StepValue };
type PsetLine = StepLine & { HasProperties?: ({ Name?: StepValue; NominalValue?: StepValue } | Handle)[] };

/** Clases espaciales: un producto agregado en ellas no tiene padre «elemento». */
const SPATIAL = new Set([
  "IFCPROJECT", "IFCPROJECTLIBRARY", "IFCSITE", "IFCBUILDING", "IFCBUILDINGSTOREY", "IFCSPACE",
  "IFCFACILITY", "IFCFACILITYPART", "IFCBRIDGE", "IFCBRIDGEPART", "IFCROAD", "IFCROADPART",
  "IFCRAILWAY", "IFCRAILWAYPART", "IFCMARINEFACILITY", "IFCMARINEPART", "IFCEXTERNALSPATIALELEMENT",
  "IFCSPATIALZONE", "IFCSPATIALELEMENT", "IFCSPATIALSTRUCTUREELEMENT",
]);

const emptyBounds = (): Bounds => ({ min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] });
const centerOf = (bounds: Bounds): Vec3 => bounds.min.map((v, i) => (v + bounds.max[i]!) / 2) as Vec3;
const valueOf = (step: StepValue) => (step && step.value !== undefined && step.value !== null ? step.value : undefined);
const textOf = (step: StepValue) => {
  const value = valueOf(step);
  return value === undefined ? undefined : String(value);
};
const handles = (raw: unknown): number[] =>
  (Array.isArray(raw) ? raw : raw ? [raw] : [])
    .map((item) => (item && typeof item === "object" && "value" in item ? Number((item as { value: unknown }).value) : NaN))
    .filter(Number.isFinite);

function union(target: Bounds, other: Bounds) {
  for (let i = 0; i < 3; i++) {
    target.min[i] = Math.min(target.min[i]!, other.min[i]!);
    target.max[i] = Math.max(target.max[i]!, other.max[i]!);
  }
}

export type ReadOptions = {
  url: string;
  bytes: number;
  /** Instante (performance.now) en que empezó la lectura, para parseMs. */
  start: number;
  onProgress?(progress: number, message: string): void;
};

/** Mapas en una pasada por relación: evita una búsqueda inversa por producto. */
function propertySetsByElement(api: IfcAPI, modelId: number) {
  const result = new Map<number, PropertySets>();
  const cache = new Map<number, [string, Record<string, PropertyValue>]>();
  const rels = api.GetLineIDsWithType(modelId, api.GetTypeCodeFromName("IFCRELDEFINESBYPROPERTIES"));
  for (let i = 0; i < rels.size(); i++) {
    const rel = api.GetLine(modelId, rels.get(i)) as { RelatingPropertyDefinition?: unknown; RelatedObjects?: unknown };
    const related = handles(rel.RelatedObjects);
    for (const psetId of handles(rel.RelatingPropertyDefinition)) {
      let entry = cache.get(psetId);
      if (!entry) {
        const set = api.GetLine(modelId, psetId, true) as PsetLine;
        const properties: Record<string, PropertyValue> = {};
        for (const prop of set.HasProperties ?? []) {
          if (!prop || !("Name" in prop)) continue;
          const value = valueOf(prop.NominalValue);
          properties[String(valueOf(prop.Name) ?? "")] = value === undefined ? null : (value as PropertyValue);
        }
        entry = [String(valueOf(set.Name) ?? ""), properties];
        cache.set(psetId, entry);
      }
      for (const element of related) {
        const psets = result.get(element) ?? {};
        psets[entry[0]] = entry[1];
        result.set(element, psets);
      }
    }
  }
  return result;
}

/** Nombre del IfcSurfaceStyle de cada geometría (IfcStyledItem.Item → expressID de la geometría). */
function stylesByItem(api: IfcAPI, modelId: number) {
  const result = new Map<number, string>();
  const names = new Map<number, string | undefined>();
  const surface = api.GetTypeCodeFromName("IFCSURFACESTYLE");
  const styleName = (id: number): string | undefined => {
    if (names.has(id)) return names.get(id);
    const line = api.GetLine(modelId, id) as StepLine & { Styles?: unknown };
    let name: string | undefined;
    if (line.type === surface) name = textOf(line.Name);
    // IFC2X3: IfcPresentationStyleAssignment con la lista de estilos dentro.
    else for (const inner of handles(line.Styles)) { name = styleName(inner); if (name) break; }
    names.set(id, name);
    return name;
  };
  const styled = api.GetLineIDsWithType(modelId, api.GetTypeCodeFromName("IFCSTYLEDITEM"));
  for (let i = 0; i < styled.size(); i++) {
    const line = api.GetLine(modelId, styled.get(i)) as StepLine & { Item?: Handle; Styles?: unknown };
    const item = Number(line.Item?.value);
    if (!Number.isFinite(item)) continue;
    let name: string | undefined;
    for (const style of handles(line.Styles)) { name = styleName(style); if (name) break; }
    name ??= textOf(line.Name);
    if (name) result.set(item, name);
  }
  return result;
}

/** Hijo → padre por IfcRelAggregates. */
function aggregation(api: IfcAPI, modelId: number) {
  const parentOf = new Map<number, number>();
  const rels = api.GetLineIDsWithType(modelId, api.GetTypeCodeFromName("IFCRELAGGREGATES"));
  for (let i = 0; i < rels.size(); i++) {
    const rel = api.GetLine(modelId, rels.get(i)) as { RelatingObject?: Handle; RelatedObjects?: unknown };
    const parent = Number(rel.RelatingObject?.value);
    if (!Number.isFinite(parent)) continue;
    for (const child of handles(rel.RelatedObjects)) parentOf.set(child, parent);
  }
  return parentOf;
}

export function readIfcModel(api: IfcAPI, modelId: number, { url, bytes, start, onProgress }: ReadOptions): IfcModel {
  const products: IfcProduct[] = [];
  const bounds = emptyBounds();
  const matrix = new Matrix4();
  const normalMatrix = new Matrix3();
  const point = new Vector3();
  const normal = new Vector3();
  const styles = stylesByItem(api, modelId);
  let triangles = 0;
  api.StreamAllMeshes(modelId, (mesh, index, total) => {
    const line = api.GetLine(modelId, mesh.expressID) as StepLine;
    const productBounds = emptyBounds();
    const parts: IfcPart[] = [];
    for (let i = 0; i < mesh.geometries.size(); i++) {
      const placed = mesh.geometries.get(i);
      const geometry = api.GetGeometry(modelId, placed.geometryExpressID);
      try {
        const interleaved = api.GetVertexArray(geometry.GetVertexData(), geometry.GetVertexDataSize());
        const indices = new Uint32Array(api.GetIndexArray(geometry.GetIndexData(), geometry.GetIndexDataSize()));
        const positions = new Float32Array(interleaved.length / 2);
        const normals = new Float32Array(positions.length);
        matrix.fromArray(placed.flatTransformation);
        normalMatrix.getNormalMatrix(matrix);
        const low = productBounds.min, high = productBounds.max;
        for (let j = 0, n = interleaved.length / 6; j < n; j++) {
          point.fromArray(interleaved, j * 6).applyMatrix4(matrix);
          normal.fromArray(interleaved, j * 6 + 3).applyNormalMatrix(normalMatrix);
          // web-ifc ya incorpora la conversión IFC Z → Y en flatTransformation.
          positions[j * 3] = point.x; positions[j * 3 + 1] = point.y; positions[j * 3 + 2] = point.z;
          normals[j * 3] = normal.x; normals[j * 3 + 1] = normal.y; normals[j * 3 + 2] = normal.z;
          if (point.x < low[0]) low[0] = point.x; if (point.x > high[0]) high[0] = point.x;
          if (point.y < low[1]) low[1] = point.y; if (point.y > high[1]) high[1] = point.y;
          if (point.z < low[2]) low[2] = point.z; if (point.z > high[2]) high[2] = point.z;
        }
        const style = styles.get(placed.geometryExpressID);
        parts.push({ positions, normals, indices,
          color: [placed.color.x, placed.color.y, placed.color.z, placed.color.w], ...(style ? { style } : {}) });
        triangles += indices.length / 3;
      } finally {
        geometry.delete();
      }
    }
    if (parts.length) {
      union(bounds, productBounds);
      const center = centerOf(productBounds);
      for (const part of parts) {
        for (let j = 0; j < part.positions.length; j += 3) {
          part.positions[j]! -= center[0];
          part.positions[j + 1]! -= center[1];
          part.positions[j + 2]! -= center[2];
        }
      }
      const name = String(valueOf(line.Name) ?? `#${mesh.expressID}`);
      const ifcType = api.GetNameFromTypeCode(line.type);
      const tag = textOf(line.Tag), description = textOf(line.Description);
      products.push({ expressId: mesh.expressID, globalId: String(valueOf(line.GlobalId) ?? ""),
        name, ifcType, semanticId: semanticId(name, ifcType, {}, tag), psets: {}, center,
        bounds: productBounds, parts, ...(tag ? { tag } : {}), ...(description ? { description } : {}) });
    }
    if (index % 4 === 0) onProgress?.(0.2 + 0.6 * (index + 1) / Math.max(1, total), "Leyendo geometría y propiedades");
  }, true);
  if (!products.length) throw new Error("El IFC no contiene productos con geometría visible");
  if (new Set(products.map(product => product.globalId)).size !== products.length || products.some(product => !product.globalId)) {
    throw new Error("El IFC contiene GlobalId vacíos o duplicados; revisa su identidad antes de compararlo");
  }

  const psets = propertySetsByElement(api, modelId);
  for (const product of products) {
    product.psets = psets.get(product.expressId) ?? {};
    product.semanticId = semanticId(product.name, product.ifcType, product.psets, product.tag);
  }

  // Agregación entre elementos: el padre de una pieza es su equipo, línea o estructura.
  const parentOf = aggregation(api, modelId);
  const lines = new Map<number, StepLine>();
  const lineOf = (id: number) => {
    let line = lines.get(id);
    if (!line) { line = api.GetLine(modelId, id) as StepLine; lines.set(id, line); }
    return line;
  };
  const isElement = (id: number) => !SPATIAL.has(api.GetNameFromTypeCode(lineOf(id).type).toUpperCase());
  const elementParent = (id: number) => {
    const parent = parentOf.get(id);
    return parent !== undefined && isElement(parent) ? parent : undefined;
  };
  const assemblies = new Map<number, IfcAssembly>();
  const assemblyOf = (id: number): IfcAssembly => {
    let assembly = assemblies.get(id);
    if (assembly) return assembly;
    const line = lineOf(id);
    const name = String(valueOf(line.Name) ?? `#${id}`);
    const ifcType = api.GetNameFromTypeCode(line.type);
    const tag = textOf(line.Tag), description = textOf(line.Description);
    const own = psets.get(id) ?? {};
    assembly = { expressId: id, globalId: String(valueOf(line.GlobalId) ?? ""), name, ifcType,
      semanticId: semanticId(name, ifcType, own, tag), psets: own, children: [], bounds: emptyBounds(),
      center: [0, 0, 0], ...(tag ? { tag } : {}), ...(description ? { description } : {}) };
    assemblies.set(id, assembly);
    const parent = elementParent(id);
    if (parent !== undefined) {
      const above = assemblyOf(parent);
      assembly.parentGlobalId = above.globalId;
      above.children.push(assembly.globalId);
    }
    return assembly;
  };
  for (const product of products) {
    const parent = elementParent(product.expressId);
    if (parent === undefined) continue;
    const assembly = assemblyOf(parent);
    product.parentGlobalId = assembly.globalId;
    assembly.children.push(product.globalId);
  }
  // Límites de cada ensamblaje: unión de sus productos descendientes (y de su geometría propia).
  for (const product of products) {
    let id = product.parentGlobalId ? elementParent(product.expressId) : undefined;
    // Un IFC con agregación circular no debe colgar el worker.
    for (let depth = 0; id !== undefined && depth < 32; depth++) {
      const assembly = assemblies.get(id);
      if (!assembly) break;
      union(assembly.bounds, product.bounds);
      id = elementParent(id);
    }
    const own = assemblies.get(product.expressId);
    if (own) union(own.bounds, product.bounds);
  }
  const grouped = [...assemblies.values()].filter(assembly => Number.isFinite(assembly.bounds.min[0]));
  for (const assembly of grouped) assembly.center = centerOf(assembly.bounds);

  return { url, schema: api.GetModelSchema(modelId), products, ...(grouped.length ? { assemblies: grouped } : {}),
    bounds, triangles, bytes, parseMs: performance.now() - start };
}
