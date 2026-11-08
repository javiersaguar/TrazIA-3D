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
import { ApiError, cancelJob, getJob, subscribeJob } from "@/lib/api/client";
import { editableElements } from "./elements";
import { convertDisplay } from "./display-value";
import { PartsEditor } from "./parts-editor";
import { draftKey, useDraftField, useDraftCache } from "./draft-store";
import { formatValue } from "@/lib/format";
import { useEquipment } from "@/lib/queries";
import { useDemoUser } from "@/lib/session";
import { useSelection } from "@/stores/selection";

import {
  startDrawing, getDrawings, drawingDownloadUrl,
  STATUS_LABEL, applyProposal, designReportUrl, interpretRequest, createProposal, discardProposal, getCatalog, getProposal, listProposals,
  previewIfcUrl, replaceProposal, revertProposal, revisionIdentity, revisionIfcUrl, startPreview,
  type Datum, type Issue, type Proposal, type Target,
} from "./api";
import {
  clarifiedText, draftSignature, draftsFromOperations, elementStates, issuesFor,
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

function Workspace({ tag: initialTag }: { tag: string }) {
  const [savedTag, setTag] = useDraftField(draftKey("navigation","",""), "tag");
  const [savedProjectId, setProjectId] = useDraftField(draftKey("navigation","",""), "projectId");
  const qc = useQueryClient();
  const user = useDemoUser();
  const selectedId = useSelection((s) => s.selectedId);
  const select = useSelection((s) => s.setSelected);
  const equipment = useEquipment();
  const rows = equipment.data ?? [];
  const selectedEquipment = rows.find(row => row.tag === savedTag && (row.project_id ?? "DEMO-PLANT") === savedProjectId)
    ?? rows.find(row => row.tag === initialTag) ?? rows[0];
  const tag = selectedEquipment?.tag ?? savedTag ?? initialTag;
  const projectId = selectedEquipment?.project_id ?? savedProjectId;
  const equipmentKey = (row: (typeof rows)[number]) => `${row.project_id ?? "DEMO-PLANT"}:${row.tag}`;
  const labels: string[] = selectedEquipment?.revisions ?? ["B"];
  const [chosenLabel, setLabel] = useDraftField(draftKey(projectId,tag,"selection"), "label");
  const label = labels.includes(chosenLabel) ? chosenLabel : labels[labels.length - 1] ?? "B";
  const identity = useQuery({ queryKey: ["design-identity", projectId, tag, label], queryFn: () => revisionIdentity(tag, label, projectId) });
  const catalog = useQuery({
    queryKey: ["design-catalog", identity.data?.identity, identity.data?.etag],
    queryFn: () => getCatalog(identity.data!.identity), enabled: !!identity.data,
  });
  const history = useQuery({
    queryKey: ["design-history", identity.data?.identity, identity.data?.etag],
    queryFn: () => listProposals(identity.data!.identity), enabled: !!identity.data,
  });

  const cacheKey = draftKey(projectId, tag, label);
  const [, setPendingJob] = useDraftField(cacheKey, "pendingJob");
  const [partForm, setPartForm] = useDraftField(cacheKey, "partForm");

  // El grupo sigue a la selección 3D salvo que la persona elija otro con esa misma selección.
  const [choice, setChoice] = useDraftField(cacheKey, "choice");
  const chosenGroup = choice && choice.selection === selectedId ? choice.group : null;
  const [drafts, setDrafts] = useDraftField(cacheKey, "drafts");
  const [partChanges,setPartChanges] = useDraftField(cacheKey, "partChanges");
  const [detailLevel,setDetailLevel] = useDraftField(cacheKey, "detailLevel");
  const [drawing,setDrawing] = useDraftField(cacheKey, "drawing");
  const [activeJob,setActiveJob] = useState<string|null>(null);
  const [reason, setReason] = useDraftField(cacheKey, "reason");
  const [actorInput, setActor] = useDraftField(cacheKey, "actor");
  const actor = actorInput ?? user ?? "";
  const name = actor.trim();
  const [proposal, setProposal] = useDraftField(cacheKey, "proposal");
  const [signature, setSignature] = useDraftField(cacheKey, "signature");
  const [steps, setSteps] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [side, setSide] = useDraftField(cacheKey, "side");
  const applyKey = useRef<{ id: string; key: string } | null>(null);
  const stopStream = useRef<(() => void) | null>(null);
  const [request, setRequest] = useDraftField(cacheKey, "request");
  const [useModel, setUseModel] = useDraftField(cacheKey, "useModel");
  const [intent, setIntent] = useDraftField(cacheKey, "intent");

  useEffect(() => () => stopStream.current?.(), []);

  useEffect(() => {
    const id = useDraftCache.getState().entries[cacheKey]?.proposal?.id;
    if (!id) return;
    let live = true;
    void getProposal(id).then(value => {
      if (live) useDraftCache.getState().update(cacheKey, "proposal", value);
    }).catch(error => {
      if (live && error instanceof ApiError && error.status===404) useDraftCache.getState().update(cacheKey,"proposal",null);
    });
    return () => { live = false; };
  }, [cacheKey]);

  useEffect(() => {
    const saved = useDraftCache.getState().entries[cacheKey]?.pendingJob;
    if (!saved) return;
    let live = true;
    let stop: (()=>void) | undefined;
    const finish = async (status: string) => {
      try {
        if (saved.kind === "preview") {
          const id = useDraftCache.getState().entries[cacheKey]?.proposal?.id;
          if (id) {
            const value = await getProposal(id);
            if (live) useDraftCache.getState().update(cacheKey,"proposal",value);
          }
        } else if (status === "done") {
          const value = await getDrawings(saved.revisionId);
          if (live) useDraftCache.getState().update(cacheKey,"drawing",value);
        }
      } finally {
        if (live) { useDraftCache.getState().update(cacheKey,"pendingJob",null); setBusy(null); setActiveJob(null); }
      }
    };
    void getJob(saved.id).then(job => {
      if (!live) return;
      if (["done","error","cancelled","timeout"].includes(job.status)) return finish(job.status);
      setActiveJob(saved.id); setBusy("seguir");
      stop = subscribeJob(saved.id,event=>setSteps(old=>[...old,event.detail]),status=>{void finish(status);},()=>{});
    }).catch(() => { if (live) {setBusy(null);setActiveJob(null);} });
    return () => {live=false;stop?.();};
  },[cacheKey]);

  // Cambiar de base empieza de cero: una propuesta pertenece a una revisión concreta.
  function changeBase(next: string, carried: Proposal | null = null) {
    setLabel(next); setSteps([]);
    if (carried) {
      const key = draftKey(projectId, tag, next);
      useDraftCache.getState().update(key, "proposal", carried);
    }
  }

  const targets = useMemo(() => catalog.data?.targets ?? [], [catalog.data]);
  const elements = useMemo(() => editableElements(targets, catalog.data?.kind ?? ""), [targets, catalog.data?.kind]);
  const group = (chosenGroup && elements.some(e => e.id === chosenGroup) ? chosenGroup : null)
    ?? elements.find(e => e.semantic && e.semantic === selectedId?.replace(/^detail:/, "").split("/")[0])?.id ?? "equipo";
  const currentElement = elements.find(e => e.id === group);
  const visible = targets.filter(t => currentElement?.targets.includes(t.target));
  const chooseElement = (id: string) => {
    const next = elements.find(e => e.id === id);
    select(next?.semantic ?? null); setChoice({group:id, selection:next?.semantic ?? null});
  };
  const operations = toOperations(drafts, targets);
  const currentSignature = draftSignature(operations, reason) + JSON.stringify([partChanges,detailLevel,name,intent?.clarifications,intent?.rejected]);
  const dirty = !!proposal && proposal.kind === "cambio_diseno" && signature !== currentSignature;
  const editable = !proposal || (proposal.kind === "cambio_diseno" && EDITABLE.has(proposal.status));
  const preview = proposal?.preview && !dirty ? proposal.preview : null;
  const issues = useMemo(() => proposal?.issues ?? [], [proposal]);
  const states = useMemo(() => elementStates(preview, dirty ? [] : issues), [preview, issues, dirty]);
  const base = proposal?.base ?? (identity.data && catalog.data
    ? { revision_id: identity.data.identity, version: catalog.data.version, revision: catalog.data.revision } : null);
  const ifcUrl = preview && side === "despues" ? previewIfcUrl(preview)
    : base ? revisionIfcUrl(base.revision_id, base.version) : "";
  const canValidate = editable && name.length >= 2 && reason.trim().length >= 3 && (operations.length > 0 || partChanges.length > 0) && !intent?.clarifications.length && !intent?.rejected.length && !busy;

  function setDraft(target: Target, patch: Partial<Drafts[string]>) {
    setDrafts((old) => ({ ...old, [target.target]: {
      value: old[target.target]?.value ?? String(target.current.value), unit: old[target.target]?.unit ?? target.unit,
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
      operations, part_changes: partChanges, detail_level: detailLevel, reason: reason.trim(), actor: name, origin: fromChat ? "chat" as const : "formulario" as const,
      request_text: fromChat ? intent?.request_text ?? null : null,
      clarifications: fromChat ? intent?.clarifications ?? [] : [],
    };
    const result = proposal && proposal.kind === "cambio_diseno" && EDITABLE.has(proposal.status)
      ? await replaceProposal(proposal.id, body)
      : await createProposal(identity.data.identity, identity.data.etag, body);
    setProposal(result); setSignature(currentSignature); setSteps([]);
    applyKey.current = null;
  });

  const runPreview = () => run("previsualizar", async () => {
    if (!proposal) return;
    const job = await startPreview(proposal.id);
    setSteps([]);
    setActiveJob(job.job_id); setPendingJob({id:job.job_id,kind:"preview",revisionId:proposal.base.revision_id});
    setBusy("previsualizar");
    await new Promise<void>((resolve,reject) => {
      stopStream.current?.();
      stopStream.current = subscribeJob(job.job_id,
        (event) => { if (event.stage !== "job") setSteps((old) => [...old, event.detail]); },
        async (status) => {
          if (status !== "done") {
            const detail = (await getJob(job.job_id).catch(() => null))?.error;
            toast.error(detail ?? `Previsualización ${status}`, { description: "La revisión base no ha cambiado." });
          }
          try { setProposal(await getProposal(proposal.id)); resolve(); }
          catch (failure) { reject(failure); }
          finally { setActiveJob(null); setPendingJob(null); }
        },
        () => { toast.error("Seguimiento interrumpido; intentando reconectar. Puedes cancelar el trabajo."); });
    });
    setSide("despues");
  });

  const confirm = () => run("confirmar", async () => {
    if (!proposal?.preview) return;
    // Reintentar la misma confirmación usa la misma clave: nunca dos revisiones.
    if (applyKey.current?.id !== proposal.id + proposal.preview.ifc_sha256)
      applyKey.current = { id: proposal.id + proposal.preview.ifc_sha256, key: crypto.randomUUID() };
    const result = await applyProposal(proposal, name, applyKey.current.key);
    setProposal(result.proposal); setDrawing(null);
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
    setPartChanges(result.part_changes ?? []); setDetailLevel(result.detail_level ?? undefined);
    if (result.part_changes?.length && !reason.trim()) setReason(`Petición: «${text.trim().slice(0, 200)}»`);
    if (!result.operations.length) setDrafts({});
    if (result.operations.length) {
      const filled = draftsFromOperations(result.operations, targets);
      setDrafts(filled);
      const first = targets.find((t) => t.target in filled);
      if (first) setChoice({ group: first.group, selection: selectedId });
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
    const current = await revisionIdentity(tag, target, projectId);
    const reversion = await revertProposal(applied.id, current.etag, name || applied.actor,
      `Deshacer la orden ${applied.id.slice(0, 8)} sobre ${applied.base.revision}`);
    // La propuesta de deshacer pertenece a la revisión derivada.
    changeBase(target, reversion);
  });

  const makeDrawing = () => run("plano", async () => {
    const target=proposal?.status==="applied"?proposal.target_revision:label;
    const current=await revisionIdentity(tag,target,projectId);
    const job=await startDrawing(current.identity,current.etag);
    setActiveJob(job.job_id);setPendingJob({id:job.job_id,kind:"drawing",revisionId:current.identity});setSteps([]);
    try {
      await new Promise<void>((resolve,reject)=>{
        stopStream.current?.();
        stopStream.current=subscribeJob(job.job_id,event=>setSteps(old=>[...old,event.detail]),status=>{
          if(status==="done")resolve();else reject(new Error(`Generación del plano: ${status}. La revisión no se ha modificado.`));
        },()=>toast.error("Seguimiento interrumpido; intentando reconectar."));
      });
      setDrawing(await getDrawings(current.identity));
      toast.success("Plano GA nuevo generado desde el IFC");
    } finally {setActiveJob(null);setPendingJob(null);}
  });

  if (identity.isLoading || catalog.isLoading) return <Skeleton className="h-[620px]" />;
  if (identity.error || catalog.error || !catalog.data)
    return <Panel><EmptyState icon={CircleAlert} title="No se pudo cargar el catálogo de operaciones">
      {(identity.error ?? catalog.error)?.message}
    </EmptyState></Panel>;

  return (
    <div className="space-y-5" data-testid="design-edit">
      <Panel><div className="space-y-3 p-4">
          <div className="grid gap-3 @xl:grid-cols-2 @4xl:grid-cols-4">
            <label className="space-y-1"><span className="text-muted">Proyecto</span>
              <select aria-label="Proyecto" className={control} value={projectId} disabled={!!busy} onChange={e=>{
                const next=rows.find(row=>(row.project_id??"DEMO-PLANT")===e.target.value);
                if(next){setProjectId(e.target.value);setTag(next.tag);select(null);}
              }}>{[...new Set(rows.map(row=>row.project_id??"DEMO-PLANT"))].map(id=><option key={id}>{id}</option>)}</select>
            </label>
            <label className="space-y-1"><span className="text-muted">Equipo</span>
              <select aria-label="Equipo" className={control} value={`${projectId}:${tag}`} disabled={!!busy} onChange={e => {
                const next = rows.find(row => equipmentKey(row) === e.target.value);
                if (next) { setTag(next.tag); setProjectId(next.project_id ?? "DEMO-PLANT"); select(null); }
              }}>
                {rows.filter(row=>(row.project_id??"DEMO-PLANT")===projectId).map(row => <option key={equipmentKey(row)} value={equipmentKey(row)}>{row.tag} · {row.kind} · {row.project_id ?? "DEMO-PLANT"}</option>)}
              </select>
            </label>
            <label className="space-y-1"><span className="text-muted">Revisión base</span>
              <select aria-label="Revisión base" className={control} value={label} onChange={(e) => changeBase(e.target.value)} disabled={!!busy}>
                {labels.map((rev) => <option key={rev} value={rev}>Rev {rev}</option>)}
              </select>
            </label>
            <label className="space-y-1"><span className="text-muted">Elemento</span>
              <select aria-label="Elemento" className={control} value={group} onChange={(e) => chooseElement(e.target.value)}>
                {elements.map(g => <option key={g.id} value={g.id}>{g.label}</option>)}
              </select>
            </label>
          </div>
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
          <span>Recorre las piezas del equipo; sus dimensiones comunes se comparten con el conjunto.</span>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="secondary" disabled={!!busy || elements.findIndex(e => e.id===group)<=0}
              onClick={() => chooseElement(elements[elements.findIndex(e => e.id===group)-1]!.id)}>Pieza anterior</Button>
            <span>{elements.findIndex(e => e.id===group)+1} / {elements.length}</span>
            <Button size="sm" variant="secondary" disabled={!!busy || elements.findIndex(e => e.id===group)>=elements.length-1}
              onClick={() => chooseElement(elements[elements.findIndex(e => e.id===group)+1]!.id)}>Pieza siguiente</Button>
          </div>
        </div>
      </div></Panel>

      <FullscreenFrame
        title="Antes y después en el IFC"
        description={preview
          ? "Después: IFC temporal generado y validado con estos parámetros. No es una revisión hasta confirmar."
          : "Revisión base. Valida y previsualiza para ver el IFC de la propuesta."}
        height="h-[min(56vh,560px)] min-h-[340px]"
        actions={<>
          <span className="text-[12px] text-warning">{catalog.data?.dataset === "real" ? "Datos de la revisión" : "Datos sintéticos"} · {tag} · DRAFT</span>
          <Segmented<"antes" | "despues"> label="Revisión mostrada" value={preview ? side : "antes"} onChange={setSide}
            options={[{ value: "antes", label: `Antes · ${base?.revision ?? label}` },
              { value: "despues", label: preview ? `Después · ${preview.target_revision}` : "Después" }]} />
        </>}
      >
        {ifcUrl ? <IfcViewer ifcUrl={ifcUrl} selectedId={selectedId ?? undefined} onSelect={(id) => select(id)}
          elementStates={states} /> : <Skeleton className="h-full" />}
      </FullscreenFrame>

      <Panel className="flex min-h-0 flex-col">
        <PanelHeader title="Proponer cambios de diseño"
          description="Cambia el diseño, no la lectura. Se crea una revisión DRAFT nueva; el plano original no se toca."
          actions={proposal ? <Badge tone={tone(proposal.status)}>{STATUS_LABEL[proposal.status]}</Badge> : null} />
        <div className="space-y-4 px-4 pb-5 text-[13px] sm:px-5" data-testid="design-form">

          {!catalog.data.geometry_supported && <p className="rounded border border-warning-border bg-warning-bg p-2 text-warning">
            Esta familia ({catalog.data.kind}, LOD {catalog.data.lod}) solo admite atributos: su geometría aún no tiene cobertura verificada.
          </p>}
          <p className="text-muted">{catalog.data.datum.elevation} Azimut: {catalog.data.datum.azimuth}</p>

          {editable && <details className="space-y-2 rounded-[var(--radius-card)] border border-border p-3" open={!!request || !!intent}><summary className="cursor-pointer font-medium text-strong">Describir el cambio con el Copiloto</summary>
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
              <Button size="sm" variant="ghost" onClick={() => { setIntent(null); setDrafts({}); setPartChanges([]); }}>Descartar borrador del chat</Button>
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
          </details>}

          <fieldset disabled={!editable || !!busy} className="grid gap-3 @xl:grid-cols-2 @4xl:grid-cols-3" data-testid="design-fields">
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
                    <input className={control} value={draft?.value ?? String(target.current.value)}
                      inputMode={target.text ? "text" : "decimal"} aria-label={`Nuevo valor de ${target.label}`}
                      aria-invalid={own.some((i) => i.severity === "error")}
                      onChange={(e) => setDraft(target, { value: e.target.value })} />
                    {units.length > 0 && <select className={`${control} w-24`} aria-label={`Unidad de ${target.label}`}
                      value={draft?.unit ?? target.unit} onChange={(e) => setDraft(target, { unit: e.target.value, value: convertDisplay(draft?.value ?? String(target.current.value), draft?.unit ?? target.unit, e.target.value) })}>
                      {units.map((u) => <option key={u} value={u}>{u === "deg" ? "°" : u}</option>)}
                    </select>}
                  </div>
                  {target.datums.length > 1 && <select className={control} aria-label={`Referencia de ${target.label}`}
                    value={draft?.datum ?? target.datums[0]} onChange={(e) => {
                      const next = e.target.value as Datum, previous = draft?.datum ?? target.datums[0];
                      const mmText = convertDisplay(draft?.value ?? String(target.current.value), draft?.unit ?? target.unit, "mm");
                      const mm = mmText ? Number(mmText) : NaN;
                      const shift = Number(convertDisplay(drafts.skirt_height?.value ?? String(catalog.data?.datum.shell_bottom_mm ?? 0), drafts.skirt_height?.unit ?? "mm", "mm"));
                      const value = Number.isFinite(mm) ? String(mm + (previous === "tangente_inferior" ? shift : -shift)) : "";
                      setDraft(target, { datum: next, value: convertDisplay(value, "mm", draft?.unit ?? target.unit) });
                    }}>
                    {target.datums.map((d) => <option key={d} value={d}>Elevación {DATUM_LABEL[d]}</option>)}
                  </select>}
                  <details className="text-[12px] text-muted"><summary className="cursor-pointer">Condiciones del campo</summary><p>{target.rule}</p></details>
                  {draft && <Button size="sm" variant="ghost" onClick={() => setDrafts(old => {
                    const next={...old}; delete next[target.target]; return next;
                  })}>Restablecer {target.label}</Button>}
                  {operation?.resolution && !dirty && <p className="text-[12px] text-sky">{operation.resolution}</p>}
                  {own.map((issue, index) => <IssueLine key={index} issue={issue} />)}
                </div>
              );
            })}
          </fieldset>
          <fieldset disabled={!editable || !!busy} className="grid gap-3 @xl:grid-cols-[2fr_1fr]">
            <label className="block space-y-1"><span className="text-muted">Motivo del cambio (obligatorio)</span>
              <textarea className={control} rows={2} maxLength={1000} value={reason} onChange={(e) => setReason(e.target.value)}
                placeholder="Por ejemplo: aumentar capacidad según la hoja de proceso" />
            </label>
            <label className="block space-y-1"><span className="text-muted">Persona que propone</span>
              <input className={control} value={actor} maxLength={100} onChange={(e) => setActor(e.target.value)} />
            </label>
          </fieldset>

          <details className="rounded-[var(--radius-card)] border border-border p-3" data-testid="parts-section">
            <summary className="cursor-pointer font-medium text-strong">Añadir o eliminar piezas {partChanges.length ? `· ${partChanges.length} en el lote` : ""}</summary>
          <PartsEditor key={identity.data?.identity} catalog={catalog.data} form={partForm} onFormChange={setPartForm} changes={partChanges} onChange={setPartChanges} detailLevel={detailLevel} onDetailLevel={setDetailLevel} disabled={!editable || !!busy} />
          </details>
          <p className="text-[12px] text-muted">
            ¿El plano dice otra cosa? Eso es <Link className="text-accent-text underline" href="/modelo?vista=revision">corregir la lectura</Link>,
            no cambiar el diseño: las órdenes de diseño no entran en el aprendizaje de extracción.
          </p>

          {proposal && <Summary proposal={proposal} dirty={dirty} />}
          {steps.length > 0 && <ol className="space-y-0.5 text-[12px] text-muted" aria-live="polite">
            {steps.map((s, i) => <li key={i}>{s}</li>)}
          </ol>}

          <p role="status" className="text-xs text-muted">Borrador conservado en esta sesión del navegador, por equipo y revisión. No se aplica hasta confirmar.</p>
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
              <Button variant="secondary" onClick={() => changeBase(proposal.target_revision)}>
                Trabajar sobre {proposal.target_revision}
              </Button>
              {!proposal.reverted_by && proposal.kind === "cambio_diseno" &&
                <Button variant="ghost" disabled={!!busy} onClick={() => undo(proposal)}><Icon icon={Undo2} size={14} />Deshacer</Button>}
            </>}
            {proposal?.status === "stale" && <Button variant="secondary" onClick={() => { setProposal(null); void identity.refetch(); }}>
              <Icon icon={RotateCcw} size={14} />Preparar sobre la versión vigente
            </Button>}
          </div>

          {activeJob && <Button size="sm" variant="ghost" onClick={()=>void cancelJob(activeJob)}>Cancelar trabajo en curso</Button>}
          <details aria-label="Plano GA nuevo" className="space-y-2 border-t border-border pt-3">
            <summary className="cursor-pointer font-semibold">Generar plano nuevo desde IFC</summary>
            <p className="text-xs text-muted">Alzado, perfil y planta en A3, cotas exteriores y cajetín. DRAFT con escala física; proyección sin ocultación. Se usa la revisión persistida {proposal?.status==="applied"?proposal.target_revision:label}, no cambios sin confirmar.</p>
            <Button disabled={!!busy} onClick={makeDrawing}>{busy==="plano"?"Generando plano…":"Generar GA nuevo"}</Button>
            {drawing && <div className="flex flex-wrap gap-3 text-sm">{Object.entries(drawing.files).map(([key,file])=><a key={key} className="text-accent-text underline" href={drawingDownloadUrl(file.url)} download>Descargar {key.toUpperCase()}</a>)}</div>}
          </details>
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
