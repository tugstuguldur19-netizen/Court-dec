import { describe, it, expect, vi } from 'vitest';
import { resolveChannel, fetchUploads, longFormPlaylistId, YouTubeApiError } from '../src/youtube-api.js';

const ID = 'UCbCmjCuTUZos6Inko4u57UQ';

function jsonResponse(body, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) });
}

function apiError(status, reason, message = 'error') {
  return jsonResponse({ error: { code: status, message, errors: [{ reason }] } }, status);
}

const channelItem = {
  id: ID,
  snippet: {
    title: 'CoComelon',
    thumbnails: { default: { url: 'https://yt3.ggpht.com/d' }, medium: { url: 'https://yt3.ggpht.com/m' } },
  },
};

function playlistItem(videoId, title, extra = {}) {
  return {
    snippet: {
      title,
      videoOwnerChannelId: ID,
      videoOwnerChannelTitle: 'CoComelon',
      resourceId: { kind: 'youtube#video', videoId },
      thumbnails: { medium: { url: `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg` } },
      ...extra,
    },
    contentDetails: { videoId, videoPublishedAt: '2026-10-01T10:00:00Z' },
  };
}

describe('longFormPlaylistId', () => {
  it('maps a channel to its Shorts-free uploads playlist', () => {
    expect(longFormPlaylistId(ID)).toBe('UULFbCmjCuTUZos6Inko4u57UQ');
  });
});

describe('resolveChannel', () => {
  it('looks a handle up with forHandle', async () => {
    const fetchImpl = vi.fn(() => jsonResponse({ items: [channelItem] }));
    const channel = await resolveChannel('KEY', { type: 'handle', value: '@CoComelon' }, fetchImpl);
    const url = new URL(fetchImpl.mock.calls[0][0]);
    expect(url.pathname).toBe('/youtube/v3/channels');
    expect(url.searchParams.get('forHandle')).toBe('@CoComelon');
    expect(url.searchParams.get('key')).toBe('KEY');
    expect(channel).toEqual({ id: ID, title: 'CoComelon', thumbnail: 'https://yt3.ggpht.com/m' });
  });

  it('uses id and forUsername for the other kinds', async () => {
    const fetchImpl = vi.fn(() => jsonResponse({ items: [channelItem] }));
    await resolveChannel('KEY', { type: 'id', value: ID }, fetchImpl);
    await resolveChannel('KEY', { type: 'username', value: 'cocomelon' }, fetchImpl);
    expect(new URL(fetchImpl.mock.calls[0][0]).searchParams.get('id')).toBe(ID);
    expect(new URL(fetchImpl.mock.calls[1][0]).searchParams.get('forUsername')).toBe('cocomelon');
  });

  it('throws a friendly error when nothing matches', async () => {
    const fetchImpl = () => jsonResponse({ items: [] });
    await expect(resolveChannel('KEY', { type: 'handle', value: '@nope' }, fetchImpl)).rejects.toThrow(
      "Couldn't find that channel",
    );
  });

  it('explains a bad API key', async () => {
    const fetchImpl = () => apiError(400, 'badRequest', 'API key not valid. Please pass a valid API key.');
    await expect(resolveChannel('BAD', { type: 'id', value: ID }, fetchImpl)).rejects.toThrow(
      'The YouTube API key is not valid',
    );
  });

  it('explains a used-up quota', async () => {
    const fetchImpl = () => apiError(403, 'quotaExceeded');
    const error = await resolveChannel('KEY', { type: 'id', value: ID }, fetchImpl).catch((e) => e);
    expect(error).toBeInstanceOf(YouTubeApiError);
    expect(error.message).toMatch(/daily YouTube limit/);
  });

  it('explains a network failure', async () => {
    const fetchImpl = () => Promise.reject(new TypeError('Failed to fetch'));
    await expect(resolveChannel('KEY', { type: 'id', value: ID }, fetchImpl)).rejects.toThrow(/internet/);
  });
});

describe('fetchUploads', () => {
  it('reads only the long-form playlist and maps videos', async () => {
    const fetchImpl = vi.fn(() =>
      jsonResponse({ items: [playlistItem('vid00000001', 'Wheels on the Bus')], nextPageToken: 'NEXT' }),
    );
    const page = await fetchUploads('KEY', ID, undefined, fetchImpl);
    const url = new URL(fetchImpl.mock.calls[0][0]);
    expect(url.pathname).toBe('/youtube/v3/playlistItems');
    expect(url.searchParams.get('playlistId')).toBe('UULFbCmjCuTUZos6Inko4u57UQ');
    expect(url.searchParams.get('maxResults')).toBe('50');
    expect(url.searchParams.has('pageToken')).toBe(false);
    expect(page).toEqual({
      nextPageToken: 'NEXT',
      videos: [
        {
          id: 'vid00000001',
          title: 'Wheels on the Bus',
          channelId: ID,
          channelTitle: 'CoComelon',
          publishedAt: '2026-10-01T10:00:00Z',
          thumbnail: 'https://i.ytimg.com/vi/vid00000001/mqdefault.jpg',
        },
      ],
    });
  });

  it('passes the page token and drops private and deleted videos', async () => {
    const privateItem = playlistItem('vid00000002', 'Private video', { videoOwnerChannelId: undefined });
    const fetchImpl = vi.fn(() =>
      jsonResponse({ items: [privateItem, playlistItem('vid00000003', 'Deleted video'), playlistItem('vid00000004', 'Ok')] }),
    );
    const page = await fetchUploads('KEY', ID, 'TOKEN', fetchImpl);
    expect(new URL(fetchImpl.mock.calls[0][0]).searchParams.get('pageToken')).toBe('TOKEN');
    expect(page.videos.map((v) => v.id)).toEqual(['vid00000004']);
    expect(page.nextPageToken).toBeNull();
  });

  it('treats a channel without regular videos as empty', async () => {
    const fetchImpl = () => apiError(404, 'playlistNotFound');
    expect(await fetchUploads('KEY', ID, undefined, fetchImpl)).toEqual({ videos: [], nextPageToken: null });
  });
});
