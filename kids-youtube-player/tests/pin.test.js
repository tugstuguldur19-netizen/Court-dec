import { describe, it, expect } from 'vitest';
import { createPinRecord, verifyPin, isValidPin } from '../src/pin.js';

describe('pin', () => {
  it('accepts 4 to 6 digits only', () => {
    expect(isValidPin('1234')).toBe(true);
    expect(isValidPin('123456')).toBe(true);
    expect(isValidPin('123')).toBe(false);
    expect(isValidPin('1234567')).toBe(false);
    expect(isValidPin('12a4')).toBe(false);
  });

  it('stores a salted hash, not the PIN', async () => {
    const record = await createPinRecord('2468');
    expect(JSON.stringify(record)).not.toContain('2468');
    expect(record.salt).toMatch(/^[0-9a-f]{32}$/);
    expect(record.hash).toMatch(/^[0-9a-f]{64}$/);
  });

  it('verifies the right PIN and rejects others', async () => {
    const record = await createPinRecord('2468');
    expect(await verifyPin('2468', record)).toBe(true);
    expect(await verifyPin('2469', record)).toBe(false);
    expect(await verifyPin('2468', null)).toBe(false);
  });

  it('uses a different salt each time', async () => {
    const a = await createPinRecord('2468');
    const b = await createPinRecord('2468');
    expect(a.hash).not.toBe(b.hash);
  });
});
