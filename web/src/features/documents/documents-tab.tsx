"use client";

import { FileUp } from "lucide-react";
import Link from "next/link";
import { useRef, useState, type DragEvent } from "react";
import { toast } from "sonner";

import { Badge, Button, Icon, Panel, PanelHeader } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import type { DocStage } from "@/lib/mock/bocetos";
import { kindFromFilename, loadDocument, saveDocument, tagFromFilename, useCatalogue, type Design } from "./catalogue";

const fieldBase =
  "h-9 rounded-[var(--radius-control)] border border-border-strong bg-surface px-3 text-[13px] text-text outline-none focus-visible:border-accent";
export const fieldClass = `${fieldBase} w-full`;
const ACCEPT = ".pdf,.xlsx,.xls,.ifc,.png,.jpg,.jpeg";
const MAX_BYTES = 50 * 1024 * 1024;
const STAGES: DocStage[] = ["recibido", "leído", "revisado"];

function StageTrack({ stage }: { stage: DocStage }) {
  const at = STAGES.indexOf(stage);
  return (
    <div className="flex items-center gap-1.5" aria-label={`Estado: ${stage}`}>
      {STAGES.map((s, i) => (
        <span key={s} className="flex items-center gap-1.5">
          {i > 0 ? <span className={cn("h-px w-4", i <= at ? "bg-accent" : "bg-border-strong")} aria-hidden /> : null}
          <span
            title={s}
            className={cn("size-2 rounded-full", i < at ? "bg-accent" : i === at ? "bg-accent ring-3 ring-accent-soft" : "bg-border-strong")}
            aria-hidden
          />
        </span>
      ))}
      <span className="ml-1.5 text-[12px] text-muted capitalize">{stage}</span>
    </div>
  );
}

const today = () => new Date().toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit", year: "numeric" });

export function DocumentsTab({
  family,
  project,
  onProject,
}: {
  family: string;
  project: string;
  onProject: (id: string) => void;
}) {
  const catalogue = useCatalogue();
  const [over, setOver] = useState(false);
  const [query, setQuery] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const [target, setTarget] = useState({ family: family === "all" ? "vertical" : family, project: project === "all" ? "demo" : project });
  // El destino sigue al filtro activo mientras el usuario no lo cambie a mano
  const [lastFilter, setLastFilter] = useState({ family, project });
  if (lastFilter.family !== family || lastFilter.project !== project) {
    setLastFilter({ family, project });
    setTarget((t) => ({ family: family === "all" ? t.family : family, project: project === "all" ? t.project : project }));
  }

  const inFamily = catalogue.designs.filter((d) => family === "all" || d.family === family);
  const projects = catalogue.projects.filter((p) => inFamily.some((d) => d.project === p.id));
  const q = query.trim().toLocaleLowerCase();
  const visible = inFamily.filter(
    (d) =>
      (project === "all" || d.project === project) &&
      (!q || `${d.name} ${d.filename ?? ""} ${d.tag ?? ""}`.toLocaleLowerCase().includes(q)),
  );

  async function add(files: FileList | null) {
    if (!files?.length) return;
    const list = [...files];
    const tooBig = list.filter((f) => f.size > MAX_BYTES);
    const ok = list.filter((f) => f.size <= MAX_BYTES && f.size > 0);
    let saved = 0;
    for (const file of ok) {
      const id = crypto.randomUUID();
      try {
        await saveDocument(id, file);
      } catch {
        toast.error(`No se pudo guardar ${file.name}. Comprueba el espacio disponible del navegador.`);
        continue;
      }
      catalogue.addDesign({
        id,
        name: file.name.replace(/\.[^.]+$/, ""),
        filename: file.name,
        size: file.size,
        family: target.family,
        project: target.project,
        kind: kindFromFilename(file.name),
        tag: tagFromFilename(file.name),
        stage: "recibido",
        received: today(),
      });
      saved++;
    }
    if (tooBig.length) toast.error(`${tooBig.map((f) => f.name).join(", ")} supera 50 MB. Elige un archivo más pequeño.`);
    if (saved) {
      const familyName = catalogue.families.find((f) => f.id === target.family)?.name ?? "la familia elegida";
      toast.success(saved === 1 ? `Documento añadido a ${familyName}` : `${saved} documentos añadidos a ${familyName}`);
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setOver(false);
    void add(e.dataTransfer.files);
  }

  async function download(d: Design) {
    try {
      const blob = await loadDocument(d.id);
      if (!blob) throw new Error("El documento no está disponible en este navegador. Vuelve a añadirlo.");
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = d.filename!;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "No se pudo abrir el documento");
    }
  }

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
        data-testid="document-dropzone"
        className={cn(
          "flex flex-col items-center justify-center gap-2 rounded-[var(--radius-panel)] border border-dashed px-6 py-9 text-center transition-[border-color,background-color] duration-200",
          over ? "border-accent bg-accent-soft" : "border-border-strong bg-surface",
        )}
      >
        <span
          className={cn(
            "flex size-11 items-center justify-center rounded-full border transition-transform duration-200",
            over ? "scale-110 border-accent text-accent" : "border-border text-muted",
          )}
        >
          <Icon icon={FileUp} size={20} />
        </span>
        <p className="text-[15px] font-medium text-strong">Suelta aquí los planos GA y las hojas de datos</p>
        <p className="text-[13px] text-muted">
          o{" "}
          <button type="button" onClick={() => input.current?.click()} className="text-accent-text underline-offset-2 hover:underline">
            elígelos en tu equipo
          </button>
          . Se guardan en este navegador; no se envían a ningún servicio.
        </p>
        <div className="mt-2 flex flex-wrap items-center justify-center gap-2 text-[13px] text-muted">
          <span>Se añaden a</span>
          <select
            aria-label="Familia de destino"
            value={target.family}
            onChange={(e) => setTarget((t) => ({ ...t, family: e.target.value }))}
            className={cn(fieldBase, "w-60 max-w-full")}
          >
            {catalogue.families.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
          <span>en</span>
          <select
            aria-label="Proyecto de destino"
            value={target.project}
            onChange={(e) => setTarget((t) => ({ ...t, project: e.target.value }))}
            className={cn(fieldBase, "w-60 max-w-full")}
          >
            {catalogue.projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          multiple
          className="sr-only"
          aria-label="Elegir documentos"
          onChange={(e) => {
            void add(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      <Panel>
        <PanelHeader
          title="Bandeja de documentos"
          description="Cada documento pasa por recibido, leído y revisado. Cambia su familia o proyecto desde la tabla."
          actions={
            <input
              type="search"
              aria-label="Buscar diseños"
              placeholder="Buscar documento o equipo"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className={cn(fieldBase, "w-60")}
            />
          }
        />
        <div className="flex flex-wrap gap-2 px-5 pb-3" role="group" aria-label="Filtrar por proyecto">
          <Button size="sm" onClick={() => onProject("all")} aria-pressed={project === "all"}>
            Todos los proyectos
          </Button>
          {projects.map((p) => (
            <Button key={p.id} size="sm" onClick={() => onProject(p.id)} aria-pressed={project === p.id}>
              {p.name}
            </Button>
          ))}
        </div>
        <div className="overflow-x-auto px-3 pb-3">
          <table className="w-full min-w-[1080px] border-separate border-spacing-0 text-[13px]">
            <thead>
              <tr className="text-left text-xs text-muted">
                {["Documento", "Tipo", "Equipo", "Rev.", "Estado", "Familia", "Proyecto", "Recibido"].map((h, i, a) => (
                  <th
                    key={h}
                    className={cn(
                      "border-y border-border bg-surface-sunken px-3 py-2.5 font-medium",
                      i === 0 && "rounded-l-[var(--radius-control)] border-l",
                      i === a.length - 1 && "rounded-r-[var(--radius-control)] border-r",
                    )}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.map((d) => (
                <tr key={d.id} className="animate-[row-in_var(--dur-slow)_var(--ease-out)]">
                  <td className="border-b border-border px-3 py-2.5 whitespace-nowrap">
                    <span className="block font-medium text-strong">{d.name}</span>
                    {d.demo ? (
                      <Link className="text-[12px] text-accent-text underline-offset-2 hover:underline" href="/modelo">
                        Abrir en Modelo
                      </Link>
                    ) : d.example ? (
                      <Badge tone="warning">ejemplo</Badge>
                    ) : d.filename ? (
                      <button className="font-mono text-[12px] text-accent-text underline-offset-2 hover:underline" onClick={() => void download(d)}>
                        {d.filename}
                      </button>
                    ) : null}
                  </td>
                  <td className="border-b border-border px-3 py-2.5 text-muted">{d.kind ?? "—"}</td>
                  <td className="border-b border-border px-3 py-2.5 font-mono text-[12px]">{d.tag ?? "—"}</td>
                  <td className="border-b border-border px-3 py-2.5">{d.rev ?? "—"}</td>
                  <td className="border-b border-border px-3 py-2.5">
                    <StageTrack stage={d.stage ?? "recibido"} />
                  </td>
                  <td className="border-b border-border px-3 py-2.5">
                    <select
                      aria-label={`Familia de ${d.name}`}
                      className={cn(fieldBase, "w-48")}
                      value={d.family}
                      onChange={(e) => catalogue.assign(d.id, e.target.value, d.project)}
                    >
                      {catalogue.families.map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="border-b border-border px-3 py-2.5">
                    <select
                      aria-label={`Proyecto de ${d.name}`}
                      className={cn(fieldBase, "w-52")}
                      value={d.project}
                      onChange={(e) => catalogue.assign(d.id, d.family, e.target.value)}
                    >
                      {catalogue.projects.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="border-b border-border px-3 py-2.5 text-muted tabular-nums">{d.received ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!visible.length ? (
            <p className="p-6 text-center text-sm text-muted">No hay documentos con estos filtros. Suelta uno arriba o elige otra familia.</p>
          ) : null}
        </div>
      </Panel>
    </div>
  );
}
