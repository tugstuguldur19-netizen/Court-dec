const CHANNEL_ID = /^UC[\w-]{22}$/;
const HANDLE = /^@[^\s/?#@]+$/;
const YOUTUBE_HOSTS = new Set(['youtube.com', 'www.youtube.com', 'm.youtube.com']);

/**
 * Turns what a parent typed or pasted into a channel reference the API can
 * look up. Returns null when it is not a channel (a video link, /c/ custom
 * URL, another site...).
 */
export function parseChannelInput(text) {
  const input = text.trim();
  if (!input) return null;
  if (CHANNEL_ID.test(input)) return { type: 'id', value: input };
  if (HANDLE.test(input)) return { type: 'handle', value: input };

  const url = toUrl(input);
  if (url) return parseChannelUrl(url);

  // A bare word like "CoComelon" is most likely a handle without the @.
  if (/^[^\s/?#@.:]+$/.test(input)) return { type: 'handle', value: `@${input}` };
  return null;
}

function toUrl(input) {
  if (!/youtube\.com/i.test(input) && !/^https?:/i.test(input)) return null;
  try {
    return new URL(/^https?:/i.test(input) ? input : `https://${input}`);
  } catch {
    return null;
  }
}

function parseChannelUrl(url) {
  if (!YOUTUBE_HOSTS.has(url.hostname.toLowerCase())) return null;
  const [first, second] = url.pathname.split('/').filter(Boolean).map(decodeURIComponent);
  if (!first) return null;
  if (HANDLE.test(first)) return { type: 'handle', value: first };
  if (first === 'channel' && second && CHANNEL_ID.test(second)) return { type: 'id', value: second };
  if (first === 'user' && second) return { type: 'username', value: second };
  return null;
}
