export function buildTimeline(scenes) {
  let start = 0;
  return scenes.map((scene) => {
    const entry = { ...scene, start, end: start + scene.seconds };
    start = entry.end;
    return entry;
  });
}

export function sceneIndex(timeline, seconds) {
  const next = timeline.findIndex(({ end }) => seconds < end);
  return next < 0 ? timeline.length - 1 : next;
}

export function clock(seconds) {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

export const idleStopwatch = { status: "idle", seconds: 0, started: null };

export function stopwatchSeconds(state, now) {
  if (state.started === null) return state.seconds;
  return state.seconds + Math.max(0, now - state.started) / 1000;
}

export function updateStopwatch(state, { type, now }) {
  if (type === "reset") return idleStopwatch;
  if (type === "start" && state.status !== "idle") return state;
  if (type === "toggle" && state.status === "running") {
    return { status: "paused", seconds: stopwatchSeconds(state, now), started: null };
  }
  return { status: "running", seconds: state.seconds, started: now };
}
