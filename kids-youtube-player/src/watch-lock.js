export const REQUIRED_SECONDS = 60;

// A single tick never adds more than this, so time spent asleep or frozen
// in the background is not counted as watching.
const MAX_TICK_SECONDS = 1;

/**
 * Keeps a video locked until it has actually played for `requiredSeconds`.
 * Feed it `update(nowMs, isPlaying)` on a timer; only time between two
 * consecutive playing ticks counts.
 */
export class WatchLock {
  constructor({ requiredSeconds = REQUIRED_SECONDS, watchedSeconds = 0 } = {}) {
    this.requiredSeconds = requiredSeconds;
    this.watchedSeconds = watchedSeconds;
    this.lastTick = null;
    this.ended = false;
    this.released = false;
  }

  update(nowMs, isPlaying) {
    if (this.lastTick !== null) {
      const delta = (nowMs - this.lastTick) / 1000;
      if (delta > 0) this.watchedSeconds += Math.min(delta, MAX_TICK_SECONDS);
    }
    this.lastTick = isPlaying ? nowMs : null;
  }

  /** The video reached its end. */
  finish() {
    this.ended = true;
  }

  /** A parent ended the lock early. */
  release() {
    this.released = true;
  }

  get unlocked() {
    return this.ended || this.released || this.watchedSeconds >= this.requiredSeconds;
  }

  get remainingSeconds() {
    if (this.unlocked) return 0;
    return Math.ceil(this.requiredSeconds - this.watchedSeconds);
  }
}
