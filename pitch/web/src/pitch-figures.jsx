import React, { useId } from "react";
import { pitch } from "./pitch-data.js";
import { asset } from "./fx.jsx";
import "./pitch-figures.css";

// Una celda por revisión. Dos tramos de una trama SVG bastan incluso en lotes grandes.
function filledRows(count, columns) {
  const full = Math.floor(count / columns);
  const rest = count % columns;
  return `M0 0h${columns}v${full}H0z M0 ${full}h${rest}v1H0z`;
}

export function BatchMarks({ batch }) {
  const uid = useId();
  const { population, drafts, errors } = batch;
  if (![population, drafts, errors].every(v => Number.isSafeInteger(v) && v >= 0)
    || population === 0 || drafts + errors !== population) return null;
  const columns = Math.ceil(Math.sqrt(population * 3));
  const rows = Math.ceil(population / columns);
  return (
    <figure className="batch-marks" aria-label={`Lote de ${population} revisiones, ${drafts} IFC DRAFT y ${errors} errores`}>
      <svg viewBox={`0 0 ${columns} ${rows}`} aria-hidden="true">
        <defs>
          <pattern id={uid + "-draft"} width="1" height="1" patternUnits="userSpaceOnUse">
            <rect x=".1" y=".1" width=".76" height=".76" rx=".1" fill="#07578e" />
          </pattern>
          <pattern id={uid + "-error"} width="1" height="1" patternUnits="userSpaceOnUse">
            <path d="m.2 .2 .56 .56m0-.56L.2 .76" stroke="#465361" strokeWidth=".14" />
          </pattern>
        </defs>
        <path d={filledRows(population, columns) + " " + filledRows(drafts, columns)}
          fillRule="evenodd" fill={`url(#${uid}-error)`} />
        <path className="batch-filled" d={filledRows(drafts, columns)} fill={`url(#${uid}-draft)`} />
      </svg>
      <figcaption><span><i /> IFC DRAFT</span><span><b aria-hidden="true">×</b> Error</span></figcaption>
    </figure>
  );
}

export function ClosingPlate() {
  const { document, page, value, unit } = pitch.evidence;
  return (
    <figure className="closing-plate" aria-label={`Del plano ${document} al IFC de ${pitch.equipment}`}>
      <div className="closing-print">
        <img className="closing-sheet" src={asset(pitch.media.plan)} alt="" />
        <div className="closing-negative" aria-hidden="true">
          <img src={asset(pitch.media.outline)} alt="" />
        </div>
        <div className="closing-positive">
          <img src={asset(pitch.media.ifcB)} alt={`Geometría IFC de ${pitch.equipment}, revisión B`} />
        </div>
        <span className="closing-plate-id">{pitch.equipment} / REV. B</span>
      </div>
      <figcaption>
        <span>Longitud de virola<strong>{value.toLocaleString("es-ES", { useGrouping: "always" })} <small>{unit}</small></strong></span>
        <span>{document}<br />Pág. {page}</span>
      </figcaption>
    </figure>
  );
}
