import { verifyPin } from './pin.js';

export const MAX_ATTEMPTS = 5;
export const LOCKOUT_MS = 5 * 60 * 1000;

/**
 * Checks the parent PIN, with a lockout after MAX_ATTEMPTS wrong tries so a
 * child can't guess it by trying every number. The count lives in storage so
 * restarting the app doesn't reset it.
 */
export function createPinGate({ storage, now = Date.now }) {
  return {
    async attempt(pin) {
      const state = storage.get('pinFailures', { count: 0, lockedUntil: 0 });
      const waitMs = state.lockedUntil - now();
      if (waitMs > 0) {
        return { ok: false, error: `Too many tries. Wait ${Math.ceil(waitMs / 60000)} min.` };
      }
      if (await verifyPin(pin, storage.get('pin'))) {
        storage.remove('pinFailures');
        return { ok: true };
      }
      const count = state.lockedUntil ? 1 : state.count + 1;
      const lockedUntil = count >= MAX_ATTEMPTS ? now() + LOCKOUT_MS : 0;
      storage.set('pinFailures', { count, lockedUntil });
      return { ok: false, error: lockedUntil ? `Too many tries. Wait ${LOCKOUT_MS / 60000} min.` : 'Wrong PIN' };
    },
  };
}
