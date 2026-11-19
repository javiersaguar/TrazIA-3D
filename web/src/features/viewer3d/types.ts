/*
  Contrato entre las pantallas y el 3D. Se pueden añadir props opcionales;
  no se quitan ni se renombran los existentes.
*/
import type { ReactNode } from "react";
import type { Bounds, PropertySets, Vec3 } from "@/workers/ifc-protocol";
import type { PreparedProduct } from "./model-resource";

export type Annotation = {
  id: string;
  label: string;
  value: number;
  unit: string;
  confidence: number;
  source?: { document_id: string; page?: number | null; locator?: string; sheet?: string | null; cell?: string | null };
  state?: string;
};

export type ProcessEnvironmentId = "neutral" | "ocean" | "coast" | "desert" | "industrial";

/** Proyección de la cámara del visor. */
export type ViewerProjection = "perspective" | "orthographic";

/**
 * Producto o ensamblaje de la planta tal y como lo lee el visor (contrato C2). Los ensamblajes
 * (`isAssembly`) son padres por IfcRelAggregates sin geometría propia: sus límites son la unión de
 * los de sus piezas y `triangles` es 0.
 */
export type PlantProductInfo = {
  semanticId: string;
  /** semanticId del ensamblaje padre (una pieza apunta a su equipo, línea o estructura). */
  parentId?: string;
  globalId: string;
  name: string;
  tag?: string;
  ifcType: string;
  psets: PropertySets;
  bounds: Bounds;
  center: Vec3;
  triangles: number;
  isAssembly: boolean;
  /** Rótulo «tag · nombre» que usa el visor (etiqueta flotante, árbol y leyenda). */
  label?: string;
  /** Atributo Description del IFC. */
  description?: string;
  /** semanticId de los hijos directos. */
  childIds?: string[];
};

/** Lo que recibe `overlay` para pintar dentro del lienzo 3D. */
export type ViewerOverlayContext = {
  /** Productos visibles con su geometría (ya colocados en sus límites). */
  products: PreparedProduct[];
  selectedId?: string;
  /** Límites del modelo completo. */
  bounds: Bounds;
};

export type IfcViewerProps = {
  ifcUrl: string;
  /** Copia gzip de los mismos bytes IFC, para las plantas públicas de demostración. */
  ifcGzipUrl?: string;
  selectedId?: string;
  hoveredId?: string;
  /**
   * Nueva selección. En proyectos de proceso (`scenario`) la selección es jerárquica: el primer
   * clic elige el equipo (`element:TAG`), el segundo baja a la pieza; Esc o un clic en vacío sube un
   * nivel y, desde la raíz, deja la selección vacía llamando a `onSelect("")`.
   */
  onSelect?(id: string): void;
  onHover?(id: string | null): void;
  annotations?: Annotation[];
  view?: "iso" | "front" | "top";
  mode?: "solid" | "xray" | "exploded";
  scenario?: ProcessEnvironmentId;
  animateEnvironment?: boolean;
  holdPrevious?: boolean;
  /**
   * Encuadra con oclusión cada nueva selección (vista elevada, distancia según el tamaño y lo que
   * tape, atenuado). Por defecto `true` si hay `scenario`. Sin selección vuelve a la vista general.
   */
  focusOnSelect?: boolean;
  /**
   * Proyección inicial en la vista general: `"perspective"` por defecto si hay `scenario`;
   * `"orthographic"` en el resto. Alzado, Planta y Como el plano son siempre ortográficas.
   */
  projection?: ViewerProjection;
  /** Productos y ensamblajes leídos del IFC, cada vez que cambia el modelo. */
  onProducts?(info: PlantProductInfo[]): void;
  showSelectionDimensions?: boolean;
  /** Contenido extra dentro del lienzo 3D (cotas, rótulos…), con los productos y la selección. */
  overlay?(context: ViewerOverlayContext): ReactNode;
  /** Piezas atenuadas porque tapan el componente encuadrado (vacío sin foco). */
  onFocusChange?(info: { occluding: string[] }): void;
};

export type PlantEquipment = {
  tag: string;
  ifcUrl: string;
  status: "draft" | "review" | "approved" | "changed";
};

export type PlantSceneProps = {
  equipment: PlantEquipment[];
  onSelect?(tag: string): void;
};

export type RevisionMorphProps = {
  fromUrl: string;
  toUrl: string;
  changes: unknown;
  progress?: number;
  onProgress?(p: number): void;
};
