/*
  Contrato entre las pantallas y el 3D. Se pueden añadir props opcionales;
  no se quitan ni se renombran los existentes.
*/

export type Annotation = {
  id: string;
  label: string;
  value: number;
  unit: string;
  confidence: number;
};

export type IfcViewerProps = {
  ifcUrl: string;
  selectedId?: string;
  hoveredId?: string;
  onSelect?(id: string): void;
  onHover?(id: string | null): void;
  annotations?: Annotation[];
  view?: "iso" | "front" | "top";
  mode?: "solid" | "xray" | "exploded";
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
