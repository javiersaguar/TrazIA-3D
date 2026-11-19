import type { Bounds, IfcAssembly, IfcProduct, PropertySets, Vec3 } from "@/workers/ifc-protocol";

/*
  Árbol de selección del visor: productos con geometría y ensamblajes (padres por IfcRelAggregates
  que son elementos). Contrato C2:

  - un clic sobre una pieza de un equipo no seleccionado selecciona el equipo (element:TAG);
  - con el equipo ya seleccionado, un clic sobre una de sus piezas baja a la pieza;
  - Esc o un clic en vacío sube un nivel y después deja la selección vacía.

  Sin ensamblajes (IFC actuales y equipos sueltos) cada producto es su propia raíz y el clic lo
  selecciona directamente, como hasta ahora.
*/

export type ProductLike = Pick<IfcProduct, "semanticId" | "globalId" | "name" | "ifcType" | "psets" | "bounds" | "center"
  | "tag" | "description" | "parentGlobalId"> & { parts?: { indices: ArrayLike<number> }[] };

export type HierarchyNode = {
  semanticId: string;
  globalId: string;
  name: string;
  tag?: string;
  description?: string;
  ifcType: string;
  psets: PropertySets;
  bounds: Bounds;
  center: Vec3;
  /** semanticId del padre (ensamblaje). */
  parentId?: string;
  /** semanticId de los hijos directos. */
  childIds: string[];
  /** semanticId de los productos con geometría del subárbol (incluido el propio si la tiene). */
  productIds: string[];
  isAssembly: boolean;
  hasGeometry: boolean;
  triangles: number;
};

export type Hierarchy = {
  nodes: Map<string, HierarchyNode>;
  /** Raíces en el orden del IFC. */
  roots: string[];
  /** Si algún producto cuelga de un ensamblaje. */
  nested: boolean;
};

export function buildHierarchy(products: ProductLike[], assemblies: IfcAssembly[] = []): Hierarchy {
  const nodes = new Map<string, HierarchyNode>();
  const byGlobal = new Map<string, HierarchyNode>();
  const add = (node: HierarchyNode) => {
    // Un ensamblaje con geometría propia también es producto: se fusionan por GlobalId.
    const existing = byGlobal.get(node.globalId);
    if (existing) {
      existing.isAssembly ||= node.isAssembly;
      existing.hasGeometry ||= node.hasGeometry;
      existing.triangles += node.triangles;
      return existing;
    }
    if (nodes.has(node.semanticId)) return nodes.get(node.semanticId)!;
    nodes.set(node.semanticId, node);
    byGlobal.set(node.globalId, node);
    return node;
  };
  for (const assembly of assemblies) {
    add({ semanticId: assembly.semanticId, globalId: assembly.globalId, name: assembly.name, tag: assembly.tag,
      description: assembly.description, ifcType: assembly.ifcType, psets: assembly.psets, bounds: assembly.bounds,
      center: assembly.center, childIds: [], productIds: [], isAssembly: true, hasGeometry: false, triangles: 0 });
  }
  for (const product of products) {
    add({ semanticId: product.semanticId, globalId: product.globalId, name: product.name, tag: product.tag,
      description: product.description, ifcType: product.ifcType, psets: product.psets, bounds: product.bounds,
      center: product.center, childIds: [], productIds: [], isAssembly: false, hasGeometry: true,
      triangles: (product.parts ?? []).reduce((sum, part) => sum + part.indices.length / 3, 0) });
  }
  const parentGlobal = new Map<string, string>();
  for (const assembly of assemblies) if (assembly.parentGlobalId) parentGlobal.set(assembly.globalId, assembly.parentGlobalId);
  for (const product of products) if (product.parentGlobalId) parentGlobal.set(product.globalId, product.parentGlobalId);
  let nested = false;
  for (const node of nodes.values()) {
    const parent = byGlobal.get(parentGlobal.get(node.globalId) ?? "");
    if (!parent || parent === node) continue;
    node.parentId = parent.semanticId;
    parent.childIds.push(node.semanticId);
    nested = true;
  }
  const roots = [...nodes.values()].filter(node => !node.parentId).map(node => node.semanticId);
  // Productos de cada subárbol (iterativo y a prueba de ciclos).
  for (const node of nodes.values()) {
    if (!node.hasGeometry) continue;
    const seen = new Set<string>();
    for (let current: HierarchyNode | undefined = node; current && !seen.has(current.semanticId);
      current = current.parentId ? nodes.get(current.parentId) : undefined) {
      seen.add(current.semanticId);
      current.productIds.push(node.semanticId);
    }
  }
  return { nodes, roots, nested };
}

/** Cadena de ids desde `id` hasta su raíz (incluidos ambos). */
export function lineage(hierarchy: Hierarchy, id: string): string[] {
  const chain: string[] = [];
  for (let node = hierarchy.nodes.get(id); node && !chain.includes(node.semanticId);
    node = node.parentId ? hierarchy.nodes.get(node.parentId) : undefined) chain.push(node.semanticId);
  return chain;
}

/** Qué selecciona un clic sobre el producto `productId` según lo que ya está seleccionado. */
export function clickTarget(hierarchy: Hierarchy, productId: string, selectedId?: string): string {
  const chain = lineage(hierarchy, productId);
  if (!chain.length) return productId;
  const level = selectedId ? chain.indexOf(selectedId) : -1;
  if (level === 0) return productId;
  if (level > 0) return chain[level - 1]!; // baja un nivel hacia la pieza pulsada
  return chain[chain.length - 1]!; // primero, el equipo entero
}

/** Un nivel por encima de `id`, o nada si ya es una raíz. */
export function levelUp(hierarchy: Hierarchy, id: string): string | undefined {
  return hierarchy.nodes.get(id)?.parentId;
}

/** Si `id` es `ancestor` o cuelga de él. */
export function isWithin(hierarchy: Hierarchy, id: string, ancestor: string): boolean {
  return lineage(hierarchy, id).includes(ancestor);
}
