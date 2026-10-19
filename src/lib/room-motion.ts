/** A short release tail; native scroll momentum is consumed before adding our own. */
export const ROOM_MAX_SPEED = 1.25;

export class RoomMotion {
  position = 0;
  target = 0;
  private raw = 0;
  private inputAt = 0;
  private releasedAt = -Infinity;
  private releaseSpeed = 0;
  private tail = 0;

  constructor(readonly end: number) {}

  begin() {
    this.releaseSpeed = 0; this.tail = 0;
    if (this.raw > 0 && this.raw < this.end) this.target = this.position;
  }

  scroll(raw: number, now: number) {
    const delta = raw - this.raw;
    this.raw = raw;
    this.inputAt = now;
    this.target = raw <= 0 ? 0 : raw >= this.end ? this.end : this.clamp(this.target + delta);
  }

  release(speed: number, now: number) {
    this.releaseSpeed = Math.max(-ROOM_MAX_SPEED, Math.min(ROOM_MAX_SPEED, speed));
    this.releasedAt = now;
    this.tail = 0;
  }

  step(milliseconds: number, now: number) {
    const dt = Math.min(40, Math.max(0, milliseconds));
    const age = now - this.releasedAt;
    if (now - this.inputAt > 80 && age < 650 && Math.abs(this.tail) < .45) {
      const extra = this.releaseSpeed * Math.exp(-age / 190) * dt / 1000;
      this.tail += extra;
      this.target = this.clamp(this.target + extra);
    }
    const difference = this.target - this.position;
    const eased = difference * (1 - Math.exp(-dt / 135));
    const limit = ROOM_MAX_SPEED * dt / 1000;
    this.position = this.clamp(this.position + Math.max(-limit, Math.min(limit, eased)));
    if (Math.abs(this.position - this.target) < 1 / 480) this.position = this.target;
    return this.position;
  }

  get moving() { return Math.abs(this.position - this.target) > 1 / 480; }
  private clamp(value: number) { return Math.max(0, Math.min(this.end, value)); }
}
