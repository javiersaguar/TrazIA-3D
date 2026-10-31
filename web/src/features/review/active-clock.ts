/** Tiempo con atención, con corte de inactividad de 60 s. No demuestra presencia humana. */
export class ActiveReviewClock {
  private total = 0;
  private accounted = 0;
  private last: number;
  private activityAt: number;
  private running = false;
  private blocked = false;

  constructor(private now: () => number = () => performance.now()) {
    this.last = this.activityAt = now();
  }

  private tick() {
    const now = this.now();
    if (this.running) this.total += Math.max(0, Math.min(now, this.activityAt + 60_000) - this.last) / 1000;
    this.last = now;
  }

  activity() { this.tick(); this.activityAt = this.now(); }
  resume() { this.tick(); this.activityAt = this.last; this.running = !this.blocked; }
  pause() { this.tick(); this.running = false; }
  block() { this.pause(); this.blocked = true; }
  unblock() { this.blocked = false; }
  seconds() { this.tick(); return this.total; }
  unaccounted() { return Math.max(0, this.seconds() - this.accounted); }
  commit(seconds: number) { this.accounted += seconds; }
}
