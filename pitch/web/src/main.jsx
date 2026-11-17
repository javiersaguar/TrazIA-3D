import React, { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { AnimatePresence, LazyMotion, MotionConfig, domAnimation, m, useIsPresent, useReducedMotion } from "motion/react";
import { ExternalLink, NotebookPen, Timer } from "lucide-react";
import "@fontsource/barlow-condensed/latin-700.css";
import "@fontsource/barlow-condensed/latin-800.css";
import "@fontsource/dm-sans/latin-400.css";
import "@fontsource/dm-sans/latin-500.css";
import "@fontsource/dm-sans/latin-700.css";
import { pitch, chapters, scenes } from "./pitch-data.js";
import { buildTimeline, sceneIndex, clock, idleStopwatch, stopwatchSeconds, updateStopwatch } from "./timeline.js";
import { asset, ease, easeInOut, useFx, usePreloadScene } from "./fx.jsx";
import { Slide, SourceNote } from "./scenes.jsx";
import "./styles.css";
import "./presentation-head.css";

const timeline = buildTimeline(scenes);
const duration = timeline.at(-1).end;

function readClock(rehearsal, now) {
  const played = rehearsal.started === null ? 0 : Math.max(0, now - rehearsal.started) / 1000;
  return Math.min(duration, rehearsal.offset + played);
}

function destination(index, target, relative) {
  return Math.max(0, Math.min(timeline.length - 1, relative ? index + target : target));
}

function SceneFrame({ scene, chapter, reduced, fx, crossing }) {
  const present = useIsPresent();
  return (
    <m.main
      className={`slide slide--${scene.id}${fx ? " slide--fx" : ""}`}
      data-scene={scene.id}
      aria-hidden={present ? undefined : true}
      inert={!present}
      initial={reduced ? false : { opacity: 0, transform: fx ? "translateY(11px)" : "translateY(11px) scale(.99)" }}
      animate={{ opacity: 1, transform: fx ? "translateY(0px)" : "translateY(0px) scale(1)" }}
      exit={{ opacity: 0, ...(fx && { transition: { duration: 0.18, ease: "easeIn" } }) }}
      transition={{ duration: reduced ? 0 : fx ? 0.37 : 0.32, ease, delay: crossing ? 0.17 : 0 }}
    >
      <div className="slide-top">
        <span>{chapter}</span>
        <span>{clock(scene.start)} – {clock(scene.end)}</span>
      </div>
      <Slide scene={scene} />
    </m.main>
  );
}

function SceneCut({ kind }) {
  return kind === "curtain" ? (
    <m.div className="fx-curtain" aria-hidden="true"
      initial={{ clipPath: "inset(0% 100% 0% 0%)" }}
      animate={{ clipPath: ["inset(0% 100% 0% 0%)", "inset(0% 0% 0% 0%)", "inset(0% 0% 0% 100%)"] }}
      transition={{ duration: 0.74, times: [0, 0.42, 1], ease: easeInOut }}
    />
  ) : (
    <m.div className="fx-cut-line" aria-hidden="true"
      initial={{ transform: "translateY(-100%)", opacity: 0 }}
      animate={{ transform: ["translateY(-100%)", "translateY(0%)"], opacity: [0, 0.88, 0.88, 0] }}
      transition={{
        transform: { duration: 0.55, ease: "linear" },
        opacity: { duration: 0.55, times: [0, 0.12, 0.85, 1], ease: "linear" },
      }}
    />
  );
}

function Stopwatch({ state, onToggle }) {
  const [now, setNow] = useState(() => performance.now());
  useEffect(() => {
    if (state.started === null) return;
    const timer = window.setInterval(() => setNow(performance.now()), 250);
    return () => window.clearInterval(timer);
  }, [state.started]);
  const label = { idle: "Iniciar", running: "Pausar", paused: "Reanudar" }[state.status];
  return (
    <button className="presentation-timer" data-status={state.status} type="button"
      onClick={onToggle} title={label + " cronómetro (T)"} aria-keyshortcuts="T">
      <Timer size={15} aria-hidden="true" />
      <span className="sr-only">{label} cronómetro de exposición. Tiempo transcurrido </span>
      <span role="timer" aria-live="off">{clock(stopwatchSeconds(state, now))}</span>
    </button>
  );
}

function App() {
  const reduced = useReducedMotion();
  const fx = useFx();
  const [rehearsal, setRehearsal] = useState({ offset: 0, started: null });
  const [now, setNow] = useState(0);
  const [stopwatch, dispatchStopwatch] = useReducer(updateStopwatch, idleStopwatch);
  const touchStart = useRef(null);
  const notesButton = useRef(null);
  const notesPanel = useRef(null);
  const [notes, showNotes] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [fullscreenError, setFullscreenError] = useState("");
  const [replay, setReplay] = useState(0);
  const elapsed = readClock(rehearsal, now);
  const index = sceneIndex(timeline, elapsed);
  const scene = timeline[index];
  const currentChapter = chapters.find(({ id }) => id === scene.chapter);
  const playing = rehearsal.started !== null;
  const demoUrl = pitch.demoOrigin && scene.demoPath ? new URL(scene.demoPath, pitch.demoOrigin).href : "";
  const sceneKey = `${scene.id}-${replay}`;
  const [cut, setCut] = useState({ key: sceneKey, chapter: scene.chapter, kind: null });
  if (cut.key !== sceneKey) {
    setCut({ key: sceneKey, chapter: scene.chapter, kind: cut.chapter === scene.chapter ? "line" : "curtain" });
  }
  usePreloadScene(timeline[index + 1]?.id);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      const stamp = performance.now();
      setNow(stamp);
      if (readClock(rehearsal, stamp) >= duration) setRehearsal({ offset: duration, started: null });
    }, 125);
    return () => window.clearInterval(timer);
  }, [playing, rehearsal]);

  const present = useCallback((type, stamp) => {
    if (stopwatch.status === "idle" && index === 0) setReplay(value => value + 1);
    dispatchStopwatch({ type, now: stamp });
  }, [index, stopwatch.status]);

  const toggleStopwatch = useCallback(() => {
    present("toggle", performance.now());
  }, [present]);

  const closeNotes = useCallback(() => {
    showNotes(false);
    notesButton.current?.focus();
  }, []);

  useEffect(() => {
    if (notes) notesPanel.current?.focus();
  }, [notes]);

  const goTo = useCallback((target, relative = false) => {
    const stamp = performance.now();
    if (destination(index, target, relative) !== index) dispatchStopwatch({ type: "start", now: stamp });
    setNow(stamp);
    setRehearsal((current) => {
      const currentIndex = sceneIndex(timeline, readClock(current, stamp));
      const next = destination(currentIndex, target, relative);
      if (relative && next === currentIndex) return current;
      return { offset: timeline[next].start, started: current.started === null ? null : stamp };
    });
  }, [index]);

  const toggleClock = useCallback(() => {
    const stamp = performance.now();
    present("start", stamp);
    setNow(stamp);
    setRehearsal((current) => current.started === null
      ? { offset: current.offset >= duration ? 0 : current.offset, started: stamp }
      : { offset: readClock(current, stamp), started: null });
  }, [present]);

  const reset = useCallback(() => {
    dispatchStopwatch({ type: "reset" });
    setRehearsal({ offset: 0, started: null });
  }, []);

  const toggleFullscreen = useCallback(async () => {
    setFullscreenError("");
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else {
        present("start", performance.now());
        await document.documentElement.requestFullscreen();
      }
    } catch {
      setFullscreenError("El navegador no pudo abrir la pantalla completa.");
    }
  }, [present]);

  useEffect(() => {
    const watch = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", watch);
    return () => document.removeEventListener("fullscreenchange", watch);
  }, []);

  useEffect(() => {
    function key(event) {
      const target = event.target instanceof Element ? event.target : null;
      if (event.altKey || event.ctrlKey || event.metaKey || target?.closest("input, textarea, select, video, [contenteditable]")) return;
      if (event.key === "Escape" && notes) closeNotes();
      if (event.repeat && ["p", "n", "f", "r", "t"].includes(event.key.toLowerCase())) return;
      if (event.key === " " && target?.closest("button, a")) return;
      switch (event.key.toLowerCase()) {
        case "arrowright":
        case "pagedown":
        case " ":
          event.preventDefault();
          goTo(1, true);
          break;
        case "arrowleft":
        case "pageup":
          event.preventDefault();
          goTo(-1, true);
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
        case "t": toggleStopwatch(); break;
        case "n": if (notes) closeNotes(); else showNotes(true); break;
        case "f": void toggleFullscreen(); break;
        case "r": if (!event.repeat) setReplay((value) => value + 1); break;
        default: break;
      }
    }
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [closeNotes, notes, goTo, reset, toggleClock, toggleFullscreen, toggleStopwatch]);

  function beginSwipe(event) {
    touchStart.current = null;
    if (event.touches.length !== 1 || event.target.closest("button, a, input, video[controls], aside")) return;
    const { clientX, clientY, identifier } = event.touches[0];
    touchStart.current = { clientX, clientY, identifier };
  }

  function endSwipe(event) {
    const start = touchStart.current;
    touchStart.current = null;
    const end = event.changedTouches[0];
    if (!start || !end || end.identifier !== start.identifier || event.touches.length) return;
    const dx = end.clientX - start.clientX;
    const dy = end.clientY - start.clientY;
    if (Math.abs(dx) > 54 && Math.abs(dx) > Math.abs(dy) * 1.5) goTo(dx < 0 ? 1 : -1, true);
  }

  const frame = <SceneFrame key={sceneKey} scene={scene} chapter={currentChapter.name}
    reduced={reduced} fx={fx} crossing={fx && cut.kind === "curtain"} />;

  return (
    <div className="deck">
      <header className="deck-head">
        <div className="brand" aria-label={pitch.brand}>
          <img src={asset("media/brand.svg")} alt="" width="34" height="34" />
          <span>TrazIA <b>3D</b></span>
        </div>
        <span className="challenge">{pitch.challenge}</span>
        <div className="presentation-tools">
          <span className="dataset"><i />{pitch.dataset}</span>
          <Stopwatch state={stopwatch} onToggle={toggleStopwatch} />
          <button ref={notesButton} type="button" className="presentation-notes-toggle"
            aria-expanded={notes} aria-controls={notes ? "speaker-notes" : undefined} aria-keyshortcuts="N"
            title="Guion y controles (N)" aria-label="Guion y controles" onClick={() => showNotes(!notes)}>
            <NotebookPen size={16} aria-hidden="true" />
          </button>
        </div>
      </header>

      <div className="deck-stage" data-scene-index={index + 1} data-rehearsing={playing}
        onTouchStart={beginSwipe} onTouchEnd={endSwipe} onTouchCancel={() => { touchStart.current = null; }}>
        <span className="sr-only" aria-live="polite">Escena {index + 1} de {timeline.length}. {scene.title} {scene.accent}</span>
        {reduced ? frame : <AnimatePresence>{frame}</AnimatePresence>}
        {fx && cut.kind && <SceneCut key={cut.key} kind={cut.kind} />}
        {fx && <SourceNote id={scene.id} pinned />}
        {notes && <aside id="speaker-notes" className="speaker-notes" aria-label="Notas de exposición" tabIndex={-1} ref={notesPanel}>
          <div><h2>Guion de exposición</h2><span>{clock(scene.seconds)} por escena</span></div>
          <p>{scene.notes}</p>
          <nav className="presentation-actions" aria-label="Controles de presentación">
            <button type="button" onClick={() => goTo(-1, true)} disabled={index === 0}>← Anterior</button>
            <button type="button" onClick={() => goTo(1, true)} disabled={index === timeline.length - 1}>Siguiente →</button>
            <button type="button" onClick={() => void toggleFullscreen()}><kbd>F</kbd> {fullscreen ? "Salir de pantalla completa" : "Pantalla completa"}</button>
            <button type="button" onClick={toggleClock} aria-pressed={playing}><kbd>P</kbd> {playing ? "Pausar ensayo" : "Ensayar"}</button>
            <button type="button" onClick={toggleStopwatch}><kbd>T</kbd> {stopwatch.status === "running" ? "Pausar" : stopwatch.status === "paused" ? "Reanudar" : "Iniciar"} cronómetro</button>
            <button type="button" onClick={() => setReplay(value => value + 1)}><kbd>R</kbd> Repetir entrada</button>
            <button type="button" onClick={reset}><kbd>Inicio</kbd> Reiniciar</button>
            {demoUrl && <a href={demoUrl} target="_blank" rel="noreferrer"><ExternalLink size={14} /> Abrir demo</a>}
          </nav>
          <button type="button" className="text-link" onClick={closeNotes}>Ocultar notas</button>
        </aside>}
        {fullscreenError && <p role="status" className="fullscreen-error">{fullscreenError}</p>}
      </div>

    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <MotionConfig reducedMotion="user">
    <LazyMotion features={domAnimation} strict><App /></LazyMotion>
  </MotionConfig>,
);
