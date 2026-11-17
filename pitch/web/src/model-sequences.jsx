import React from "react";
import { ArrowRight } from "lucide-react";
import { asset } from "./fx.jsx";
import { pitch } from "./pitch-data.js";
import "./model-sequences.css";

const bandCount = 6;

export function ModelExposure() {
  const { equipment, media } = pitch;
  const steel = asset(media.ifcB);
  return (
    <figure className="model-exposure">
      <div className="exposure-grid" aria-hidden="true" />
      <div className="exposure-plan">
        <img src={asset(media.plan)} alt={`Plano GA de ${equipment}, revisión B`} />
        <span>Plano GA</span>
      </div>
      <div className="exposure-volume">
        <img className="exposure-outline" src={asset(media.outline)} alt="" />
        <img className="exposure-steel" src={steel} alt={`Render de la geometría IFC de ${equipment}, revisión B`} />
        <div className="exposure-bands" aria-hidden="true">
          {Array.from({ length: bandCount }, (_, i) => (
            <img key={i} src={steel} alt="" style={{
              clipPath: `inset(${100 * i / bandCount}% 0 ${100 * (bandCount - i - 1) / bandCount}% 0)`,
              "--travel": i % 2 ? "5%" : "-5%",
              animationDelay: `${0.7 + i * 0.135}s`,
            }} />
          ))}
        </div>
        <div className="exposure-gate" aria-hidden="true" />
      </div>
      <figcaption>{equipment} / IFC REV. B</figcaption>
    </figure>
  );
}

export function RevisionExposure() {
  const { ifcA, ifcB, revisionDetail } = pitch.media;
  const showDetail = revisionDetail?.image === ifcB &&
    pitch.changes.some(({ field }) => field === revisionDetail?.field);
  return (
    <div className="revision-exposure" role="group" aria-label="Comparación de revisiones IFC">
      <div className="revision-registration" aria-hidden="true" />
      {[[ifcA, "A"], [ifcB, "B"]].map(([path, revision]) => (
        <figure className={`revision-plate revision-plate--${revision.toLowerCase()}`} key={revision}>
          <figcaption>REV. {revision}</figcaption>
          <div className="revision-negative">
            <div className="revision-frame">
              <img src={asset(path)} alt={`Modelo IFC de la revisión ${revision}`} />
              {revision === "B" && showDetail && (
                <div className="revision-focus" aria-hidden="true"
                  style={{ left: `${revisionDetail.x * 100}%`, top: `${revisionDetail.y * 100}%` }}>
                  <span>{revisionDetail.label}</span>
                </div>
              )}
            </div>
          </div>
        </figure>
      ))}
      <span className="revision-splice" aria-hidden="true"><ArrowRight size={19} strokeWidth={1.5} /></span>
    </div>
  );
}
