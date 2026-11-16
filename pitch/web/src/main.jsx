import React, { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { AnimatePresence, LazyMotion, MotionConfig, domAnimation, m, useIsPresent, useReducedMotion } from "motion/react";
import { ArrowLeft, ArrowRight, ExternalLink, Maximize, Minimize, NotebookPen, Pause, Play, RotateCcw } from "lucide-react";
import "@fontsource/barlow-condensed/latin-700.css";
import "@fontsource/barlow-condensed/latin-800.css";
import "@fontsource/dm-sans/latin-400.css";
import "@fontsource/dm-sans/latin-500.css";
import "@fontsource/dm-sans/latin-700.css";
import { pitch, chapters, scenes } from "./pitch-data.js";
import { buildTimeline, sceneIndex, clock } from "./timeline.js";
import { asset, ease, Slide } from "./scenes.jsx";
import "./styles.css";

const timeline = buildTimeline(scenes);
const duration = timeline.at(-1).end;
const chapterStarts = chapters.map(({ id }) => timeline.findIndex(({ chapter }) => chapter === id));

function readClock(rehearsal, now) {
  const played = rehearsal.started === null ? 0 : Math.max(0, now - rehearsal.started) / 1000;
  return Math.min(duration, rehearsal.offset + played);
}

function SceneFrame({ scene, chapter, reduced }) {
  const present = useIsPresent();
  return (
    <m.main
      className={`slide slide--${scene.id}`}
      data-scene={scene.id}
      aria-hidden={present ? undefined : true}
      inert={!present}
      initial={reduced ? false : { opacity: 0, transform: "translateY(11px) scale(.99)" }}
      animate={{ opacity: 1, transform: "translateY(0px) scale(1)" }}
      exit={{ opacity: 0 }}
      transition={{ duration: reduced ? 0 : 0.32, ease }}
    >
      <div className="slide-top">
        <span>{chapter}</span>
        <span>{clock(scene.start)} – {clock(scene.end)}</span>
      </div>
      <Slide scene={scene} />
    </m.main>
  );
}

function App() {
  const reduced = useReducedMotion();
  const [rehearsal, setRehearsal] = useState({ offset: 0, started: null });
  const [now, setNow] = useState(0);
  const [notes, showNotes] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [fullscreenError, setFullscreenError] = useState("");
  const elapsed = readClock(rehearsal, now);
  const index = sceneIndex(timeline, elapsed);
  const scene = timeline[index];
  const currentChapter = chapters.find(({ id }) => id === scene.chapter);
  const playing = rehearsal.started !== null;
  const demoUrl = pitch.demoOrigin && scene.demoPath ? new URL(scene.demoPath, pitch.demoOrigin).href : "";

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      const stamp = performance.now();
      setNow(stamp);
      if (readClock(rehearsal, stamp) >= duration) setRehearsal({ offset: duration, started: null });
    }, 125);
    return () => window.clearInterval(timer);
  }, [playing, rehearsal]);

  const goTo = useCallback((target) => {
    const position = timeline[Math.max(0, Math.min(timeline.length - 1, target))].start;
    const stamp = performance.now();
    setNow(stamp);
    setRehearsal((current) => ({ offset: position, started: current.started === null ? null : stamp }));
  }, []);

  const toggleClock = useCallback(() => {
    const stamp = performance.now();
    setNow(stamp);
    setRehearsal((current) => current.started === null
      ? { offset: current.offset >= duration ? 0 : current.offset, started: stamp }
      : { offset: readClock(current, stamp), started: null });
  }, []);

  const reset = useCallback(() => setRehearsal({ offset: 0, started: null }), []);

  const toggleFullscreen = useCallback(async () => {
    setFullscreenError("");
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch {
      setFullscreenError("El navegador no pudo abrir la pantalla completa.");
    }
  }, []);

  useEffect(() => {
    const watch = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", watch);
    return () => document.removeEventListener("fullscreenchange", watch);
  }, []);

  useEffect(() => {
    function key(event) {
      if (event.altKey || event.ctrlKey || event.metaKey || event.target?.closest("input, textarea, select, video, [contenteditable]")) return;
      if (event.key === "Escape" && notes) showNotes(false);
      if (event.key === " " && event.target?.closest("button, a")) return;
      switch (event.key.toLowerCase()) {
        case "arrowright":
        case "pagedown":
        case " ":
          event.preventDefault();
          if (index < timeline.length - 1) goTo(index + 1);
          break;
        case "arrowleft":
        case "pageup":
          event.preventDefault();
          if (index > 0) goTo(index - 1);
          break;
        case "home":
          event.preventDefault();
          reset();
          break;
        case "end":
          event.preventDefault();
          goTo(timeline.length - 1);
          break;
        case "p": toggleClock(); break;
        case "n": showNotes((previous) => !previous); break;
        case "f": void toggleFullscreen(); break;
        default: break;
      }
    }
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [index, notes, goTo, reset, toggleClock, toggleFullscreen]);

  const frame = <SceneFrame key={scene.id} scene={scene} chapter={currentChapter.name} reduced={reduced} />;

  return (
    <div className="deck">
      <header className="deck-head">
        <div className="brand" aria-label={pitch.brand}>
          <img src={asset("media/brand.svg")} alt="" width="34" height="34" />
          <span>TrazIA <b>3D</b></span>
        </div>
        <span className="challenge">{pitch.challenge}</span>
        <span className="dataset"><i />{pitch.dataset}</span>
      </header>

      <div className="deck-stage">
        <span className="sr-only" aria-live="polite">Escena {index + 1} de {timeline.length}. {scene.title} {scene.accent}</span>
        {reduced ? frame : <AnimatePresence>{frame}</AnimatePresence>}
        {notes && <aside className="speaker-notes" aria-label="Notas de exposición">
          <div><h2>Guion de exposición</h2><span>{clock(scene.seconds)} por escena</span></div>
          <p>{scene.notes}</p>
          <button type="button" className="text-link" onClick={() => showNotes(false)}>Ocultar notas</button>
        </aside>}
        {fullscreenError && <p role="status" className="fullscreen-error">{fullscreenError}</p>}
      </div>

      <footer className="transport">
        <nav className="timeline" aria-label="Bloques de la presentación">
          {chapters.map(({ id, name }, chapterIndex) => (
            <button
              key={id}
              onClick={() => goTo(chapterStarts[chapterIndex])}
              type="button"
              className={id === scene.chapter ? "current" : ""}
              aria-current={id === scene.chapter ? "step" : undefined}
            >
              <span>{name}</span>
              <small>{clock(timeline[chapterStarts[chapterIndex]].start)}</small>
            </button>
          ))}
        </nav>
        <div className="track" aria-hidden="true"><i style={{ transform: `scaleX(${elapsed / duration})` }} /></div>
        <div className="control-row">
          <div className="playback">
            <button type="button" className="play-control" onClick={toggleClock} aria-pressed={playing}>
              {playing ? <Pause size={16} /> : <Play size={16} />} {playing ? "Pausar" : "Ensayar"}
            </button>
            <span className="clock">{clock(elapsed)} <span>/</span> {clock(duration)}</span>
            <button type="button" className="icon-button reset" onClick={reset} aria-label="Reiniciar ensayo" title="Reiniciar (Inicio)"><RotateCcw size={16} /></button>
          </div>
          <div className="paging">
            <button type="button" className="icon-button" onClick={() => goTo(index - 1)} disabled={index === 0} aria-label="Escena anterior"><ArrowLeft size={18} /></button>
            <span className="slide-index">{String(index + 1).padStart(2, "0")} <span>/</span> {String(timeline.length).padStart(2, "0")}</span>
            <button type="button" className="icon-button" onClick={() => goTo(index + 1)} disabled={index === timeline.length - 1} aria-label="Escena siguiente"><ArrowRight size={18} /></button>
          </div>
          <div className="extras">
            {demoUrl && <a className="demo-link" href={demoUrl} target="_blank" rel="noreferrer" aria-label="Abrir demo"><ExternalLink size={15} /> <span>Abrir demo</span></a>}
            <button type="button" className="icon-button" onClick={() => showNotes(!notes)} aria-label="Notas de exposición" aria-pressed={notes} title="Notas (N)"><NotebookPen size={17} /></button>
            <button type="button" className="icon-button" onClick={() => void toggleFullscreen()} aria-label={fullscreen ? "Salir de pantalla completa" : "Pantalla completa"} title="Pantalla completa (F)">
              {fullscreen ? <Minimize size={18} /> : <Maximize size={18} />}
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <MotionConfig reducedMotion="user">
    <LazyMotion features={domAnimation} strict><App /></LazyMotion>
  </MotionConfig>,
);
