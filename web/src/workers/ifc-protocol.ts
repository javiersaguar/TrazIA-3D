export type Vec3 = [number, number, number];
export type Bounds = { min: Vec3; max: Vec3 };
export type PropertyValue = string | number | boolean | null;
export type PropertySets = Record<string, Record<string, PropertyValue>>;
export type IfcPart = {
  positions: Float32Array;
  normals: Float32Array;
  indices: Uint32Array;
  color: [number, number, number, number];
};
export type IfcProduct = {
  expressId: number;
  globalId: string;
  name: string;
  ifcType: string;
  semanticId: string;
  psets: PropertySets;
  bounds: Bounds;
  center: Vec3;
  parts: IfcPart[];
};
export type IfcModel = {
  url: string;
  schema: string;
  products: IfcProduct[];
  bounds: Bounds;
  triangles: number;
  bytes: number;
  parseMs: number;
};
export type LoadRequest = { type: "load"; url: string; wasmPath: string };
export type WorkerReply =
  | { type: "progress"; progress: number; message: string }
  | { type: "ready"; model: IfcModel }
  | { type: "error"; message: string };
