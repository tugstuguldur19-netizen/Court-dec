import { describe, it, expect, vi } from 'vitest';
import { createVideoFeed, CACHE_TTL_MS } from '../src/video-feed.js';
import { createStorage } from '../src/storage.js';

function memoryStorage() {
  const map = new Map();
  return createStorage({
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(k, v),
    removeItem: (k) => map.delete(k),
  });
}

const video = (id, channelId, publishedAt) => ({ id, channelId, title: id, channelTitle: channelId, publishedAt, thumbnail: '' });
const A = { id: 'UCa', title: 'A' };
const B = { id: 'UCb', title: 'B' };

function pages(map) {
  return vi.fn(async (channelId, token) => {
    const page = map[`${channelId}:${token ?? ''}`];
    if (page instanceof Error) throw page;
    return page;
  });
}

describe('video feed', () => {
  it('merges channels newest first', async () => {
    const fetchPage = pages({
      'UCa:': { videos: [video('a2', 'UCa', '2026-10-05'), video('a1', 'UCa', '2026-10-01')], nextPageToken: null },
      'UCb:': { videos: [video('b1', 'UCb', '2026-10-03')], nextPageToken: null },
    });
    const feed = createVideoFeed({ storage: memoryStorage(), fetchPage });
    const result = await feed.load([A, B]);
    expect(result.videos.map((v) => v.id)).toEqual(['a2', 'b1', 'a1']);
    expect(result.hasMore).toBe(false);
    expect(result.errors).toEqual([]);
  });

  it('uses the cache until it is 3 hours old', async () => {
    let now = 1_000_000;
    const fetchPage = pages({ 'UCa:': { videos: [video('a1', 'UCa', '2026-10-01')], nextPageToken: null } });
    const feed = createVideoFeed({ storage: memoryStorage(), fetchPage, now: () => now });
    await feed.load([A]);
    now += CACHE_TTL_MS - 1;
    await feed.load([A]);
    expect(fetchPage).toHaveBeenCalledTimes(1);
    now += 2;
    await feed.load([A]);
    expect(fetchPage).toHaveBeenCalledTimes(2);
  });

  it('refetches when forced', async () => {
    const fetchPage = pages({ 'UCa:': { videos: [], nextPageToken: null } });
    const feed = createVideoFeed({ storage: memoryStorage(), fetchPage });
    await feed.load([A]);
    await feed.load([A], { force: true });
    expect(fetchPage).toHaveBeenCalledTimes(2);
  });

  it('falls back to stale cache and reports the error', async () => {
    let now = 0;
    const storage = memoryStorage();
    const ok = pages({ 'UCa:': { videos: [video('a1', 'UCa', '2026-10-01')], nextPageToken: null } });
    await createVideoFeed({ storage, fetchPage: ok, now: () => now }).load([A]);
    now += CACHE_TTL_MS + 1;
    const failing = pages({ 'UCa:': new Error('No internet') });
    const result = await createVideoFeed({ storage, fetchPage: failing, now: () => now }).load([A]);
    expect(result.videos.map((v) => v.id)).toEqual(['a1']);
    expect(result.errors).toEqual(['No internet']);
  });

  it('loads more pages for channels that have them', async () => {
    const fetchPage = pages({
      'UCa:': { videos: [video('a2', 'UCa', '2026-10-05')], nextPageToken: 'P2' },
      'UCa:P2': { videos: [video('a1', 'UCa', '2026-10-01')], nextPageToken: null },
      'UCb:': { videos: [video('b1', 'UCb', '2026-10-03')], nextPageToken: null },
    });
    const feed = createVideoFeed({ storage: memoryStorage(), fetchPage });
    expect((await feed.load([A, B])).hasMore).toBe(true);
    const more = await feed.loadMore([A, B]);
    expect(more.videos.map((v) => v.id)).toEqual(['a2', 'b1', 'a1']);
    expect(more.hasMore).toBe(false);
    expect(fetchPage).toHaveBeenCalledTimes(3);
  });

  it('only shows channels that are still approved', async () => {
    const fetchPage = pages({
      'UCa:': { videos: [video('a1', 'UCa', '2026-10-01')], nextPageToken: null },
      'UCb:': { videos: [video('b1', 'UCb', '2026-10-03')], nextPageToken: null },
    });
    const feed = createVideoFeed({ storage: memoryStorage(), fetchPage });
    await feed.load([A, B]);
    const result = await feed.load([A]);
    expect(result.videos.map((v) => v.id)).toEqual(['a1']);
  });
});
