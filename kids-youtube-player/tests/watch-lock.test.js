import { describe, it, expect } from 'vitest';
import { WatchLock } from '../src/watch-lock.js';

describe('WatchLock', () => {
  it('starts locked with the full minute remaining', () => {
    const lock = new WatchLock();
    expect(lock.unlocked).toBe(false);
    expect(lock.remainingSeconds).toBe(60);
  });

  it('counts only time spent playing', () => {
    const lock = new WatchLock();
    lock.update(0, true);
    lock.update(500, true);
    lock.update(1000, true);
    lock.update(1500, false); // paused: the last half second still counted
    lock.update(30000, false); // long pause adds nothing
    expect(lock.watchedSeconds).toBeCloseTo(1.5);
    lock.update(30250, true); // resume: first tick only sets the baseline
    lock.update(30750, true);
    expect(lock.watchedSeconds).toBeCloseTo(2);
  });

  it('ignores big jumps between ticks, such as the phone sleeping', () => {
    const lock = new WatchLock();
    lock.update(0, true);
    lock.update(120000, true);
    expect(lock.watchedSeconds).toBe(1);
  });

  it('unlocks after 60 seconds of playing', () => {
    const lock = new WatchLock();
    for (let t = 0; t <= 59500; t += 500) lock.update(t, true);
    expect(lock.unlocked).toBe(false);
    expect(lock.remainingSeconds).toBe(1);
    lock.update(60000, true);
    expect(lock.unlocked).toBe(true);
    expect(lock.remainingSeconds).toBe(0);
  });

  it('unlocks when the video ends, even before a minute', () => {
    const lock = new WatchLock();
    lock.finish();
    expect(lock.unlocked).toBe(true);
  });

  it('unlocks when released by a parent', () => {
    const lock = new WatchLock();
    lock.release();
    expect(lock.unlocked).toBe(true);
  });

  it('resumes from previously watched seconds', () => {
    const lock = new WatchLock({ watchedSeconds: 45 });
    expect(lock.remainingSeconds).toBe(15);
  });

  it('honours a custom requirement', () => {
    const lock = new WatchLock({ requiredSeconds: 10 });
    lock.update(0, true);
    for (let t = 1000; t <= 10000; t += 1000) lock.update(t, true);
    expect(lock.unlocked).toBe(true);
  });
});
