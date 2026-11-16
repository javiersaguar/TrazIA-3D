import React, { useRef, useState } from "react";
import { m, useReducedMotion } from "motion/react";
import {
  ArrowDownToLine, ArrowRight, Box, Check, ChevronRight, Database, FileSpreadsheet,
  FileText, GitCompareArrows, Layers, Play, ScanLine, Workflow,
} from "lucide-react";
import { pitch } from "./pitch-data.js";
import {
  asset, ease, easeInOut, useFx, Barrido, CajaTrazo, Contador, DeltaMarker, Esquinas, PuntoRecorrido,
} from "./fx.jsx";

const number = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0, useGrouping: "always" });
const score = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
const decimal = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const formatNumber = (value) => number.format(value);
const formatScore = (value) => score.format(value);
const formatSpeedup = (value) => `${decimal.format(value)}×`;
const formatDelta = (value) => `+${number.format(value)} mm`;

// Marco azul del recorte de 411 × 147. Se mantiene alineado al cambiar el ancho del recorte.
const evidenceBox = { left: "4.87%", top: "40.14%", width: "43.31%", height: "19.73%" };
const sources = {
  cost: "Fuente: enunciado GA2MODEL, pág. 5",
  bench: "Evaluación previa al evento. El conjunto del reto se evalúa por separado.",
  scale: pitch.batch.detail,
};

export function SourceNote({ id, pinned = false }) {
  const text = sources[id];
  if (!text) return null;
  return <p className={`source-note ${pinned ? "fx-source-note" : ""}`}>{text}</p>;
}

export function Reveal({
  children, delay = 0, className, from = "translateY(18px)", to = "translateY(0px)", inline = false, ...attributes
}) {
  const reduced = useReducedMotion();
  const Element = inline ? m.span : m.div;
  return (
    <Element
      {...attributes}
      className={className}
      initial={reduced ? false : { opacity: 0, transform: from }}
      animate={{ opacity: 1, transform: to }}
      transition={{ duration: reduced ? 0 : 0.57, ease, delay: reduced ? 0 : delay }}
    >
      {children}
    </Element>
  );
}

function Heading({ scene, children }) {
  return (
    <div className="story">
      <h1>
        <span className="title-mask"><Reveal inline from="translateY(72%)" to="translateY(0%)">{scene.title}</Reveal></span>
        {scene.accent && <span className="title-mask accent"><Reveal inline from="translateY(72%)" to="translateY(0%)" delay={0.09}>{scene.accent}</Reveal></span>}
      </h1>
      <Reveal delay={0.19}>
        <p className="subtitle">{scene.subtitle}</p>
        {children}
      </Reveal>
    </div>
  );
}

function Plan({ className = "" }) {
  return <img className={`plan ${className}`} src={asset(pitch.media.plan)} alt={`Plano GA de ${pitch.equipment}, revisión B`} />;
}

function Hero({ scene }) {
  const fx = useFx();
  return (
    <div className="scene-layout hero-layout">
      <Heading scene={scene} />
      <m.div className="hero-art"
        initial={fx ? { transform: "scale(1)" } : false}
        animate={fx ? { transform: "scale(1.04)" } : undefined}
        transition={{ duration: 20, ease: "linear" }}
      >
        <div className="hero-cross" aria-hidden="true" />
        <Reveal className="hero-paper" from="translate(34px, 44px) rotate(-6deg)" to="translate(0px, 0px) rotate(0deg)" delay={0.16}>
          <div className="hero-plan-wrap fx-image">
            <Plan />
            {fx && <Barrido delay={9} strength={0.23} repeat={1} repeatDelay={8.2} />}
          </div>
        </Reveal>
        <Reveal className="hero-object" from="translate(28px, 28px) scale(.94)" to="translate(0px, 0px) scale(1)" delay={0.34}>
          <img src={asset(pitch.media.ifcB)} alt={`Recipiente ${pitch.equipment} extraído de su IFC`} />
        </Reveal>
        <span className="art-label">{pitch.equipment} / REV. A → B{fx && <Esquinas delay={1.1} />}</span>
      </m.div>
    </div>
  );
}

function Cost({ scene }) {
  const fx = useFx();
  const range = pitch.baseline.hours.match(/^([\d.]+)([^\d.]+)([\d.]+)$/);
  return (
    <div className="cost-layout">
      <Heading scene={scene} />
      <Reveal className="cost-number" delay={0.21} from="translateY(21px) scale(.97)" to="translateY(0px) scale(1)">
        {fx && range ? (
          <span className="fx-cost-range">
            <Contador value={Number(range[1].replaceAll(".", ""))} format={formatNumber} delay={0.24} duration={0.86} />
            {range[2]}
            <Contador value={Number(range[3].replaceAll(".", ""))} format={formatNumber} delay={0.24} duration={0.86} />
            <Esquinas delay={1.1} />
          </span>
        ) : pitch.baseline.hours}<span className="cost-unit"> h</span>
      </Reveal>
      <div className="cost-factors">
        {pitch.baseline.factors.map(([value, label], index) => (
          <Reveal className="factor" delay={0.34 + 0.075 * index} key={label}>
            <strong>{value}</strong><span>{label}</span>
          </Reveal>
        ))}
      </div>
      {!fx && <SourceNote id="cost" />}
    </div>
  );
}

const steps = [
  [FileText, "Lectura", "Texto y tablas"],
  [ScanLine, "OCR", "Entrada raster"],
  [Layers, "Fusión", "Evidencia por campo"],
  [Check, "Revisión", "Control humano"],
];

function Input({ scene }) {
  const fx = useFx();
  const process = useRef(null);
  const travelDelay = 1.05;
  const travelInterval = 0.34;
  return (
    <div className="scene-layout input-layout">
      <Heading scene={scene}>
        <a className="text-link" href={asset(pitch.media.planPdf)} target="_blank" rel="noreferrer">
          Abrir plano de ejemplo <ArrowDownToLine size={16} />
        </a>
      </Heading>
      <div className="input-desk">
        <Reveal className="file-sheet" from="translate(-26px, 42px) rotate(-6deg)" to="translate(0px, 0px) rotate(0deg)" delay={0.11}>
          <div className="file-heading"><FileText size={18} /> Plano GA <span>PDF</span></div>
          <div className="fx-image">
            <Plan />
            {fx && <Barrido delay={0.24} />}
          </div>
        </Reveal>
        <Reveal className="file-sheet data-sheet" from="translate(34px, 28px) rotate(5deg)" to="translate(0px, 0px) rotate(0deg)" delay={0.24}>
          <div className="file-heading"><FileSpreadsheet size={18} /> Hoja de datos <span>XLSX</span></div>
          <div className="spreadsheet" aria-hidden="true">{Array.from({ length: 21 }, (_, i) => <i key={i} />)}</div>
        </Reveal>
        <Reveal className="package-label" delay={0.39}>
          <Box size={17} /> {pitch.equipment} <span>REV. B</span>
          {fx && <Esquinas delay={travelDelay + travelInterval * (steps.length - 1)} />}
        </Reveal>
      </div>
      <div className="process-strip" ref={process} aria-label="Etapas de entrada">
        {steps.map(([Icon, title, detail], index) => (
          <Reveal key={title} className="process-step" data-fx-step delay={0.22 + index * 0.08}>
            <Icon size={21} />
            <div><strong>{title}</strong><span>{detail}</span></div>
          </Reveal>
        ))}
        {fx && <PuntoRecorrido container={process} delay={travelDelay} interval={travelInterval} stories />}
      </div>
    </div>
  );
}

function Evidence({ scene }) {
  const fx = useFx();
  const field = pitch.evidence;
  const snippet = {
    path: field.path, value: field.value, unit: field.unit,
    source: field.document, page: field.page, confidence: field.confidence,
  };
  const json = JSON.stringify(snippet, null, 2);
  return (
    <div className="scene-layout trace-layout">
      <Heading scene={scene} />
      <div className="trace-board">
        <Reveal className="trace-source" delay={0.15}>
          <header><FileText size={16} /> {field.document} <span>PÁG. {field.page}</span></header>
          <div className="fx-image">
            <img src={asset(pitch.media.evidence)} alt="Recorte del plano con el valor de longitud resaltado" />
            {fx && <CajaTrazo delay={0.22} style={evidenceBox} />}
          </div>
        </Reveal>
        <div className={`trace-connector ${fx ? "fx-trace-connector" : ""}`} aria-hidden="true">
          <span /><ChevronRight size={25} />
        </div>
        <Reveal className="trace-result" delay={0.36} from="translateX(22px)" to="translateX(0px)">
          <div className="field-value">
            <span>LONGITUD DE VIROLA</span>
            <strong>{fx
              ? <Contador value={field.value} format={formatNumber} delay={1.37} duration={0.58} />
              : number.format(field.value)} <small>{field.unit}</small></strong>
          </div>
          <pre>{fx ? json.split("\n").map((line, index) => (
            <React.Fragment key={index}>
              {index > 0 && "\n"}
              <m.span className="fx-json-line"
                initial={{ clipPath: "inset(0% 100% 0% 0%)" }}
                animate={{ clipPath: "inset(0% 0% 0% 0%)" }}
                transition={{ duration: 0.14, delay: 1.97 + 0.04 * index, ease }}
              >{line}</m.span>
            </React.Fragment>
          )) : json}</pre>
        </Reveal>
      </div>
    </div>
  );
}

function Bench({ scene }) {
  const fx = useFx();
  const study = pitch.study;
  const selected = study.variants.find(({ key }) => key === study.selected);
  const reduced = useReducedMotion();
  const selectedDelay = 0.12 + 0.07 * study.variants.findIndex(({ key }) => key === study.selected);
  const barDuration = 0.75;
  const spotlight = 0.12 + 0.07 * (study.variants.length - 1) + barDuration;
  return (
    <div className="scene-layout bench-layout">
      <Heading scene={scene}>
        {selected && <div className="bench-highlight">
          <strong>{fx
            ? <Contador value={selected.score} format={formatScore} delay={selectedDelay} duration={barDuration} />
            : score.format(selected.score)}</strong>
          <div><span>{selected.label}</span><small>{study.interval}</small></div>
        </div>}
      </Heading>
      <div className="bench-visual">
        <div className="data-caption">{study.label}</div>
        <div className="bench-scale" aria-hidden="true"><span>0</span><span>0,5</span><span>1</span></div>
        {study.variants.map(({ key, label, score: value }, index) => (
          <Reveal key={key} delay={0.09 + index * 0.07}>
            <m.div className={`bench-row ${key === study.selected ? "is-selected" : ""}`}
              initial={false}
              animate={fx && key !== study.selected ? { opacity: [1, 0.35, 0.35, 1] } : undefined}
              transition={{ duration: 0.96, delay: spotlight, times: [0, 0.24, 0.68, 1], ease: easeInOut }}
            >
            <span className="strategy-id">{key}</span>
            <span>{label}</span>
            <div className="bench-track">
              <m.div
                initial={reduced ? false : { transform: "scaleX(.025)" }}
                animate={{ transform: `scaleX(${value})` }}
                transition={{ duration: reduced ? 0 : barDuration, delay: reduced ? 0 : 0.12 + index * 0.07, ease }}
              />
            </div>
            <strong>{score.format(value)}</strong>
            {fx && key === study.selected && <Esquinas delay={spotlight} spring />}
            </m.div>
          </Reveal>
        ))}
        {!fx && <SourceNote id="bench" />}
      </div>
    </div>
  );
}

function MediaSlot({ path, children }) {
  const [video, setVideo] = useState(false);
  if (video) {
    return <div className="media-slot">
      <video src={asset(path)} controls autoPlay playsInline className="demo-video" aria-label="Grabación de la demo" />
      <button className="media-switch" type="button" onClick={() => setVideo(false)}>Volver a la escena</button>
    </div>;
  }
  return <div className="media-slot">
    {children}
    {path && <button className="media-switch" type="button" onClick={() => setVideo(true)}>
      <Play size={16} /> Ver grabación
    </button>}
  </div>;
}

function Model({ scene }) {
  const fx = useFx();
  return (
    <div className="scene-layout model-layout">
      <Heading scene={scene}>
        <div className="model-status">
          <Box size={16} /> IFC4 <span>DRAFT</span>{fx && <Esquinas delay={1.92} />}
        </div>
      </Heading>
      <MediaSlot path={pitch.media.modelVideo}>
        <div className="materialize">
          <div className="model-grid" aria-hidden="true" />
          <div className="model-sheet"><Plan /></div>
          <div className="model-volume">
            <img className="ifc-outline" src={asset(pitch.media.outline)} alt="" />
            <img className="ifc-steel" src={asset(pitch.media.ifcB)} alt={`Render de la geometría IFC de ${pitch.equipment}, revisión B`} />
            <div className="scan" aria-hidden="true" />
          </div>
          <span className="art-label">{pitch.equipment} / IFC REV. B</span>
        </div>
      </MediaSlot>
    </div>
  );
}

function Delta({ scene }) {
  const fx = useFx();
  const table = useRef(null);
  const markerDelay = 0.44;
  const interval = 0.38;
  return (
    <div className="delta-layout">
      <Heading scene={scene} />
      <div className="delta-content">
        <MediaSlot path={pitch.media.changesVideo}>
          <div className="delta-models">
            <Reveal className="delta-vessel" delay={0.14} from="translateX(-20px)" to="translateX(0px)">
              <span>REV. A</span><img src={asset(pitch.media.ifcA)} alt="Modelo IFC de la revisión A" />
            </Reveal>
            <m.div className="delta-arrow" aria-hidden="true"
              initial={fx ? { transform: "scale(1)" } : false}
              animate={fx ? { transform: ["scale(1)", "scale(1.19)", "scale(1)"] } : undefined}
              transition={{ delay: 0.40, duration: 0.46, ease: easeInOut }}
            ><ArrowRight size={28} /></m.div>
            <Reveal className="delta-vessel after" delay={0.29} from="translateX(20px)" to="translateX(0px)">
              <span>REV. B</span><img src={asset(pitch.media.ifcB)} alt="Modelo IFC de la revisión B" />
            </Reveal>
          </div>
        </MediaSlot>
        <div className={`delta-table ${fx ? "fx-delta-table" : ""}`} ref={table} aria-label="Cambios detectados">
          {pitch.changes.map(({ field, before, after, delta }, index) => {
            const change = delta.match(/^\+([\d.]+) mm$/);
            const hit = markerDelay + interval * index;
            return (
            <Reveal className="delta-row" key={field} delay={0.21 + 0.08 * index}>
              <div><strong>{field}</strong><span>{before} → {after} mm</span></div>
              <strong className="delta-number">{fx && change
                ? <Contador value={Number(change[1].replaceAll(".", ""))} format={formatDelta} delay={hit} duration={0.47} />
                : fx ? <m.span className="fx-delta-add"
                  initial={{ transform: "scale(.93)", opacity: 0.45 }}
                  animate={{ transform: "scale(1)", opacity: 1 }}
                  transition={{
                    transform: { type: "spring", duration: 0.43, bounce: 0.27, delay: hit },
                    opacity: { duration: 0.29, ease, delay: hit },
                  }}>{delta}</m.span> : delta}</strong>
            </Reveal>
            );
          })}
          {fx && <DeltaMarker container={table} delay={markerDelay} interval={interval} />}
        </div>
      </div>
    </div>
  );
}

function Scale({ scene }) {
  const fx = useFx();
  const architecture = useRef(null);
  const { population, drafts, errors, speedup } = pitch.batch;
  const multiplier = speedup.match(/^([\d]+(?:[.,]\d+)?)×$/);
  const metrics = [
    [population, "revisiones", formatNumber, number.format(population)],
    [drafts, "IFC DRAFT", formatNumber, number.format(drafts)],
    [errors, "errores", formatNumber, number.format(errors)],
    [multiplier ? Number(multiplier[1].replace(",", ".")) : null, "aceleración", formatSpeedup, speedup],
  ];
  return (
    <div className="scale-layout">
      <Heading scene={scene} />
      <div className="scale-metrics">
        {metrics.map(([value, label, format, text], index) => (
          <Reveal className="factor" delay={0.25 + 0.075 * index} key={label}>
            <strong>{fx && value !== null ? <Contador value={value} format={format} delay={0.3 + index * 0.075} /> : text}</strong><span>{label}</span>
          </Reveal>
        ))}
      </div>
      <div className="architecture" ref={architecture} aria-label="Arquitectura del lote">
        {[[Database, "Caché por huella"], [Workflow, "Cola y workers"], [GitCompareArrows, "Delta de revisiones"], [Check, "Revisión humana"]].map(([Icon, title], index) => (
          <Reveal className="process-step" key={title} data-fx-step delay={0.39 + 0.07 * index}><Icon size={19} /><strong>{title}</strong></Reveal>
        ))}
        {fx && <PuntoRecorrido container={architecture} delay={0.81} interval={0.36} echoes />}
      </div>
      {!fx && <SourceNote id="scale" />}
    </div>
  );
}

function Close({ scene }) {
  const fx = useFx();
  const flow = useRef(null);
  const travelDelay = 0.68;
  const interval = 0.26;
  const decision = travelDelay + 4 * interval;
  const check = (delay) => fx ? (
    <m.svg width={17} height={17} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
      initial={{ clipPath: "inset(0% 100% 0% 0%)" }}
      animate={{ clipPath: "inset(0% 0% 0% 0%)" }}
      transition={{ duration: 0.35, delay, ease }}
    ><path d="m20 6-11 11-5-5" /></m.svg>
  ) : <Check size={17} />;
  return (
    <div className="close-layout">
      <Heading scene={scene} />
      <div className="end-flow" ref={flow} aria-label="Recorrido completo">
        {["Plano", "Dato", "Modelo", "Cambio", "Decisión"].map((label, index) => (
          <Reveal key={label} data-fx-step delay={0.24 + index * 0.085}>
            {index > 0 && <ChevronRight aria-hidden="true" size={20} />}
            <span className="fx-flow-word">{label}{fx && index === 4 && <Esquinas delay={decision} breathing />}</span>
          </Reveal>
        ))}
        {fx && <PuntoRecorrido container={flow} delay={travelDelay} interval={interval} />}
      </div>
      <Reveal className="next-measures" delay={0.67}>
        <span>{check(decision + 0.2)} Medir fidelidad frente al IFC de referencia</span>
        <span>{check(decision + 0.36)} Cronometrar la revisión humana</span>
      </Reveal>
    </div>
  );
}

const layouts = { open: Hero, cost: Cost, input: Input, trace: Evidence, bench: Bench, model: Model, delta: Delta, scale: Scale, close: Close };

export function Slide({ scene }) {
  const Layout = layouts[scene.id];
  return <Layout scene={scene} />;
}
