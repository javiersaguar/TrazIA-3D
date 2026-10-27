"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Badge, Button, Code, Icon } from "@/components/ui/primitives";
import { ApiError, askCopilot, type CopilotAnswer } from "@/lib/api/client";
import { formatValue } from "@/lib/format";
import type { RevisionId } from "@/lib/mock/api";
import type { ReviewField } from "@/lib/mock/fields";

export function CopilotConversation({ revision, field }: { revision: RevisionId; field?: ReviewField }) {
  const [question, setQuestion] = useState("");
  const controller = useRef<AbortController | null>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const client = useQueryClient();
  const answer = useMutation({
    meta: { readOnly: true },
    mutationFn: ({ question, signal }: { question: string; signal: AbortSignal }) => askCopilot(revision, question, field?.path, signal),
    onError: error => {
      if (error instanceof ApiError && error.status === 409) {
        void client.invalidateQueries({ queryKey: ["revision", revision] });
        void client.invalidateQueries({ queryKey: ["review-fields", revision] });
      }
    },
  });
  useEffect(() => () => controller.current?.abort(), []);
  const submit = () => {
    if (!question.trim() || answer.isPending) return;
    controller.current?.abort();
    controller.current = new AbortController();
    answer.mutate({ question: question.trim(), signal: controller.current.signal });
  };
  const suggestions = ["Explica la fuente de este valor", "¿Qué debo comprobar antes de aceptarlo?",
    ...(revision === "B" ? ["¿Qué cambia respecto a la revisión A?"] : [])];

  return <div className="space-y-5 text-[13px]">
    {field ? <div>
      <p className="text-xs text-muted">{field.group} · rev {revision}</p>
      <h2 className="mt-1 text-[15px] font-semibold text-strong">{field.label}</h2>
      <p className="mt-1 text-[22px] font-semibold">{formatValue(field.correctedValue ?? field.value, field.unit)}</p>
      <Badge tone={field.status === "accepted" || field.status === "corrected" ? "live" : "warning"}>{field.status === "candidate" ? "Pendiente de revisión" : field.status}</Badge>
    </div> : <p className="text-muted">Pregunta sobre V-101, revisión {revision}, o selecciona un campo para centrar la consulta.</p>}
    <form onSubmit={event => { event.preventDefault(); submit(); }} className="space-y-2">
      <label htmlFor="copilot-question" className="block font-medium text-text">Tu pregunta</label>
      <textarea id="copilot-question" ref={input} value={question} onChange={event => setQuestion(event.target.value)}
        maxLength={2000} rows={3} placeholder="¿Qué dice el original y qué queda por revisar?"
        className="w-full resize-y rounded-[var(--radius-control)] border border-border bg-surface-sunken px-3 py-2 text-text outline-offset-2 placeholder:text-faint" />
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-faint">{question.length} / 2000</span>
        <div className="flex gap-2">
          {answer.isPending ? <Button size="sm" onClick={() => controller.current?.abort()}>Cancelar</Button> : null}
          <Button type="submit" size="sm" variant="primary" disabled={answer.isPending || !question.trim()}>
            <Icon icon={answer.isPending ? LoaderCircle : Send} className={answer.isPending ? "motion-safe:animate-spin" : undefined} size={14} />
            {answer.isPending ? "Consultando…" : "Preguntar"}
          </Button>
        </div>
      </div>
    </form>
    {!answer.data && !answer.isPending ? <div className="flex flex-wrap gap-1.5">
      {suggestions.map(text => <Button key={text} size="sm" variant="ghost" className="h-auto whitespace-normal text-left"
        onClick={() => { setQuestion(text); input.current?.focus(); }}>{text}</Button>)}
    </div> : null}
    {answer.isPending ? <p role="status" className="text-muted">Leyendo evidencia y consultando el modelo local…</p> : null}
    {answer.isError ? <p role="alert" className="rounded-lg border border-warning-border bg-warning-bg p-3 text-warning">
      {answer.error.name === "AbortError" ? "Consulta cancelada." : answer.error.message}
    </p> : null}
    {answer.data ? <AnswerView answer={answer.data} question={answer.variables?.question} /> : null}
  </div>;
}

function AnswerView({ answer, question }: { answer: CopilotAnswer; question?: string }) {
  const citations = answer.citations ?? [];
  const index = new Map(citations.map((citation, i) => [citation.id, i + 1]));
  return <div className="space-y-4" data-testid="copilot-answer">
    {question ? <p className="border-t border-border pt-3 text-xs text-muted">Consulta: {question}</p> : null}
    {answer.abstained ? <div className="rounded-lg border border-warning-border bg-warning-bg p-3 text-warning">
      <p className="font-medium">Sin respuesta respaldada</p>
      <p className="mt-1">{answer.reason ?? "No hay evidencia suficiente para responder."}</p>
    </div> : <>
      <section><h3 className="mb-2 text-xs font-medium text-faint">Respuesta</h3>
        {answer.statements.map((statement, i) => <p key={i} className="mb-2 leading-relaxed text-text">
          {statement.text} <span className="whitespace-nowrap text-accent-text">{statement.citations.map(id => `[${index.get(id) ?? "?"}]`).join(" ")}</span>
        </p>)}
      </section>
      {answer.proposals.length ? <section><h3 className="mb-2 text-xs font-medium text-faint">Comprobaciones propuestas</h3>
        <ul className="list-disc space-y-2 pl-4 text-muted">{answer.proposals.map((proposal, i) => <li key={i}>
          {proposal.text} <span className="text-accent-text">{proposal.citations.map(id => `[${index.get(id) ?? "?"}]`).join(" ")}</span>
        </li>)}</ul>
      </section> : null}
      <section><h3 className="mb-2 text-xs font-medium text-faint">Fuentes leídas</h3>
        <div className="space-y-2">{citations.map((citation, i) => <details key={citation.id} className="rounded-lg border border-border bg-surface-sunken px-3 py-2">
          <summary className="cursor-pointer leading-relaxed text-text">[{i + 1}] {citation.title}
            {citation.page ? ` · página ${citation.page}` : citation.sheet ? ` · ${citation.sheet}, ${citation.cell}` : ""}
          </summary>
          <div className="mt-2 space-y-2 text-xs leading-relaxed text-muted">
            <blockquote className="whitespace-pre-wrap border-l-2 border-accent pl-2">{citation.excerpt}</blockquote>
            {citation.original_verified ? <Badge tone="live">Original verificado por SHA-256</Badge> : null}
            {citation.sha256 ? <p>SHA-256 <Code>{citation.sha256.slice(0, 12)}…</Code></p> : null}
            {citation.bbox ? <p>Región: {citation.bbox.map(x => x.toFixed(3)).join(", ")}</p> : null}
          </div>
        </details>)}</div>
      </section>
    </>}
    <div className="border-t border-border pt-3 text-xs leading-relaxed text-faint">
      <p>{answer.model} · {answer.run.seconds.toFixed(2)} s · solo lectura</p>
      <p className="mt-1">Comprueba la evidencia antes de aceptar o corregir un dato.</p>
    </div>
  </div>;
}
