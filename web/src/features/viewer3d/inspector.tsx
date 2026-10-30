"use client";
import type { PreparedProduct } from "./model-resource";
import { elementLabel } from "./semantic";
function tracedFields(product?: PreparedProduct) {
  const raw = product?.psets.TrazIA_Traceability?.FieldsJSON;
  if (typeof raw !== "string") return [];
  try {
    const fields: unknown = JSON.parse(raw);
    if (!fields || typeof fields !== "object" || Array.isArray(fields))
      return [];
    return Object.entries(fields).flatMap(([path, field]) => {
      if (
        !field ||
        typeof field !== "object" ||
        typeof field.confidence !== "number"
      )
        return [];
      const source =
        field.source && typeof field.source === "object" ? field.source : null;
      return [
        {
          path,
          confidence: field.confidence,
          source: source
            ? `${source.document_id ?? "—"}${source.page ? ` · pág. ${source.page}` : ""}${source.locator ? ` · ${source.locator}` : ""}`
            : "Sin fuente en el IFC",
        },
      ];
    });
  } catch {
    return [];
  }
}
export function IfcInspector({
  product,
  onClose,
}: {
  product?: PreparedProduct;
  onClose(): void;
}) {
  const traces = tracedFields(product);
  return (
    <aside
      aria-label="Inspector IFC"
      className="absolute right-3 top-40 z-[4] max-h-[65%] w-[min(290px,calc(100%-24px))] overflow-auto rounded-lg border border-border-strong bg-surface p-3 text-xs shadow-xl"
    >
      <div className="mb-3 flex items-center justify-between">
        <strong>Inspector IFC</strong>
        <button
          type="button"
          aria-label="Cerrar inspector IFC"
          onClick={onClose}
          className="px-2 py-1"
        >
          ×
        </button>
      </div>
      {product ? (
        <>
          <p className="font-medium">{elementLabel(product.semanticId)}</p>
          <p className="mt-1 text-muted">{product.ifcType}</p>
          <p className="mt-3 text-faint">GlobalId</p>
          <code className="break-all" data-testid="inspector-guid">
            {product.globalId}
          </code>
          <p className="mt-2 text-muted">Nombre: {product.name}</p>
          {product.psets.Pset_TrazIA?.Origen ? (
            <p
              className="mt-3 rounded-md border border-warning/30 bg-warning/10 p-2 text-warning"
              data-testid="derived-origin"
            >
              Detalle derivado · no leído del plano
              {product.psets.Pset_TrazIA.ClaseOrigen === "supuesto_visual"
                ? " · clase supuesta"
                : ""}
            </p>
          ) : null}
          {traces.length ? (
            <details className="mt-3 border-t border-border pt-2" open>
              <summary className="cursor-pointer font-medium">
                Fuente y confianza · IFC
              </summary>
              <ul className="mt-2 space-y-3">
                {traces.map((trace) => (
                  <li key={trace.path}>
                    <p className="flex justify-between gap-2">
                      <code className="break-all">{trace.path}</code>
                      <span>
                        {(trace.confidence * 100).toLocaleString("es-ES", {
                          maximumFractionDigits: 1,
                        })}{" "}
                        %
                      </span>
                    </p>
                    <p className="mt-1 break-all text-muted">{trace.source}</p>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
          {Object.entries(product.psets).map(([name, values]) => (
            <details key={name} className="mt-3 border-t border-border pt-2">
              <summary className="cursor-pointer break-all font-mono">
                {name}
              </summary>
              <dl className="mt-2 space-y-1">
                {Object.entries(values).map(([key, value]) => (
                  <div key={key} className="grid grid-cols-[1fr_1.2fr] gap-2">
                    <dt className="break-all text-muted">{key}</dt>
                    <dd className="break-all">
                      {value === null ? "—" : String(value)}
                    </dd>
                  </div>
                ))}
              </dl>
            </details>
          ))}
        </>
      ) : (
        <p className="text-muted">
          Selecciona un componente para consultar sus propiedades leídas del
          IFC.
        </p>
      )}
    </aside>
  );
}
