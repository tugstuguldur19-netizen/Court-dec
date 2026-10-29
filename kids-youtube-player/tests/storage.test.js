import { describe, it, expect } from 'vitest';
import { createStorage } from '../src/storage.js';

function memoryBacking() {
  const map = new Map();
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(k, String(v)),
    removeItem: (k) => map.delete(k),
    map,
  };
}

describe('storage', () => {
  it('round-trips JSON under a prefix', () => {
    const backing = memoryBacking();
    const storage = createStorage(backing);
    storage.set('channels', [{ id: 'UC1' }]);
    expect(storage.get('channels')).toEqual([{ id: 'UC1' }]);
    expect([...backing.map.keys()]).toEqual(['kyp:channels']);
  });

  it('returns the fallback for missing or corrupt values', () => {
    const backing = memoryBacking();
    const storage = createStorage(backing);
    expect(storage.get('missing', 'x')).toBe('x');
    backing.setItem('kyp:bad', '{not json');
    expect(storage.get('bad', [])).toEqual([]);
  });

  it('removes values', () => {
    const storage = createStorage(memoryBacking());
    storage.set('a', 1);
    storage.remove('a');
    expect(storage.get('a', null)).toBeNull();
  });
});
