/*
  Cambios de prueba sobre el IFC de una planta, en el navegador y sobre el propio texto STEP.

  Las plantas de proceso escriben cada pieza con coordenadas del modelo (colocación identidad
  compartida), en IfcTriangulatedFaceSet o en instancias IfcMappedItem de una geometría común.
  Un cambio de envolvente o de posición de un equipo:

  - transforma los puntos de las piezas del equipo (IfcCartesianPointList3D) respecto al centro
    de su huella y a su cota inferior, para que siga apoyado donde estaba;
  - mueve el origen de cada instancia repetida (pernos, peldaños…) sin cambiar su tamaño;
  - mueve los puertos del equipo, que dejan de coincidir con su tubería: la línea queda marcada
    para revisar en vez de deformarse a escondidas;
  - añade al equipo el pset TrazIA_Edicion con lo que se ha cambiado, y el IFC sigue en DRAFT.

  No se dibuja nada aparte: el visor relee este IFC como cualquier otro.
*/

export type EquipmentEdit = {
  /** Envolvente objetivo en metros (X, Y, Z del modelo). Sin valor: se conserva. */
  length?: number;
  width?: number;
  height?: number;
  /**
   * Factores de escala (X, Y, Z). Si se dan, mandan sobre la envolvente objetivo: así quien mide
   * la envolvente de otra forma (el visor, con sus límites) obtiene la proporción que pide.
   */
  scale?: [number, number, number];
  /** Desplazamiento en planta, en metros. */
  dx?: number;
  dy?: number;
};

export type Envelope = { min: [number, number, number]; max: [number, number, number] };

type Entity = { id: number; type: string; args: string };

const LINE = /^#(\d+)=([A-Z0-9_]+)\((.*)\);\s*$/;
const REF = /^#(\d+)$/;

/** Separa los argumentos de primer nivel de una entidad STEP (respeta paréntesis y cadenas). */
export function splitArgs(args: string): string[] {
  const out: string[] = [];
  let depth = 0;
  let quoted = false;
  let start = 0;
  for (let i = 0; i < args.length; i++) {
    const c = args[i];
    if (quoted) {
      if (c === "'") {
        if (args[i + 1] === "'") i++;
        else quoted = false;
      }
      continue;
    }
    if (c === "'") quoted = true;
    else if (c === "(") depth++;
    else if (c === ")") depth--;
    else if (c === "," && depth === 0) {
      out.push(args.slice(start, i).trim());
      start = i + 1;
    }
  }
  out.push(args.slice(start).trim());
  return out;
}

const refs = (value: string) => [...value.matchAll(/#(\d+)/g)].map(m => Number(m[1]));
const ref = (value: string | undefined) => {
  const match = value ? REF.exec(value) : null;
  return match ? Number(match[1]) : null;
};
const unquote = (value: string | undefined) => (value && value.startsWith("'") ? value.slice(1, -1).replace(/''/g, "'") : undefined);

/** Real STEP: siempre con punto decimal, al milímetro de décima. */
export function real(value: number): string {
  const rounded = Math.round(value * 10_000) / 10_000;
  const text = String(Object.is(rounded, -0) ? 0 : rounded);
  return /[.eE]/.test(text) ? text : `${text}.`;
}

const parseTriples = (body: string) =>
  [...body.matchAll(/\(\s*(-?[\d.eE+-]+)\s*,\s*(-?[\d.eE+-]+)\s*,\s*(-?[\d.eE+-]+)\s*\)/g)].map(
    m => [Number(m[1]), Number(m[2]), Number(m[3])] as [number, number, number],
  );

/** Índice mínimo del STEP: entidades por id y el orden de las líneas para reescribirlo. */
export class StepModel {
  readonly lines: string[];
  private readonly entities = new Map<number, Entity>();
  private readonly lineOf = new Map<number, number>();
  private nextId = 1;

  constructor(text: string) {
    this.lines = text.split(/\r?\n/);
    this.lines.forEach((line, index) => {
      const match = LINE.exec(line);
      if (!match) return;
      const id = Number(match[1]);
      this.entities.set(id, { id, type: match[2]!, args: match[3]! });
      this.lineOf.set(id, index);
      this.nextId = Math.max(this.nextId, id + 1);
    });
  }

  get(id: number) {
    return this.entities.get(id);
  }

  args(id: number) {
    const entity = this.entities.get(id);
    return entity ? splitArgs(entity.args) : [];
  }

  set(id: number, args: string) {
    const entity = this.entities.get(id)!;
    entity.args = args;
    this.lines[this.lineOf.get(id)!] = `#${id}=${entity.type}(${args});`;
  }

  /** Añade entidades nuevas antes de ENDSEC de la sección DATA. */
  add(type: string, args: string) {
    const id = this.nextId++;
    const end = this.lines.lastIndexOf("ENDSEC;");
    this.lines.splice(end, 0, `#${id}=${type}(${args});`);
    this.entities.set(id, { id, type, args });
    // Las líneas a partir de ENDSEC se han desplazado una posición.
    for (const [key, index] of this.lineOf) if (index >= end) this.lineOf.set(key, index + 1);
    this.lineOf.set(id, end);
    return id;
  }

  *ofType(type: string) {
    for (const entity of this.entities.values()) if (entity.type === type) yield entity;
  }

  /** Primer elemento con ese Tag (atributo 8 de IfcElement). */
  byTag(tag: string) {
    const quoted = `'${tag.replace(/'/g, "''")}'`;
    for (const entity of this.entities.values()) {
      if (!entity.args.includes(quoted)) continue;
      const args = splitArgs(entity.args);
      if (args[7] === quoted) return entity;
    }
    return undefined;
  }

  toString() {
    return this.lines.join("\n");
  }
}

/**
 * Instancia de una geometría repetida: la geometría fuente está en coordenadas del modelo de la
 * primera copia y el operador lleva el desplazamiento de esta copia (ejes y escala identidad).
 */
type Instance = { item: number; operator: number; source: number[]; delta: [number, number, number] };
type Targets = { pointLists: Set<number>; instances: Instance[]; ports: Set<number> };

/** Puntos que hay que mover para un equipo: geometría de sus piezas, instancias y puertos. */
function collect(model: StepModel, rootId: number): Targets {
  const targets: Targets = { pointLists: new Set(), instances: [], ports: new Set() };
  const children: number[] = [];
  for (const rel of model.ofType("IFCRELAGGREGATES")) {
    const args = splitArgs(rel.args);
    if (ref(args[4]) === rootId) children.push(...refs(args[5] ?? ""));
  }
  for (const child of children) {
    const shape = ref(model.args(child)[6]);
    if (shape === null) continue;
    for (const representation of refs(model.args(shape)[2] ?? "")) {
      for (const item of refs(model.args(representation)[3] ?? "")) {
        const entity = model.get(item);
        if (!entity) continue;
        if (entity.type === "IFCTRIANGULATEDFACESET" || entity.type === "IFCPOLYGONALFACESET") {
          const coordinates = ref(splitArgs(entity.args)[0]);
          if (coordinates !== null) targets.pointLists.add(coordinates);
        } else if (entity.type === "IFCMAPPEDITEM") {
          const [map, op] = splitArgs(entity.args);
          const operator = ref(op);
          const mapping = ref(map);
          const origin = operator === null ? null : ref(model.args(operator)[2]);
          if (operator === null || mapping === null || origin === null) continue;
          const mapped = ref(model.args(mapping)[1]);
          const source = mapped === null ? [] : refs(model.args(mapped)[3] ?? "")
            .map(id => model.get(id))
            .filter(e => e?.type === "IFCTRIANGULATEDFACESET" || e?.type === "IFCPOLYGONALFACESET")
            .map(e => ref(splitArgs(e!.args)[0]))
            .filter((id): id is number => id !== null);
          const delta = readPoint(model, origin) ?? [0, 0, 0];
          targets.instances.push({ item, operator, source, delta });
        }
      }
    }
  }
  for (const rel of model.ofType("IFCRELNESTS")) {
    const args = splitArgs(rel.args);
    if (ref(args[4]) !== rootId) continue;
    for (const port of refs(args[5] ?? "")) {
      const placement = ref(model.args(port)[5]);
      const axis = placement === null ? null : ref(model.args(placement)[1]);
      const point = axis === null ? null : ref(model.args(axis)[0]);
      if (point !== null) targets.ports.add(point);
    }
  }
  return targets;
}

function readPoint(model: StepModel, id: number) {
  return parseTriples(model.args(id)[0] ?? "")[0];
}

/** Envolvente real de un equipo (coordenadas IFC, Z arriba), de la geometría de sus piezas. */
export function equipmentEnvelope(model: StepModel, tag: string): Envelope | null {
  const root = model.byTag(tag);
  if (!root) return null;
  const targets = collect(model, root.id);
  const min: [number, number, number] = [Infinity, Infinity, Infinity];
  const max: [number, number, number] = [-Infinity, -Infinity, -Infinity];
  const grow = (p: [number, number, number]) => {
    for (let i = 0; i < 3; i++) {
      min[i] = Math.min(min[i]!, p[i]!);
      max[i] = Math.max(max[i]!, p[i]!);
    }
  };
  for (const list of targets.pointLists) parseTriples(model.args(list)[0] ?? "").forEach(grow);
  for (const instance of targets.instances) {
    for (const list of instance.source) {
      for (const p of parseTriples(model.args(list)[0] ?? "")) {
        grow([p[0] + instance.delta[0], p[1] + instance.delta[1], p[2] + instance.delta[2]]);
      }
    }
  }
  return Number.isFinite(min[0]) ? { min, max } : null;
}

/** Guid IFC (22 caracteres) determinista a partir de un texto. */
function guid(seed: string) {
  const alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$";
  let h1 = 0x811c9dc5, h2 = 0x9e3779b9;
  let out = "";
  for (let round = 0; out.length < 22; round++) {
    for (let i = 0; i < seed.length; i++) {
      h1 = Math.imul(h1 ^ seed.charCodeAt(i), 16777619) >>> 0;
      h2 = Math.imul(h2 ^ (seed.charCodeAt(i) + round), 2246822519) >>> 0;
    }
    let value = (h1 ^ (h2 << 7)) >>> 0;
    for (let k = 0; k < 5 && out.length < 22; k++) {
      out += alphabet[(out.length === 0 ? value % 4 : value % 64)];
      value = Math.floor(value / 64) ^ h2;
    }
  }
  return out;
}

const stepText = (value: string) => `'${value.replace(/'/g, "''").replace(/[^\x20-\x7e]/g, c => {
  const hex = c.charCodeAt(0).toString(16).toUpperCase().padStart(4, "0");
  return `\\X2\\${hex}\\X0\\`;
})}'`;

export type EditResult = {
  text: string;
  /** Equipos cambiados con su envolvente antes y después. */
  changed: { tag: string; before: Envelope; after: Envelope }[];
};

/** Aplica cambios de envolvente y posición a los equipos indicados por tag. */
export function applyEquipmentEdits(text: string, edits: Record<string, EquipmentEdit>): EditResult {
  const model = new StepModel(text);
  const changed: EditResult["changed"] = [];
  // Orígenes de las colocaciones absolutas: compartidos por todo el modelo, nunca se mueven.
  const done = new Set<number>();
  for (const placement of model.ofType("IFCLOCALPLACEMENT")) {
    const args = splitArgs(placement.args);
    const axis = args[0] === "$" ? ref(args[1]) : null;
    const point = axis === null ? null : ref(model.args(axis)[0]);
    if (point !== null) done.add(point);
  }
  for (const [tag, edit] of Object.entries(edits)) {
    const root = model.byTag(tag);
    const before = root && equipmentEnvelope(model, tag);
    if (!root || !before) continue;
    const size = before.max.map((v, i) => v - before.min[i]!) as [number, number, number];
    const scale = edit.scale ?? [edit.length, edit.width, edit.height].map((target, i) =>
      target && size[i]! > 1e-6 ? target / size[i]! : 1,
    ) as [number, number, number];
    const anchor = [(before.min[0] + before.max[0]) / 2, (before.min[1] + before.max[1]) / 2, before.min[2]];
    const shift = [edit.dx ?? 0, edit.dy ?? 0, 0];
    const move = (p: [number, number, number]) =>
      p.map((v, i) => anchor[i]! + (v - anchor[i]!) * scale[i]! + shift[i]!) as [number, number, number];
    const targets = collect(model, root.id);
    for (const list of targets.pointLists) {
      if (done.has(list)) continue;
      done.add(list);
      const args = model.args(list);
      const points = parseTriples(args[0] ?? "").map(move);
      args[0] = `(${points.map(p => `(${p.map(real).join(",")})`).join(",")})`;
      model.set(list, args.join(","));
    }
    // Cada copia repetida conserva su tamaño: se desplaza su centro. El operador y su punto se
    // clonan porque varias copias pueden compartirlos.
    for (const instance of targets.instances) {
      const points = instance.source.flatMap(list => parseTriples(model.args(list)[0] ?? ""));
      if (!points.length) continue;
      const center = [0, 1, 2].map(i => points.reduce((sum, p) => sum + p[i]!, 0) / points.length);
      const placed = center.map((v, i) => v + instance.delta[i]!) as [number, number, number];
      const delta = move(placed).map((v, i) => v - center[i]!);
      const origin = model.add("IFCCARTESIANPOINT", `(${delta.map(real).join(",")})`);
      const operator = model.args(instance.operator);
      operator[2] = `#${origin}`;
      const clone = model.add(model.get(instance.operator)!.type, operator.join(","));
      const item = model.args(instance.item);
      item[1] = `#${clone}`;
      model.set(instance.item, item.join(","));
    }
    for (const point of targets.ports) {
      if (done.has(point)) continue;
      done.add(point);
      const p = readPoint(model, point);
      if (p) model.set(point, `(${move(p).map(real).join(",")})`);
    }
    const after: Envelope = {
      min: move(before.min),
      max: [anchor[0]! + (before.max[0] - anchor[0]!) * scale[0] + shift[0]!,
        anchor[1]! + (before.max[1] - anchor[1]!) * scale[1] + shift[1]!,
        anchor[2]! + (before.max[2] - anchor[2]!) * scale[2]],
    };
    changed.push({ tag, before, after });
    // Constancia en el propio IFC: qué se cambió y desde qué envolvente.
    const values: [string, string][] = [
      ["Motivo", stepText("Cambio de prueba en TrazIA-3D; no procede de los planos")],
      ["EnvolventeAntesM", stepText(size.map(v => v.toFixed(3)).join(" x "))],
      ["EnvolventeDespuesM", stepText(after.max.map((v, i) => (v - after.min[i]!).toFixed(3)).join(" x "))],
      ["DesplazamientoXM", real(shift[0]!)],
      ["DesplazamientoYM", real(shift[1]!)],
    ];
    const properties = values.map(([name, value]) => {
      const typed = value.startsWith("'") ? `IFCTEXT(${value})` : `IFCLENGTHMEASURE(${value})`;
      return model.add("IFCPROPERTYSINGLEVALUE", `${stepText(name)},$,${typed},$`);
    });
    const ownerHistory = model.args(root.id)[1] ?? "$";
    const pset = model.add(
      "IFCPROPERTYSET",
      `${stepText(guid(`edicion/${tag}/pset`))},${ownerHistory},'TrazIA_Edicion',$,(${properties.map(id => `#${id}`).join(",")})`,
    );
    model.add(
      "IFCRELDEFINESBYPROPERTIES",
      `${stepText(guid(`edicion/${tag}/rel`))},${ownerHistory},$,$,(#${root.id}),#${pset}`,
    );
  }
  return { text: model.toString(), changed };
}

export type NominalField = "length" | "width" | "height";
export type NominalAdjustment = { tag: string; field: NominalField; value: number };

const nominalProps: Record<NominalField, string> = {
  length: "NominalLengthM", width: "NominalWidthM", height: "NominalHeightM",
};

/** Lee las cotas nominales publicadas en TrazIA_Traceability del equipo. */
export function nominalOf(model: StepModel, tag: string): Partial<Record<NominalField, { id: number; value: number }>> {
  const root = model.byTag(tag);
  const found: Partial<Record<NominalField, { id: number; value: number }>> = {};
  if (!root) return found;
  for (const rel of model.ofType("IFCRELDEFINESBYPROPERTIES")) {
    const args = splitArgs(rel.args);
    if (!(args[4] ?? "").split(/[(),]/).includes(`#${root.id}`)) continue;
    const pset = ref(args[5]);
    if (pset === null || model.get(pset)?.type !== "IFCPROPERTYSET") continue;
    const psetArgs = model.args(pset);
    if (psetArgs[2] !== "'TrazIA_Traceability'") continue;
    for (const id of (psetArgs[4] ?? "").match(/#\d+/g) ?? []) {
      const property = model.args(Number(id.slice(1)));
      const field = (Object.keys(nominalProps) as NominalField[]).find(key => property[0] === `'${nominalProps[key]}'`);
      const value = Number(/\(([-\d.eE+]+)\)/.exec(property[2] ?? "")?.[1]);
      if (field && Number.isFinite(value)) found[field] = { id: Number(id.slice(1)), value };
    }
  }
  return found;
}

/**
 * Ejes del modelo que sigue cada cota nominal según la familia del equipo. El ancho de un
 * recipiente horizontal es su diámetro (Y y Z); en verticales, columnas y tanques es el
 * diámetro en planta (X e Y).
 */
export function nominalAxes(family: string, field: NominalField): number[] {
  if (field === "length") return [0];
  if (field === "height") return [2];
  if (family === "horizontal") return [1, 2];
  if (["vertical", "column", "tank"].includes(family)) return [0, 1];
  return [1];
}

/**
 * Cambios de prueba sobre cotas nominales de equipos, sin API: escala la geometría IFC en
 * proporción a la cota pedida y actualiza la propiedad nominal publicada.
 */
export function applyNominalEdits(text: string, adjustments: NominalAdjustment[], families: Record<string, string>): EditResult {
  const model = new StepModel(text);
  const edits: Record<string, EquipmentEdit> = {};
  const updates: [number, number][] = [];
  for (const { tag, field, value } of adjustments) {
    const current = nominalOf(model, tag)[field];
    if (!current || current.value <= 0 || !(value > 0)) continue;
    const scale = (edits[tag]?.scale ?? [1, 1, 1]) as [number, number, number];
    for (const axis of nominalAxes(families[tag] ?? "", field)) scale[axis]! *= value / current.value;
    edits[tag] = { scale };
    updates.push([current.id, value]);
  }
  for (const [id, value] of updates) {
    const args = model.args(id);
    args[2] = `IFCREAL(${real(value)})`;
    model.set(id, args.join(","));
  }
  return applyEquipmentEdits(model.toString(), edits);
}

/** Lineas cuyos extremos tocan un equipo cambiado: su puerto ya no coincide con la tubería. */
export function linesToReview(lines: { tag: string; start: string; end: string }[], changed: string[]) {
  const set = new Set(changed);
  return lines.filter(line => set.has(line.start) || set.has(line.end)).map(line => line.tag);
}

export { unquote };
