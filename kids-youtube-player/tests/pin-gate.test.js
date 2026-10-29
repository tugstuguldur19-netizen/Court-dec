import { describe, it, expect } from 'vitest';
import { createPinGate, MAX_ATTEMPTS, LOCKOUT_MS } from '../src/pin-gate.js';
import { createPinRecord } from '../src/pin.js';
import { createStorage } from '../src/storage.js';

async function setup() {
  const map = new Map();
  const storage = createStorage({
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(k, v),
    removeItem: (k) => map.delete(k),
  });
  storage.set('pin', await createPinRecord('1357'));
  const clock = { t: 0 };
  return { storage, clock, gate: createPinGate({ storage, now: () => clock.t }) };
}

describe('pin gate', () => {
  it('opens for the right PIN', async () => {
    const { gate } = await setup();
    expect(await gate.attempt('1357')).toEqual({ ok: true });
  });

  it('says when the PIN is wrong', async () => {
    const { gate } = await setup();
    expect(await gate.attempt('0000')).toEqual({ ok: false, error: 'Wrong PIN' });
  });

  it('locks out after too many wrong tries, even with the right PIN', async () => {
    const { gate, clock } = await setup();
    for (let i = 0; i < MAX_ATTEMPTS; i++) await gate.attempt('0000');
    const blocked = await gate.attempt('1357');
    expect(blocked.ok).toBe(false);
    expect(blocked.error).toMatch(/Too many tries/);
    clock.t += LOCKOUT_MS;
    expect(await gate.attempt('1357')).toEqual({ ok: true });
  });

  it('keeps the lockout across app restarts', async () => {
    const { gate, storage, clock } = await setup();
    for (let i = 0; i < MAX_ATTEMPTS; i++) await gate.attempt('0000');
    const restarted = createPinGate({ storage, now: () => clock.t });
    expect((await restarted.attempt('1357')).ok).toBe(false);
  });

  it('resets the count after a success', async () => {
    const { gate } = await setup();
    for (let i = 0; i < MAX_ATTEMPTS - 1; i++) await gate.attempt('0000');
    await gate.attempt('1357');
    for (let i = 0; i < MAX_ATTEMPTS - 1; i++) await gate.attempt('0000');
    expect(await gate.attempt('1357')).toEqual({ ok: true });
  });
});
