/* Archivo generado por scripts/gen-types.mjs desde generated/revision.schema.json. No editar a mano. */

export type SchemaVersion = "0.2";
export type ProjectId = string;
export type Revision1 = string;
export type Dataset = "synthetic" | "real";
/**
 * @minItems 1
 */
export type Documents = [Document, ...Document[]];
export type Id = string;
export type Filename = string;
export type Revision2 = string;
export type Sha256 = string;
export type PageCount = number | null;
export type Id1 = string;
export type Value = string;
export type Unit = "1";
export type DocumentId = string;
export type Page = number | null;
export type Sheet = string | null;
export type Cell = string | null;
export type Locator = string;
export type Bbox = [unknown, unknown, unknown, unknown] | null;
export type Confidence = number;
export type Reviewed = boolean;
export type Kind = "vertical_vessel";
export type Value1 = number;
export type Unit1 = "mm";
export type Value2 = number | string;
export type Unit2 = string;
/**
 * @minItems 3
 */
export type Nozzles = [Nozzle, Nozzle, Nozzle, ...Nozzle[]];
export type Id2 = string;
export type Value3 = number;
export type Unit3 = "mm";
export type Value4 = number;
export type Unit4 = "deg";
export type Reviewer = string;
export type Timestamp = string;
export type InputSha256 = string;

export interface Revision {
  schema_version?: SchemaVersion;
  project_id: ProjectId;
  revision: Revision1;
  dataset: Dataset;
  documents: Documents;
  equipment: Equipment;
  approval?: Approval | null;
}
export interface Document {
  id: Id;
  filename: Filename;
  revision: Revision2;
  sha256: Sha256;
  page_count?: PageCount;
}
export interface Equipment {
  id: Id1;
  tag: Tag;
  kind?: Kind;
  diameter: Dimension;
  height: Dimension;
  head_depth: Dimension;
  skirt_height: Dimension;
  skirt_thickness: Dimension;
  attributes?: Attributes;
  nozzles: Nozzles;
}
export interface Tag {
  value: Value;
  unit?: Unit;
  source: Source;
}
export interface Source {
  document_id: DocumentId;
  page?: Page;
  sheet?: Sheet;
  cell?: Cell;
  locator: Locator;
  bbox?: Bbox;
  confidence: Confidence;
  reviewed?: Reviewed;
}
export interface Dimension {
  value: Value1;
  unit?: Unit1;
  source: Source;
}
export interface Attributes {
  [k: string]: Attribute | undefined;
}
/**
 * This interface was referenced by `Attributes`'s JSON-Schema definition
 * via the `patternProperty` "^[A-Za-z0-9_-]+$".
 */
export interface Attribute {
  value: Value2;
  unit: Unit2;
  source: Source;
}
export interface Nozzle {
  id: Id2;
  diameter: Dimension;
  projection: Dimension;
  elevation: Elevation;
  azimuth: Angle;
}
export interface Elevation {
  value: Value3;
  unit?: Unit3;
  source: Source;
}
export interface Angle {
  value: Value4;
  unit?: Unit4;
  source: Source;
}
export interface Approval {
  reviewer: Reviewer;
  timestamp: Timestamp;
  input_sha256: InputSha256;
}
