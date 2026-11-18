"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { IfcViewer } from "@/components/three";
import { Badge, Button, Panel, PanelHeader } from "@/components/ui/primitives";
import { apiRevisionById } from "@/lib/api/client";
import { apiEnabled, apiURL } from "@/lib/api/config";
import { formatPercent, formatValue } from "@/lib/format";
import { flattenRevision } from "@/lib/mock/fields";

const resourceLink = "text-sm font-medium text-accent-text underline underline-offset-2";

export function PipelineResult({ identity }: { identity: string }) {
  const revision = useQuery({
    queryKey: ["pipeline-result", identity], queryFn: () => apiRevisionById(identity), enabled: apiEnabled,
  });
  const [showModel, setShowModel] = useState(false);
  const record = revision.data;
  const root = `/revisions/${encodeURIComponent(identity)}`;
  const ifcUrl = apiURL(`${root}/ifc?draft=true`);
  const original = (documentId: string) => apiURL(`${root}/documents/${encodeURIComponent(documentId)}`);
  const documents = new Map(record?.documents.map(document => [document.id, document]));

  return (
    <div className="space-y-5">
      <Link href="/pipeline" className={resourceLink}>Volver al pipeline</Link>
      {!apiEnabled ? <p>Configura la conexión con la API para abrir este resultado.</p> : null}
      {apiEnabled && revision.isPending ? <p role="status">Cargando resultado…</p> : null}
      {revision.isError ? <Panel className="space-y-3 p-4">
        <p role="alert">{revision.error.message}</p>
        <Button onClick={() => void revision.refetch()}>Reintentar</Button>
      </Panel> : null}
      {record ? <>
        <header className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold text-strong">{record.equipment.tag.value} · Rev. {record.revision}</h1>
            <Badge tone="warning">IFC DRAFT</Badge>
            {record.dataset === "synthetic" ? <Badge tone="neutral">Datos sintéticos</Badge> : null}
          </div>
          <p className="text-sm text-muted">{record.project_id} · {record.equipment.id}</p>
        </header>
        <Panel>
          <PanelHeader title="IFC de la revisión"
            actions={<div className="flex flex-wrap items-center gap-3">
              <a href={ifcUrl} className={resourceLink}>Descargar IFC DRAFT</a>
              <Button size="sm" onClick={() => setShowModel(value => !value)}>{showModel ? "Ocultar modelo 3D" : "Ver modelo 3D"}</Button>
            </div>} />
          {showModel ? <div className="h-[420px] px-4 pb-4"><IfcViewer ifcUrl={ifcUrl} /></div> : null}
        </Panel>
        <Panel>
          <PanelHeader title="Documentos originales" description="La API verifica la huella del archivo al servirlo." />
          <ul className="space-y-2 px-5 pb-5">
            {record.documents.map(document => <li key={document.id}>
              <a className={resourceLink} href={original(document.id)} target="_blank" rel="noreferrer">{document.filename}</a>
            </li>)}
          </ul>
        </Panel>
        <Panel>
          <PanelHeader title="Campos extraídos" description="Valores y evidencias de esta revisión. Compruébalos antes de utilizar el modelo." />
          <div className="overflow-x-auto px-5 pb-5">
            <table className="w-full text-left text-sm">
              <thead><tr className="text-muted">
                {["Campo", "Valor", "Confianza", "Evidencia"].map(label => <th key={label} scope="col" className="py-2 pr-3">{label}</th>)}
              </tr></thead>
              <tbody>
                {flattenRevision(record).map(item => {
                  const document = documents.get(item.source.document_id);
                  const locator = [item.source.page ? `pág. ${item.source.page}` : "",
                    item.source.sheet, item.source.cell, item.source.locator].filter(Boolean).join(" · ");
                  return <tr key={item.path} className="border-t border-border">
                    <th scope="row" className="py-2 pr-3 font-medium">{item.label}</th>
                    <td className="py-2 pr-3">{formatValue(item.value, item.unit)}</td>
                    <td className="py-2 pr-3">{formatPercent(item.confidence)}</td>
                    <td className="py-2">
                      {document ? <a className={resourceLink} href={original(document.id)} target="_blank" rel="noreferrer">{document.filename}</a> : null}
                      {locator ? <span className="block text-xs text-muted">{locator}</span> : null}
                    </td>
                  </tr>;
                })}
              </tbody>
            </table>
          </div>
        </Panel>
      </> : null}
    </div>
  );
}
