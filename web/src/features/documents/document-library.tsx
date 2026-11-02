"use client";

import { FileUp, FolderOpen, Plus, Shapes } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { Segmented } from "@/components/ui/controls";
import { Button, Icon, Panel } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { useMounted } from "@/lib/use-mounted";
import { kindFromFilename, saveDocument, tagFromFilename, useCatalogue } from "./catalogue";
import { DocumentsTab, fieldClass } from "./documents-tab";
import { FamiliesTab } from "./families-tab";
import { projectFamilies, ProjectsTab } from "./projects-tab";

export type LibraryView = "documentos" | "proyectos" | "familias";
const VIEWS: LibraryView[] = ["documentos", "proyectos", "familias"];
type FormKind = "family" | "project" | "design";
const FORM_TITLE: Record<FormKind, string> = { family: "Nueva familia", project: "Nuevo proyecto", design: "Añadir diseño" };

export function DocumentLibrary() {
  const catalogue = useCatalogue();
  const mounted = useMounted();
  const params = useSearchParams();
  const router = useRouter();
  const raw = params.get("vista") as LibraryView | null;
  const view: LibraryView = raw && VIEWS.includes(raw) ? raw : "documentos";
  const setView = (v: LibraryView) => router.replace(v === "documentos" ? "/documentos" : `/documentos?vista=${v}`, { scroll: false });

  const [family, setFamily] = useState("all");
  const [project, setProject] = useState("all");
  const [form, setForm] = useState<FormKind | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = String(data.get("name") ?? "").trim();
    if (!name) return;
    setError("");
    setBusy(true);
    try {
      if (form === "family") {
        setFamily(catalogue.addFamily(name));
        setProject("all");
      }
      if (form === "project") {
        catalogue.addProject(name);
        setProject("all");
      }
      if (form === "design") {
        const file = data.get("file");
        if (!(file instanceof File) || !file.size) throw new Error("Selecciona un documento para el diseño.");
        if (file.size > 50 * 1024 * 1024) throw new Error("El documento supera 50 MB. Selecciona un archivo más pequeño.");
        const id = crypto.randomUUID();
        await saveDocument(id, file);
        catalogue.addDesign({
          id,
          name,
          family: String(data.get("family")),
          project: String(data.get("project")),
          filename: file.name,
          size: file.size,
          kind: kindFromFilename(file.name),
          // Si el nombre ya es el equipo (V-202), la columna Equipo no lo repite
          tag: tagFromFilename(name) ? undefined : tagFromFilename(file.name),
          stage: "recibido",
          received: new Date().toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit", year: "numeric" }),
        });
        setFamily(String(data.get("family")));
        setProject("all");
        if (view !== "documentos") setView("documentos");
      }
      setForm(null);
      toast.success("Guardado en este navegador");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar. Comprueba el espacio disponible del navegador.");
    } finally {
      setBusy(false);
    }
  }

  if (!mounted) return <p role="status" className="p-6 text-sm text-muted">Cargando catálogo…</p>;

  const counts = (id: string) =>
    view === "proyectos"
      ? catalogue.projects.filter((p) => id === "all" || projectFamilies(p, catalogue.designs).includes(id)).length
      : catalogue.designs.filter((d) => id === "all" || d.family === id).length;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-strong">Documentos</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted">
            Documentos, proyectos y familias en un mismo lugar. Cada diseño se clasifica en una familia y un proyecto. Los archivos se conservan
            en este navegador y no se envían a servicios externos.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => (setForm("family"), setError(""))}>
            <Icon icon={Shapes} /> Nueva familia
          </Button>
          <Button onClick={() => (setForm("project"), setError(""))}>
            <Icon icon={FolderOpen} /> Nuevo proyecto
          </Button>
          <Button variant="primary" onClick={() => (setForm("design"), setError(""))}>
            <Icon icon={FileUp} /> Añadir diseño
          </Button>
        </div>
      </header>

      {form ? (
        <Panel className="p-5">
          <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2" aria-label={FORM_TITLE[form]}>
            <h2 className="text-lg font-semibold sm:col-span-2">{FORM_TITLE[form]}</h2>
            <label className="space-y-2 text-sm">
              Nombre
              <input name="name" required maxLength={120} autoFocus className={fieldClass} />
            </label>
            {form === "design" ? (
              <>
                <label className="space-y-2 text-sm">
                  Documento
                  <input type="file" name="file" required accept=".pdf,.xlsx,.xls,.ifc,.png,.jpg,.jpeg" className="w-full rounded-[var(--radius-control)] border border-border-strong bg-surface px-3 py-1.5 text-[13px] text-text" />
                </label>
                <label className="space-y-2 text-sm">
                  Familia
                  <select aria-label="Familia" name="family" defaultValue={family === "all" ? "vertical" : family} className={fieldClass}>
                    {catalogue.families.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="space-y-2 text-sm">
                  Proyecto
                  <select aria-label="Proyecto" name="project" defaultValue={project === "all" ? "demo" : project} className={fieldClass}>
                    {catalogue.projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </label>
              </>
            ) : null}
            {form === "family" ? (
              <p className="self-end text-sm text-muted">Puedes clasificar documentos en una familia nueva. La creación de su plantilla geométrica se revisa por separado.</p>
            ) : null}
            {error ? (
              <p role="alert" className="text-sm text-danger sm:col-span-2">
                {error}
              </p>
            ) : null}
            <div className="flex gap-2 sm:col-span-2">
              <Button type="submit" variant="primary" disabled={busy}>
                <Icon icon={Plus} />
                {busy ? "Guardando…" : "Guardar"}
              </Button>
              <Button type="button" onClick={() => setForm(null)}>
                Cancelar
              </Button>
            </div>
          </form>
        </Panel>
      ) : null}

      <Segmented<LibraryView>
        label="Sección de documentos"
        value={view}
        onChange={setView}
        options={[
          { value: "documentos", label: "Documentos" },
          { value: "proyectos", label: "Proyectos" },
          { value: "familias", label: "Familias" },
        ]}
      />

      {view === "familias" ? (
        <FamiliesTab
          selected={family}
          onOpen={(id, next) => {
            setFamily(id);
            setProject("all");
            setView(next);
          }}
        />
      ) : (
        <div className="grid gap-5 xl:grid-cols-[230px_minmax(0,1fr)]">
          <Panel className="h-fit p-3">
            <h2 className="px-2 py-2 text-sm font-semibold">Familias</h2>
            <nav aria-label="Familias de documentos" className="space-y-1">
              {[{ id: "all", name: "Todas las familias" }, ...catalogue.families].map((f) => (
                <button
                  key={f.id}
                  onClick={() => {
                    setFamily(f.id);
                    setProject("all");
                  }}
                  aria-pressed={family === f.id}
                  className={cn(
                    "flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm",
                    family === f.id ? "bg-accent-soft text-accent-text" : "text-muted hover:bg-surface-raised",
                  )}
                >
                  <span>{f.name}</span>
                  <span className="text-xs tabular-nums">{counts(f.id)}</span>
                </button>
              ))}
            </nav>
          </Panel>
          <div className="min-w-0">
            {view === "documentos" ? (
              <DocumentsTab family={family} project={project} onProject={setProject} />
            ) : (
              <ProjectsTab
                family={family}
                onOpenProject={(id) => {
                  setProject(id);
                  setView("documentos");
                }}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
