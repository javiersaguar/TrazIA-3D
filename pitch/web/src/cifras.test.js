import assert from "node:assert/strict";
import test from "node:test";
import { conCifras, pitch, scenes } from "./pitch-data.js";
import { buildTimeline } from "./timeline.js";

const cifras = {
  fecha: "2026-11-26",
  lote: { equipos: 40, revisiones: 120, correctas: 104, errores: 16, segundos_mediana: 7.4 },
  evaluacion: { equipos: 4, error_relativo_diametro: 0.0123, boquillas_recall: 0.8 },
};

test("sin cifras del evento el pitch sigue siendo el sintético", () => {
  assert.equal(pitch.batch.population, 336);
  assert.equal(pitch.dataset, "Datos sintéticos");
});

test("con cifras, el lote y las notas de escala pasan a ser las del evento", () => {
  const resultado = conCifras(pitch, scenes, cifras);
  assert.equal(resultado.pitch.batch.population, 120);
  assert.equal(resultado.pitch.batch.speedup, null);
  assert.equal(resultado.pitch.batch.medianSeconds, 7.4);
  assert.match(resultado.pitch.batch.detail, /Dataset del reto/);
  const escala = resultado.scenes.find(({ id }) => id === "scale");
  assert.match(escala.notes, /120 revisiones de 40 equipos/);
  assert.match(escala.notes, /1,2 %/);
  assert.match(escala.notes, /80 % de las boquillas/);
  // Las cifras no cambian la duración: los seis bloques siguen en su sitio.
  assert.equal(buildTimeline(resultado.scenes).at(-1).end, 360);
});

test("sin evaluación contra TR se dice que no hay cifra", () => {
  const { scenes: escenas } = conCifras(pitch, scenes, { ...cifras, evaluacion: null });
  assert.match(escenas.find(({ id }) => id === "scale").notes, /todavía no tiene cifra/);
});
