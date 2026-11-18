"use client";

import { useRef, useState, type FormEvent } from "react";
import { Button, Panel } from "@/components/ui/primitives";
import { usePipeline } from "@/stores/pipeline";
import { PROFILES, type Strategy } from "./graph-model";

const field = "w-full rounded-[var(--radius-control)] border border-border-strong bg-surface px-3 py-2 text-sm";
const formats = /\.(pdf|xlsx|png|jpe?g)$/i;
const convention = /^(?:GAD|GA|HDM|VESOR|ESTRUCTURA)_(.+?)(?:_rev([^_.]+))?\.[^.]+$/i;

function suggestions(files: File[]) {
  const names = files.flatMap(file => {
    const match = file.name.match(convention);
    return match ? [{ tag: match[1], revision: match[2] }] : [];
  });
  const tags = [...new Set(names.map(name => name.tag))];
  const revisions = [...new Set(names.flatMap(name => name.revision ? [name.revision] : []))];
  return { tag: tags.length === 1 ? tags[0] ?? "" : "", revision: revisions.length === 1 ? revisions[0] ?? "" : "",
    mixed: tags.length > 1 || revisions.length > 1 };
}

export function IntakeForm({ strategy, setStrategy }: { strategy: Strategy; setStrategy: (value: Strategy) => void }) {
  const running = usePipeline(state => state.running);
  const submit = usePipeline(state => state.submit);
  const [files, setFiles] = useState<File[]>([]);
  const [tag, setTag] = useState("");
  const [revision, setRevision] = useState("");
  const [equipmentId, setEquipmentId] = useState("");
  const [mixed, setMixed] = useState(false);
  const [error, setError] = useState("");
  const attempt = useRef<{ key: string; input: string } | null>(null);
  const picker = useRef<HTMLInputElement>(null);

  function choose(list: File[]) {
    const detected = suggestions(list);
    setFiles(list);
    setTag(detected.tag);
    setRevision(detected.revision);
    setEquipmentId("");
    setMixed(detected.mixed);
    setError("");
    attempt.current = null;
  }

  async function process(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const id = equipmentId.trim() || tag.trim();
    const destination = revision.trim();
    if (mixed || !files.length || files.length > 30 || files.some(file =>
      !formats.test(file.name) || !file.size || file.size > 25 * 1024 * 1024)) {
      setError(mixed ? "Se han detectado varios equipos o revisiones en los nombres. Selecciona solo los documentos de una revisión."
        : "Selecciona entre 1 y 30 archivos PDF, XLSX, PNG o JPEG, de hasta 25 MiB cada uno.");
      return;
    }
    if (!/^[A-Za-z0-9_-]+$/.test(id) || !destination || /[:/\\\r\n]/.test(destination) || !tag.trim()) {
      setError("Indica el tag, un ID estable con letras, números, guiones o guiones bajos y una revisión sin barras ni dos puntos.");
      return;
    }
    const input = {
      project_id: String(data.get("project")).trim(), equipment_id: id,
      tag: tag.trim(), revision: destination, strategy,
      dataset: data.get("dataset") === "real" ? "real" as const : "synthetic" as const,
    };
    const serialized = JSON.stringify(input);
    if (attempt.current?.input !== serialized) attempt.current = { key: crypto.randomUUID(), input: serialized };
    setError("");
    const jobId = await submit({ input, files }, attempt.current.key);
    if (jobId) {
      attempt.current = null;
      if (picker.current) picker.current.value = "";
      setFiles([]);
    }
  }

  return (
    <Panel className="p-5">
      <form aria-label="Procesar planos y hojas de datos" onSubmit={process}
        onDragOver={event => event.preventDefault()} onDrop={event => {
          event.preventDefault();
          if (!running) choose(Array.from(event.dataTransfer.files));
        }}>
        <h2 className="text-[15px] font-semibold text-strong">Procesar planos y hojas de datos</h2>
        <p className="mt-1 text-sm text-muted">Suelta los archivos de un equipo y una revisión. La API guarda los originales, ejecuta la lectura y genera un IFC DRAFT.</p>
        <fieldset disabled={running} className="mt-4 grid gap-3 md:grid-cols-3">
          <label className="grid gap-1 text-sm md:col-span-2">Archivos de entrada
            <input ref={picker} aria-label="Documentos para procesar" type="file" multiple accept=".pdf,.xlsx,.png,.jpg,.jpeg"
              onChange={event => choose(Array.from(event.currentTarget.files ?? []))} className={field} />
          </label>
          <label className="grid gap-1 text-sm">Origen
            <select name="dataset" aria-label="Origen de documentos" defaultValue="synthetic" className={field}>
              <option value="synthetic">Sintéticos de prueba</option>
              <option value="real">Datos reales del reto</option>
            </select>
          </label>
          <label className="grid gap-1 text-sm">Proyecto
            <input name="project" required pattern="[A-Za-z0-9_\-]+" defaultValue="ENSAYO" maxLength={80} className={field} />
          </label>
          <label className="grid gap-1 text-sm">Tag del equipo
            <input value={tag} required maxLength={120} onChange={event => setTag(event.target.value)} className={field} />
          </label>
          <label className="grid gap-1 text-sm">Revisión
            <input value={revision} required maxLength={50} onChange={event => setRevision(event.target.value)} className={field} />
          </label>
          <label className="grid gap-1 text-sm">ID estable del equipo
            <input value={equipmentId} placeholder={tag || "Igual al tag si se deja vacío"} maxLength={120}
              onChange={event => setEquipmentId(event.target.value)} className={field} />
          </label>
          <label className="grid gap-1 text-sm">Estrategia
            <select aria-label="Estrategia de lectura" value={strategy} onChange={event => setStrategy(event.target.value as Strategy)} className={field}>
              {Object.entries(PROFILES).map(([value, profile]) => <option key={value} value={value}>{profile.name}</option>)}
            </select>
          </label>
          <div className="flex items-end">
            <Button type="submit" variant="primary" disabled={!files.length || mixed}>Procesar documentos</Button>
          </div>
        </fieldset>
        {files.length ? <p className="mt-3 break-words text-xs text-muted">{files.map(file => file.name).join(" · ")}</p> : null}
        {mixed || error ? <p role="alert" className="mt-2 text-sm text-danger">{error || "Selecciona archivos de un solo equipo y una sola revisión."}</p> : null}
      </form>
    </Panel>
  );
}
