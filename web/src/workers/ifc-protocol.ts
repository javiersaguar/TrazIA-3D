export type Vec3 = [number, number, number];
export type Bounds = { min: Vec3; max: Vec3 };
export type PropertyValue = string | number | boolean | null;
export type PropertySets = Record<string, Record<string, PropertyValue>>;
export type IfcPart = {
  positions: Float32Array;
  normals: Float32Array;
  indices: Uint32Array;
  color: [number, number, number, number];
  /** Nombre del IfcSurfaceStyle del IfcStyledItem de esta geometría (p. ej. "Acero"). */
  style?: string;
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
  /** Atributo Tag del IFC (en proceso: "TAG" en la raíz y "TAG/clave" en la pieza). */
  tag?: string;
  /** Atributo Description del IFC. */
  description?: string;
  /** Padre por IfcRelAggregates cuando el padre es un elemento (no un nivel o un edificio). */
  parentGlobalId?: string;
};
/**
 * Padre de agregación que es un elemento (equipo, línea o estructura) y agrupa productos.
 * En proceso no tiene geometría propia: sus límites son la unión de los de sus descendientes.
 */
export type IfcAssembly = {
  expressId: number;
  globalId: string;
  name: string;
  tag?: string;
  description?: string;
  ifcType: string;
  semanticId: string;
  psets: PropertySets;
  /** GlobalId de los hijos directos (productos o ensamblajes). */
  children: string[];
  bounds: Bounds;
  center: Vec3;
  /** Si este ensamblaje cuelga a su vez de otro elemento. */
  parentGlobalId?: string;
};
export type IfcModel = {
  url: string;
  schema: string;
  products: IfcProduct[];
  /** Solo si el IFC agrega productos en elementos; los IFC sin descomposición no lo traen. */
  assemblies?: IfcAssembly[];
  bounds: Bounds;
  triangles: number;
  bytes: number;
  parseMs: number;
};
export type LoadRequest = { type: "load"; url: string; wasmPath: string; gzipUrl?: string };
export type WorkerReply =
  | { type: "progress"; progress: number; message: string }
  | { type: "ready"; model: IfcModel }
  | { type: "error"; message: string };
