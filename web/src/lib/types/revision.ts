/* Archivo generado por scripts/gen-types.mjs desde generated/revision.schema.json. No editar a mano. */

export type SchemaVersion = "0.3";
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
export type DocumentId = string;
export type Page = number | null;
export type Sheet = string | null;
export type Cell = string | null;
export type Locator = string;
export type Bbox = [unknown, unknown, unknown, unknown] | null;
export type Confidence = number;
export type Reviewed = boolean;
export type ConfidenceRaw = number | null;
export type Channel =
  | (
      | "texto"
      | "tabla"
      | "cota"
      | "cajetin"
      | "hoja_datos"
      | "vesor"
      | "ocr"
      | "detector"
      | "vision"
      | "geometria"
      | "rag"
      | "memoria_revision"
      | "humano"
    )
  | null;
export type Strategy = string | null;
export type Model = string | null;
export type PromptSha256 = string | null;
export type Grounded = boolean | null;
export type TextOriginal = string | null;
export type UnitOriginal = string | null;
export type State = "candidate" | "conflict" | "abstained" | "accepted" | "corrected" | "assumed";
export type Low = number;
export type High = number;
export type Level = number;
export type Method = "conformal";
export type Value = number | string;
export type Unit = string;
export type Alternatives = Alternative[];
export type Explanation = string | null;
export type Value1 = string;
export type Unit1 = "1";
export type Kind = "vertical_vessel" | "horizontal_vessel" | "column" | "tank" | "pump" | "compressor" | "generic";
export type Lod = 1 | 2 | 3;
export type Support = ("skirt" | "legs" | "saddles" | "lugs" | "baseplate" | "none") | null;
export type State1 = "candidate" | "conflict" | "abstained" | "accepted" | "corrected" | "assumed";
export type Alternatives1 = Alternative[];
export type Explanation1 = string | null;
export type Value2 = number;
export type Unit2 = "mm";
export type State2 = "candidate" | "conflict" | "abstained" | "accepted" | "corrected" | "assumed";
export type Alternatives2 = Alternative[];
export type Explanation2 = string | null;
export type Value3 = number | string;
export type Unit3 = string;
export type Id2 = string;
export type State3 = "candidate" | "conflict" | "abstained" | "accepted" | "corrected" | "assumed";
export type Alternatives3 = Alternative[];
export type Explanation3 = string | null;
export type Value4 = number;
export type Unit4 = "mm";
export type State4 = "candidate" | "conflict" | "abstained" | "accepted" | "corrected" | "assumed";
export type Alternatives4 = Alternative[];
export type Explanation4 = string | null;
export type Value5 = number;
export type Unit5 = "deg";
export type NozzleType = ("radial" | "tangential" | "top" | "bottom" | "inclined") | null;
export type Nozzles = Nozzle[];
export type Reviewer = string;
export type Timestamp = string;
export type InputSha256 = string;
export type Strategy1 = string;
export type Providers = string[];
export type Seconds = number;
export type GpuSeconds = number | null;
export type TokensIn = number | null;
export type TokensOut = number | null;
export type CostEur = number | null;
export type ExternalCalls = number;

export interface Revision {
  schema_version?: SchemaVersion;
  project_id: ProjectId;
  revision: Revision1;
  dataset: Dataset;
  documents: Documents;
  equipment: Equipment;
  approval?: Approval | null;
  run?: RunInfo | null;
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
  lod?: Lod;
  support?: Support;
  envelope?: Envelope | null;
  diameter?: Dimension | null;
  height?: Dimension | null;
  head_depth?: Dimension | null;
  skirt_height?: Dimension | null;
  skirt_thickness?: Dimension | null;
  attributes?: Attributes;
  nozzles: Nozzles;
}
export interface Tag {
  source: Source;
  state?: State;
  interval?: Interval | null;
  alternatives?: Alternatives;
  explanation?: Explanation;
  value: Value1;
  unit?: Unit1;
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
  confidence_raw?: ConfidenceRaw;
  channel?: Channel;
  strategy?: Strategy;
  model?: Model;
  prompt_sha256?: PromptSha256;
  grounded?: Grounded;
  text_original?: TextOriginal;
  unit_original?: UnitOriginal;
}
export interface Interval {
  low: Low;
  high: High;
  level: Level;
  method?: Method;
}
export interface Alternative {
  value: Value;
  unit: Unit;
  source: Source;
}
export interface Envelope {
  origin: Vector3;
  size: Vector3;
}
export interface Vector3 {
  x: Dimension;
  y: Dimension;
  z: Dimension;
}
export interface Dimension {
  source: Source;
  state?: State1;
  interval?: Interval | null;
  alternatives?: Alternatives1;
  explanation?: Explanation1;
  value: Value2;
  unit?: Unit2;
}
export interface Attributes {
  [k: string]: Attribute | undefined;
}
/**
 * This interface was referenced by `Attributes`'s JSON-Schema definition
 * via the `patternProperty` "^[A-Za-z0-9_-]+$".
 */
export interface Attribute {
  source: Source;
  state?: State2;
  interval?: Interval | null;
  alternatives?: Alternatives2;
  explanation?: Explanation2;
  value: Value3;
  unit: Unit3;
}
export interface Nozzle {
  id: Id2;
  diameter: Dimension;
  projection: Dimension;
  elevation: Elevation;
  azimuth: Angle;
  service?: Attribute | null;
  rating?: Attribute | null;
  nozzle_type?: NozzleType;
}
export interface Elevation {
  source: Source;
  state?: State3;
  interval?: Interval | null;
  alternatives?: Alternatives3;
  explanation?: Explanation3;
  value: Value4;
  unit?: Unit4;
}
export interface Angle {
  source: Source;
  state?: State4;
  interval?: Interval | null;
  alternatives?: Alternatives4;
  explanation?: Explanation4;
  value: Value5;
  unit?: Unit5;
}
export interface Approval {
  reviewer: Reviewer;
  timestamp: Timestamp;
  input_sha256: InputSha256;
}
export interface RunInfo {
  strategy: Strategy1;
  providers: Providers;
  seconds: Seconds;
  gpu_seconds?: GpuSeconds;
  tokens_in?: TokensIn;
  tokens_out?: TokensOut;
  cost_eur?: CostEur;
  external_calls: ExternalCalls;
}
