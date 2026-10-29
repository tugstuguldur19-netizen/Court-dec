const PREFIX = 'kyp:';

/** JSON values in localStorage (or any object with the same three methods). */
export function createStorage(backing = globalThis.localStorage) {
  return {
    get(key, fallback = null) {
      try {
        const raw = backing.getItem(PREFIX + key);
        return raw === null ? fallback : JSON.parse(raw);
      } catch {
        return fallback;
      }
    },
    set(key, value) {
      backing.setItem(PREFIX + key, JSON.stringify(value));
    },
    remove(key) {
      backing.removeItem(PREFIX + key);
    },
  };
}
