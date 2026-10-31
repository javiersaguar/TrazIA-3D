import { describe, expect, it } from "vitest";
import { ActiveReviewClock } from "./active-clock";
import { parseReviewNumber } from "./review-value";

describe("tiempo activo de revisión", () => {
  it("excluye pausas, guardados e inactividad y conserva una acción fallida", () => {
    let now = 0;
    const clock = new ActiveReviewClock(() => now);
    clock.resume();
    now = 10_000;
    expect(clock.unaccounted()).toBe(10);
    clock.block();
    now = 40_000;
    clock.resume(); // Un focus durante la petición no reactiva el reloj bloqueado.
    now = 50_000;
    expect(clock.unaccounted()).toBe(10);
    clock.unblock(); clock.resume();
    now = 55_000;
    expect(clock.unaccounted()).toBe(15); // La acción fallida no consume el tiempo.
    clock.commit(15);
    clock.pause();
    now = 100_000;
    expect(clock.unaccounted()).toBe(0);
    clock.resume();
    now = 200_000;
    expect(clock.unaccounted()).toBe(60);
    clock.activity();
    now = 205_000;
    expect(clock.seconds()).toBe(80);
  });

  it("admite coordenadas negativas y decimales, y rechaza entradas ambiguas", () => {
    expect(parseReviewNumber("-0,5")).toBe(-0.5);
    expect(parseReviewNumber("0.5")).toBe(0.5);
    expect(parseReviewNumber("1.234,5")).toBe(1234.5);
    expect(Number.isNaN(parseReviewNumber(""))).toBe(true);
    expect(Number.isNaN(parseReviewNumber("1..2,3"))).toBe(true);
  });
});
