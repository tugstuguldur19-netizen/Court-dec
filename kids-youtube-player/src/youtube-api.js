const BASE = 'https://www.googleapis.com/youtube/v3';
const HIDDEN_TITLES = new Set(['Private video', 'Deleted video']);

export class YouTubeApiError extends Error {
  constructor(message, { status = 0, reason = '' } = {}) {
    super(message);
    this.name = 'YouTubeApiError';
    this.status = status;
    this.reason = reason;
  }
}

/**
 * Every channel UC<x> has a playlist UULF<x> with only its regular uploads:
 * YouTube leaves Shorts and live streams out of it.
 */
export function longFormPlaylistId(channelId) {
  return `UULF${channelId.slice(2)}`;
}

const LOOKUP_PARAM = { handle: 'forHandle', id: 'id', username: 'forUsername' };

/** Looks up a channel from parseChannelInput() output. */
export async function resolveChannel(apiKey, ref, fetchImpl = fetch) {
  const data = await get('channels', { part: 'snippet', [LOOKUP_PARAM[ref.type]]: ref.value }, apiKey, fetchImpl);
  const item = data.items?.[0];
  if (!item) throw new YouTubeApiError("Couldn't find that channel. Check the @handle or link.");
  const thumbs = item.snippet.thumbnails ?? {};
  return {
    id: item.id,
    title: item.snippet.title,
    thumbnail: (thumbs.medium ?? thumbs.default ?? {}).url ?? '',
  };
}

/** One page (up to 50) of a channel's regular videos, newest first. */
export async function fetchUploads(apiKey, channelId, pageToken, fetchImpl = fetch) {
  const params = { part: 'snippet,contentDetails', playlistId: longFormPlaylistId(channelId), maxResults: 50 };
  if (pageToken) params.pageToken = pageToken;
  let data;
  try {
    data = await get('playlistItems', params, apiKey, fetchImpl);
  } catch (error) {
    if (error.status === 404) return { videos: [], nextPageToken: null };
    throw error;
  }
  const videos = (data.items ?? []).filter(isWatchable).map(toVideo);
  return { videos, nextPageToken: data.nextPageToken ?? null };
}

function isWatchable(item) {
  const s = item.snippet;
  return Boolean(s?.videoOwnerChannelId && s.resourceId?.videoId) && !HIDDEN_TITLES.has(s.title);
}

function toVideo(item) {
  const s = item.snippet;
  const thumbs = s.thumbnails ?? {};
  return {
    id: s.resourceId.videoId,
    title: s.title,
    channelId: s.videoOwnerChannelId,
    channelTitle: s.videoOwnerChannelTitle ?? '',
    publishedAt: item.contentDetails?.videoPublishedAt ?? s.publishedAt ?? '',
    thumbnail: (thumbs.medium ?? thumbs.high ?? thumbs.default ?? {}).url ?? '',
  };
}

async function get(resource, params, apiKey, fetchImpl) {
  const url = new URL(`${BASE}/${resource}`);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  url.searchParams.set('key', apiKey);

  let response;
  try {
    response = await fetchImpl(url.toString());
  } catch {
    throw new YouTubeApiError('No internet connection. Check Wi-Fi and try again.');
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw toApiError(response.status, body.error);
  return body;
}

function toApiError(status, error = {}) {
  const reason = error.errors?.[0]?.reason ?? '';
  const message = error.message ?? '';
  if (/API key not valid/i.test(message) || reason === 'keyInvalid') {
    return new YouTubeApiError('The YouTube API key is not valid. A parent needs to check it.', { status, reason });
  }
  if (reason === 'quotaExceeded' || reason === 'dailyLimitExceeded') {
    return new YouTubeApiError("Today's daily YouTube limit is used up. Try again tomorrow.", { status, reason });
  }
  if (status === 403) {
    return new YouTubeApiError(
      'YouTube refused the request. Make sure "YouTube Data API v3" is enabled for this key.',
      { status, reason },
    );
  }
  return new YouTubeApiError(message || `YouTube error (${status})`, { status, reason });
}
