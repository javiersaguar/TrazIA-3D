import assert from "node:assert/strict";
import test from "node:test";
import { scenes } from "./pitch-data.js";
import { buildTimeline, clock, idleStopwatch, sceneIndex, stopwatchSeconds, updateStopwatch } from "./timeline.js";

const timeline = buildTimeline(scenes);

test("el pitch respeta los seis bloques cronometrados del reto", () => {
  assert.deepEqual(
    [...new Set(timeline.map(({ chapter }) => chapter))]
      .map((chapter) => timeline.find((scene) => scene.chapter === chapter).start),
    [0, 45, 90, 150, 225, 300],
  );
  assert.equal(timeline.at(-1).end, 360);
  assert.equal(clock(timeline.at(-1).end), "6:00");
});

test("los cortes y el fin seleccionan la escena correcta", () => {
  assert.equal(timeline[sceneIndex(timeline, 89.9)].id, "input");
  assert.equal(timeline[sceneIndex(timeline, 90)].id, "trace");
  assert.equal(timeline[sceneIndex(timeline, 150)].id, "model");
  assert.equal(timeline[sceneIndex(timeline, 360)].id, "close");
});

test("el cronómetro conserva el tiempo al navegar, al pausar y al superar seis minutos", () => {
  const started = updateStopwatch(idleStopwatch, { type: "start", now: 2000 });
  assert.equal(updateStopwatch(started, { type: "start", now: 3500 }), started);
  assert.equal(clock(stopwatchSeconds(started, 370500)), "6:08");
  const paused = updateStopwatch(started, { type: "toggle", now: 370500 });
  assert.equal(stopwatchSeconds(paused, 400000), 368.5);
  assert.equal(updateStopwatch(paused, { type: "start", now: 400000 }), paused);
  const resumed = updateStopwatch(paused, { type: "toggle", now: 400000 });
  assert.equal(stopwatchSeconds(resumed, 402000), 370.5);
  assert.equal(updateStopwatch(resumed, { type: "reset" }), idleStopwatch);
});
