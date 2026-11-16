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
