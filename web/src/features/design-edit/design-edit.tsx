"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, CircleCheck, Eye, History, MessageSquareText, PencilRuler, RotateCcw, Undo2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { IfcViewer } from "@/components/three";
import { FullscreenFrame } from "@/components/shell/fullscreen";
import { Segmented } from "@/components/ui/controls";
import { Badge, Button, EmptyState, Icon, Panel, PanelHeader, Skeleton } from "@/components/ui/primitives";
import { apiEnabled } from "@/lib/api/config";
import { getJob, subscribeJob } from "@/lib/api/client";
import { formatValue } from "@/lib/format";
import { useEquipment } from "@/lib/queries";
import { useDemoUser } from "@/lib/session";
import { useSelection } from "@/stores/selection";

import {
  STATUS_LABEL, applyProposal, designReportUrl, interpretRequest, createProposal, discardProposal, getCatalog, getProposal, listProposals,
  previewIfcUrl, replaceProposal, revertProposal, revisionIdentity, revisionIfcUrl, startPreview,
  type Datum, type IntentDraft, type Issue, type Proposal, type Target,
} from "./api";
import {
  clarifiedText, draftSignature, draftsFromOperations, elementStates, groupForSelection, groups, issuesFor,
  toOperations, unitsFor, type Drafts,
} from "./form";

const EDITABLE = new Set(["draft", "needs_clarification", "invalid", "ready", "previewed"]);
const DATUM_LABEL: Record<Datum, string> = {
  suelo: "sobre el suelo", tangente_inferior: "sobre la tangente inferior", interno: "convenio interno", norte: "Norte",
};
const control = "w-full rounded-[var(--radius-control)] border border-border bg-surface px-2 py-1.5 text-[13px] text-text";

function tone(status: Proposal["status"]) {
  return status === "previewed" || status === "applied" ? "approved"
    : status === "invalid" || status === "stale" ? "danger"
      : status === "needs_clarification" ? "warning" : "neutral";
}

/** K.4 · Proponer cambios de diseño desde Modelo: formulario → validar → previsualizar → confirmar. */
export function DesignEditWorkspace({ tag = "V-101" }: { tag?: string }) {
  if (!apiEnabled) {
    return <Panel><EmptyState icon={PencilRuler} title="La edición asistida necesita la API local">
      Arranca <code>uv run trazia serve</code> y define NEXT_PUBLIC_API_URL. Sin API no se simulan propuestas.
    </EmptyState></Panel>;
  }
  return <Workspace tag={tag} />;
}

function Workspace({ tag }: { tag: string }) {
  const qc = useQueryClient();
  const user = useDemoUser();
  const selectedId = useSelection((s) => s.selectedId);
  const select = useSelection((s) => s.setSelected);
  const equipment = useEquipment();
  const labels = equipment.data?.find((row) => row.tag === tag)?.revisions ?? ["B"];
  const [label, setLabel] = useState<string>("B");
  const identity = useQuery({ queryKey: ["design-identity", tag, label], queryFn: () => revisionIdentity(tag, label) });
  const catalog = useQuery({
    queryKey: ["design-catalog", identity.data?.identity, identity.data?.etag],
    queryFn: () => getCatalog(identity.data!.identity), enabled: !!identity.data,
  });
  const history = useQuery({
    queryKey: ["design-history", identity.data?.identity, identity.data?.etag],
    queryFn: () => listProposals(identity.data!.identity), enabled: !!identity.data,
  });

  const [group, setGroup] = useState(() => groupForSelection(selectedId));
  const [drafts, setDrafts] = useState<Drafts>({});
  const [reason, setReason] = useState("");
  const [actor, setActor] = useState(user ?? "");
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [signature, setSignature] = useState("");
  const [steps, setSteps] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [side, setSide] = useState<"antes" | "despues">("despues");
  const applyKey = useRef<{ id: string; key: string } | null>(null);
  const stopStream = useRef<(() => void) | null>(null);
  const pending = useRef<Proposal | null>(null);
  const [request, setRequest] = useState("");
  const [useModel, setUseModel] = useState(false);
  const [intent, setIntent] = useState<IntentDraft | null>(null);

  useEffect(() => { if (user && !actor) setActor(user); }, [user, actor]);
  useEffect(() => { setGroup(groupForSelection(selectedId)); }, [selectedId]);
  useEffect(() => () => stopStream.current?.(), []);
  // Cambiar de base empieza de cero: una propuesta pertenece a una revisión concreta.
  useEffect(() => {
    setProposal(pending.current); pending.current = null; setDrafts({}); setSteps([]); setIntent(null);
  }, [label]);

  const targets = useMemo(() => catalog.data?.targets ?? [], [catalog.data]);
  const visible = targets.filter((t) => t.group === group);
  const operations = toOperations(drafts, targets);
  const dirty = !!proposal && proposal.kind === "cambio_diseno" && signature !== draftSignature(operations, reason);
  const editable = !proposal || (proposal.kind === "cambio_diseno" && EDITABLE.has(proposal.status));
  const preview = proposal?.preview && !dirty ? proposal.preview : null;
  const issues = proposal?.issues ?? [];
  const states = useMemo(() => elementStates(preview, dirty ? [] : issues), [preview, issues, dirty]);
  const base = proposal?.base ?? (identity.data && catalog.data
    ? { revision_id: identity.data.identity, version: catalog.data.version, revision: catalog.data.revision } : null);
  const ifcUrl = preview && side === "despues" ? previewIfcUrl(preview)
    : base ? revisionIfcUrl(base.revision_id, base.version) : "";
  const name = actor.trim();
  const canValidate = editable && name.length >= 2 && reason.trim().length >= 3 && operations.length > 0 && !busy;

  function setDraft(target: Target, patch: Partial<Drafts[string]>) {
    setDrafts((old) => ({ ...old, [target.target]: {
      value: old[target.target]?.value ?? "", unit: old[target.target]?.unit ?? target.unit,
      datum: old[target.target]?.datum ?? target.datums[0], ...patch,
    } }));
  }

  async function run<T>(step: string, action: () => Promise<T>): Promise<T | undefined> {
    setBusy(step);
    try { return await action(); }
    catch (error) { toast.error(error instanceof Error ? error.message : "No se pudo completar la acción"); }
    finally { setBusy(null); }
  }

  const validate = () => run("validar", async () => {
    if (!identity.data) return;
    // Si el lote viene del chat se conserva la petición original; el contenido es el del formulario.
    const fromChat = !!intent && intent.request_text.trim() !== "";
    const body = {
      operations, reason: reason.trim(), actor: name, origin: fromChat ? "chat" as const : "formulario" as const,
      request_text: fromChat ? intent?.request_text ?? null : null,
    };
    const result = proposal && proposal.kind === "cambio_diseno" && EDITABLE.has(proposal.status)
      ? await replaceProposal(proposal.id, body)
      : await createProposal(identity.data.identity, identity.data.etag, body);
    setProposal(result); setSignature(draftSignature(operations, reason)); setSteps([]);
    applyKey.current = null;
  });

  const runPreview = () => run("previsualizar", async () => {
    if (!proposal) return;
    const job = await startPreview(proposal.id);
    setSteps([]);
    setBusy("previsualizar");
    await new Promise<void>((resolve) => {
      stopStream.current?.();
      stopStream.current = subscribeJob(job.job_id,
        (event) => { if (event.stage !== "job") setSteps((old) => [...old, event.detail]); },
        async (status) => {
          if (status !== "done") {
            const detail = (await getJob(job.job_id).catch(() => null))?.error;
            toast.error(detail ?? `Previsualización ${status}`, { description: "La revisión base no ha cambiado." });
          }
          setProposal(await getProposal(proposal.id));
          resolve();
        },
        () => { toast.error("Se perdió el seguimiento; recarga la propuesta"); resolve(); });
    });
    setSide("despues");
  });

  const confirm = () => run("confirmar", async () => {
    if (!proposal?.preview) return;
    // Reintentar la misma confirmación usa la misma clave: nunca dos revisiones.
    if (applyKey.current?.id !== proposal.id + proposal.preview.ifc_sha256)
      applyKey.current = { id: proposal.id + proposal.preview.ifc_sha256, key: crypto.randomUUID() };
    const result = await applyProposal(proposal, name, applyKey.current.key);
    setProposal(result.proposal);
    toast.success(`Revisión ${result.proposal.target_revision} creada como DRAFT`, {
      description: "La revisión base se conserva. La aprobación técnica sigue siendo una acción posterior.",
    });
    await qc.invalidateQueries({ queryKey: ["equipment"] });
    await qc.invalidateQueries({ queryKey: ["design-history"] });
  });

  const ask = (text: string) => run("interpretar", async () => {
    if (!identity.data || !text.trim()) return;
    const result = await interpretRequest(identity.data.identity, text.trim(), selectedId, useModel);
    setIntent(result);
    if (result.operations.length) {
      const filled = draftsFromOperations(result.operations, targets);
      setDrafts(filled);
      const first = targets.find((t) => t.target in filled);
      if (first) setGroup(first.group);
      if (!reason.trim()) setReason(`Petición: «${text.trim().slice(0, 200)}»`);
    }
  });

  const discard = () => run("descartar", async () => {
    if (!proposal) return;
    await discardProposal(proposal.id, name || "Revisor local");
    setProposal(null); setSteps([]);
  });

  const undo = (applied: Proposal) => run("deshacer", async () => {
    const target = applied.target_revision;
    const current = await revisionIdentity(tag, target);
    const reversion = await revertProposal(applied.id, current.etag, name || applied.actor,
      `Deshacer la orden ${applied.id.slice(0, 8)} sobre ${applied.base.revision}`);
    // La propuesta de deshacer pertenece a la revisión derivada: se fija al cambiar de base.
    pending.current = reversion;
    if (label === target) { setProposal(reversion); pending.current = null; } else setLabel(target);
  });

  if (identity.isLoading || catalog.isLoading) return <Skeleton className="h-[620px]" />;
  if (identity.error || catalog.error || !catalog.data)
    return <Panel><EmptyState icon={CircleAlert} title="No se pudo cargar el catálogo de operaciones">
      {(identity.error ?? catalog.error)?.message}
    </EmptyState></Panel>;

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_440px]" data-testid="design-edit">
      <FullscreenFrame
        title="Antes y después en el IFC"
        description={preview
          ? "Después: IFC temporal generado y validado con estos parámetros. No es una revisión hasta confirmar."
          : "Revisión base. Valida y previsualiza para ver el IFC de la propuesta."}
        height="h-[min(72vh,760px)] min-h-[460px]"
        actions={<>
          <span className="text-[12px] text-warning">Datos sintéticos · {tag} · DRAFT</span>
          <Segmented<"antes" | "despues"> label="Revisión mostrada" value={preview ? side : "antes"} onChange={setSide}
            options={[{ value: "antes", label: `Antes · ${base?.revision ?? label}` },
              { value: "despues", label: preview ? `Después · ${preview.target_revision}` : "Después" }]} />
        </>}
      >
        {ifcUrl ? <IfcViewer ifcUrl={ifcUrl} selectedId={selectedId ?? undefined} onSelect={(id) => select(id)}
          elementStates={side === "despues" ? states : undefined} /> : <Skeleton className="h-full" />}
      </FullscreenFrame>

      <Panel className="flex min-h-0 flex-col">
        <PanelHeader title="Proponer cambios de diseño"
          description="Cambia el diseño, no la lectura. Se crea una revisión DRAFT nueva; el plano original no se toca."
          actions={proposal ? <Badge tone={tone(proposal.status)}>{STATUS_LABEL[proposal.status]}</Badge> : null} />
        <div className="space-y-4 overflow-y-auto px-5 pb-5 text-[13px]">
          <div className="grid grid-cols-2 gap-2">
            <label className="space-y-1"><span className="text-muted">Revisión base</span>
              <select className={control} value={label} onChange={(e) => setLabel(e.target.value)} disabled={!!busy}>
                {labels.map((rev) => <option key={rev} value={rev}>Rev {rev}</option>)}
              </select>
            </label>
            <label className="space-y-1"><span className="text-muted">Elemento</span>
              <select className={control} value={group} onChange={(e) => {
                setGroup(e.target.value);
                const nozzle = e.target.value.startsWith("boquilla:") ? `nozzle:${e.target.value.slice(9)}` : null;
                select(nozzle);
              }}>
                {groups(targets).map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}
              </select>
            </label>
          </div>
          {!catalog.data.geometry_supported && <p className="rounded border border-warning-border bg-warning-bg p-2 text-warning">
            Esta familia ({catalog.data.kind}, LOD {catalog.data.lod}) solo admite atributos: su geometría aún no tiene cobertura verificada.
          </p>}
          <p className="text-muted">{catalog.data.datum.elevation} Azimut: {catalog.data.datum.azimuth}</p>

          {editable && <section className="space-y-2 rounded-[var(--radius-card)] border border-border p-3" aria-label="Describir el cambio">
            <label className="block space-y-1">
              <span className="flex items-center gap-1.5 font-medium text-strong"><Icon icon={MessageSquareText} size={14} />Describir el cambio</span>
              <textarea className={control} rows={2} maxLength={2000} value={request} onChange={(e) => setRequest(e.target.value)}
                placeholder="Por ejemplo: cambia la longitud entre tangentes a 7000 mm y la elevación de N3 a 4,2 m" />
            </label>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <label className="flex items-center gap-1.5 text-[12px] text-muted">
                <input type="checkbox" checked={useModel} onChange={(e) => setUseModel(e.target.checked)} />Usar el modelo local si está disponible
              </label>
              <Button size="sm" disabled={!!busy || !request.trim()} onClick={() => ask(request)}>
                {busy === "interpretar" ? "Interpretando…" : "Preparar borrador"}
              </Button>
            </div>
            {intent && <div className="space-y-1 text-[12px]" aria-live="polite">
              <p className="text-muted">{intent.notice} · {intent.provider}</p>
              {intent.operations.length > 0 && <p>Formulario rellenado con {intent.operations.length} cambio(s): revísalos abajo y valida.</p>}
              {intent.notes.map((note, i) => <p key={`n${i}`} className="text-muted">{note}</p>)}
              {intent.rejected.map((message, i) => <p key={`r${i}`} role="alert" className="text-danger">{message}</p>)}
              {intent.clarifications.map((item, i) => <div key={`c${i}`} className="space-y-1">
                <p className="text-warning">{item.question}</p>
                {item.options.length > 0 && <div className="flex flex-wrap gap-1">
                  {item.options.map((option) => <Button key={option} size="sm" variant="secondary" disabled={!!busy} onClick={() => {
                    const text = clarifiedText(request, option); setRequest(text); void ask(text);
                  }}>{targets.find((t) => t.target === option)?.label ?? option}</Button>)}
                </div>}
              </div>)}
            </div>}
          </section>}

          <fieldset disabled={!editable || !!busy} className="space-y-3">
            {visible.length === 0 && <p className="text-muted">No hay operaciones admitidas para este elemento.</p>}
            {visible.map((target) => {
              const draft = drafts[target.target];
              const opIds = proposal?.operations.filter((o) => o.target === target.target).map((o) => o.id) ?? [];
              const own = dirty ? [] : issuesFor(target.target, target.path, issues, opIds);
              const operation = proposal?.operations.find((o) => o.target === target.target);
              const units = unitsFor(target);
              return (
                <div key={target.target} className="space-y-1 rounded-[var(--radius-card)] border border-border p-3">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="font-medium text-strong">{target.label}</span>
                    <span className="text-muted">
                      actual {formatValue(target.current.value, target.current.unit)}
                      {target.current.channel === "diseno" ? " · orden de diseño" : ""}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <input className={control} value={draft?.value ?? ""} placeholder="Sin cambio"
                      inputMode={target.text ? "text" : "decimal"} aria-label={`Nuevo valor de ${target.label}`}
                      aria-invalid={own.some((i) => i.severity === "error")}
                      onChange={(e) => setDraft(target, { value: e.target.value })} />
                    {units.length > 0 && <select className={`${control} w-24`} aria-label={`Unidad de ${target.label}`}
                      value={draft?.unit ?? target.unit} onChange={(e) => setDraft(target, { unit: e.target.value })}>
                      {units.map((u) => <option key={u} value={u}>{u === "deg" ? "°" : u}</option>)}
                    </select>}
                  </div>
                  {target.datums.length > 1 && <select className={control} aria-label={`Referencia de ${target.label}`}
                    value={draft?.datum ?? target.datums[0]} onChange={(e) => setDraft(target, { datum: e.target.value as Datum })}>
                    {target.datums.map((d) => <option key={d} value={d}>Elevación {DATUM_LABEL[d]}</option>)}
                  </select>}
                  <p className="text-[12px] text-muted">{target.rule}</p>
                  {operation?.resolution && !dirty && <p className="text-[12px] text-sky">{operation.resolution}</p>}
                  {own.map((issue, index) => <IssueLine key={index} issue={issue} />)}
                </div>
              );
            })}
            <label className="block space-y-1"><span className="text-muted">Motivo del cambio (obligatorio)</span>
              <textarea className={control} rows={2} maxLength={1000} value={reason} onChange={(e) => setReason(e.target.value)}
                placeholder="Por ejemplo: aumentar capacidad según la hoja de proceso" />
            </label>
            <label className="block space-y-1"><span className="text-muted">Persona que propone</span>
              <input className={control} value={actor} maxLength={100} onChange={(e) => setActor(e.target.value)} />
            </label>
          </fieldset>

          <p className="text-[12px] text-muted">
            ¿El plano dice otra cosa? Eso es <Link className="text-accent-text underline" href="/modelo?vista=revision">corregir la lectura</Link>,
            no cambiar el diseño: las órdenes de diseño no entran en el aprendizaje de extracción.
          </p>

          {proposal && <Summary proposal={proposal} dirty={dirty} />}
          {steps.length > 0 && <ol className="space-y-0.5 text-[12px] text-muted" aria-live="polite">
            {steps.map((s, i) => <li key={i}>{s}</li>)}
          </ol>}

          <div className="flex flex-wrap gap-2">
            {editable && <Button variant={proposal?.status === "ready" && !dirty ? "secondary" : "primary"} disabled={!canValidate} onClick={validate}>
              {busy === "validar" ? "Validando…" : proposal ? "Volver a validar" : "Validar lote"}
            </Button>}
            {proposal && ["ready", "previewed"].includes(proposal.status) && !dirty &&
              <Button variant={proposal.status === "ready" ? "primary" : "secondary"} disabled={!!busy} onClick={runPreview}>
                <Icon icon={Eye} size={14} />{busy === "previsualizar" ? "Generando IFC…" : "Previsualizar"}
              </Button>}
            {proposal?.status === "previewed" && !dirty &&
              <Button variant="primary" disabled={!!busy || name.length < 2} onClick={confirm}>
                <Icon icon={CircleCheck} size={14} />{busy === "confirmar" ? "Confirmando…" : `Confirmar y crear ${proposal.target_revision}`}
              </Button>}
            {proposal && proposal.status !== "applied" && proposal.status !== "discarded" &&
              <Button variant="ghost" disabled={!!busy} onClick={discard}>Descartar</Button>}
            {proposal?.status === "applied" && <>
              <Button variant="secondary" onClick={() => { setLabel(proposal.target_revision); }}>
                Trabajar sobre {proposal.target_revision}
              </Button>
              {!proposal.reverted_by && proposal.kind === "cambio_diseno" &&
                <Button variant="ghost" disabled={!!busy} onClick={() => undo(proposal)}><Icon icon={Undo2} size={14} />Deshacer</Button>}
            </>}
            {proposal?.status === "stale" && <Button variant="secondary" onClick={() => { setProposal(null); void identity.refetch(); }}>
              <Icon icon={RotateCcw} size={14} />Preparar sobre la versión vigente
            </Button>}
          </div>

          <HistoryList proposals={history.data ?? []} busy={!!busy} onUndo={undo} />
        </div>
      </Panel>
    </div>
  );
}

function IssueLine({ issue }: { issue: Issue }) {
  const color = issue.severity === "error" ? "text-danger" : issue.severity === "clarification" ? "text-warning" : "text-muted";
  return <p role={issue.severity === "error" ? "alert" : undefined} className={`text-[12px] ${color}`}>{issue.message}</p>;
}

function Summary({ proposal, dirty }: { proposal: Proposal; dirty: boolean }) {
  const general = proposal.issues.filter((i) => !i.path && !i.operation_id);
  return (
    <section className="space-y-2 rounded-[var(--radius-card)] border border-border bg-surface-sunken p-3" aria-label="Resumen de la propuesta">
      <p className="text-[12px] text-muted">
        {proposal.kind === "reversion" ? "Deshacer" : "Propuesta"} sobre Rev {proposal.base.revision} (versión {proposal.base.version})
        → revisión nueva <strong>{proposal.target_revision}</strong> · DRAFT
      </p>
      {dirty && <p className="text-warning">Has cambiado entradas: la validación y la previsualización anteriores ya no valen.</p>}
      {proposal.stale_reason && <p className="text-danger">{proposal.stale_reason}</p>}
      {proposal.operations.length > 0 && <table className="w-full text-[12px]">
        <thead><tr className="text-left text-muted"><th>Campo</th><th>Antes</th><th>Después</th></tr></thead>
        <tbody>{proposal.operations.map((op) => <tr key={op.id}>
          <td className="pr-2">{op.label}</td>
          <td className="pr-2">{formatValue(op.before.value, op.before.unit)}</td>
          <td className="font-medium text-strong">{formatValue(op.after.value, op.after.unit)}</td>
        </tr>)}</tbody>
      </table>}
      {proposal.derived.total_height && <p className="text-[12px]">
        Altura total: {formatValue(proposal.derived.total_height.before, "mm")} → {formatValue(proposal.derived.total_height.after, "mm")}
      </p>}
      {proposal.effects.filter((e) => e.geometry_changed).length > 0 && <p className="text-[12px] text-muted">
        Piezas regeneradas: {proposal.effects.filter((e) => e.geometry_changed).map((e) => e.part).join(", ")}
      </p>}
      {general.map((issue, index) => <IssueLine key={index} issue={issue} />)}
      {proposal.issues.filter((i) => i.severity === "error" && (i.path || i.operation_id)).map((issue, index) =>
        <IssueLine key={`e${index}`} issue={issue} />)}
      {proposal.preview && !dirty && <p className="text-[12px] text-muted">
        IFC temporal {proposal.preview.ifc_sha256.slice(0, 12)} · {proposal.preview.validation.express_rules ? "esquema y reglas EXPRESS" : "esquema"} ·
        {" "}{proposal.preview.delta.changes.length} cambios · {Math.round((proposal.preview.timings_ms.total_ms ?? 0) / 100) / 10} s
      </p>}
      {proposal.status === "applied" && <p className="text-approved">
        Aplicada en {proposal.target_revision}. Nace DRAFT y no hereda aprobación: la revisión técnica sigue pendiente.
      </p>}
      {proposal.status === "applied" && proposal.applied_revision_id && <a className="text-[12px] text-accent-text underline"
        href={designReportUrl(proposal.applied_revision_id)} download>
        Descargar plano derivado (PDF anotado, documento aparte del original)
      </a>}
    </section>
  );
}

function HistoryList({ proposals, busy, onUndo }: { proposals: Proposal[]; busy: boolean; onUndo(p: Proposal): void }) {
  const applied = proposals.filter((p) => p.status === "applied");
  if (applied.length === 0) return null;
  return (
    <section className="space-y-2 border-t border-border pt-3" aria-label="Historial de órdenes">
      <h3 className="flex items-center gap-1.5 font-medium text-strong"><Icon icon={History} size={14} />Órdenes aplicadas</h3>
      {applied.map((p) => <div key={p.id} className="flex items-center justify-between gap-2 text-[12px]">
        <span>{p.kind === "reversion" ? "Deshacer" : "Cambio"} {p.base.revision} → {p.target_revision} · {p.actor}
          {p.reverted_by ? " · deshecha" : ""}</span>
        {!p.reverted_by && p.kind === "cambio_diseno" &&
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => onUndo(p)}>Deshacer</Button>}
      </div>)}
    </section>
  );
}
