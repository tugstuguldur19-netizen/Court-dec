export const CACHE_TTL_MS = 3 * 60 * 60 * 1000;

/**
 * The child's video list: every approved channel's regular uploads merged
 * newest first. Each channel's pages are cached in storage under
 * `videos:<channelId>` so the API quota lasts and the list works offline.
 *
 * `fetchPage(channelId, pageToken)` returns `{videos, nextPageToken}`.
 */
export function createVideoFeed({ storage, fetchPage, now = Date.now, ttlMs = CACHE_TTL_MS }) {
  const cacheKey = (channelId) => `videos:${channelId}`;

  async function refresh(channel, force, errors) {
    const cached = storage.get(cacheKey(channel.id));
    if (cached && !force && now() - cached.fetchedAt < ttlMs) return;
    try {
      const page = await fetchPage(channel.id);
      storage.set(cacheKey(channel.id), { fetchedAt: now(), ...page });
    } catch (error) {
      errors.push(error.message);
    }
  }

  async function nextPage(channel, errors) {
    const cached = storage.get(cacheKey(channel.id));
    if (!cached?.nextPageToken) return;
    try {
      const page = await fetchPage(channel.id, cached.nextPageToken);
      storage.set(cacheKey(channel.id), {
        ...cached,
        videos: [...cached.videos, ...page.videos],
        nextPageToken: page.nextPageToken,
      });
    } catch (error) {
      errors.push(error.message);
    }
  }

  function collect(channels, errors) {
    const seen = new Set();
    const videos = [];
    let hasMore = false;
    for (const channel of channels) {
      const cached = storage.get(cacheKey(channel.id));
      if (!cached) continue;
      if (cached.nextPageToken) hasMore = true;
      for (const v of cached.videos) {
        if (!seen.has(v.id)) {
          seen.add(v.id);
          videos.push(v);
        }
      }
    }
    videos.sort((a, b) => (a.publishedAt < b.publishedAt ? 1 : a.publishedAt > b.publishedAt ? -1 : 0));
    return { videos, hasMore, errors: [...new Set(errors)] };
  }

  return {
    async load(channels, { force = false } = {}) {
      const errors = [];
      await Promise.all(channels.map((c) => refresh(c, force, errors)));
      return collect(channels, errors);
    },
    async loadMore(channels) {
      const errors = [];
      await Promise.all(channels.map((c) => nextPage(c, errors)));
      return collect(channels, errors);
    },
    forget(channelId) {
      storage.remove(cacheKey(channelId));
    },
  };
}
