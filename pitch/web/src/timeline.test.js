import assert from "node:assert/strict";
import test from "node:test";
import { scenes } from "./pitch-data.js";
import { buildTimeline, clock, sceneIndex } from "./timeline.js";

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
