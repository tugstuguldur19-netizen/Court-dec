# Curated: design

A YouTube-style player that shows regular videos (no Shorts, no live streams) from
channels the user approves, and nothing else. Runs as a home-screen web app on
iPhone (GitHub Pages) and as an Android app (Capacitor) from the same code.

## Screens

1. **Home**: the feed, newest first across approved channels, channel chips to filter,
   "Show more videos" at the end, bottom tabs Home and Channels.
2. **Watch**: the player (sticky at the top), title, views and age, the channel, and "Up next"
   (same channel first, then the rest). When a video ends, the app's own overlay offers
   Replay or Play next.
3. **Search**: matches words in titles and channel names among loaded videos.
4. **Channels**: add by `@handle`, channel URL or `UC…` ID; remove; the API key.

Screens are browser-history entries (`history.pushState`), so the browser back gesture,
Android's back button and reloads all work.

## Modules (`src/`)

| Module | Job |
| --- | --- |
| `storage.js` | JSON get/set over `localStorage`, namespaced keys |
| `channel-input.js` | Turns what the user typed into a channel reference |
| `youtube-api.js` | `resolveChannel`, `fetchUploads` (the channel's `UULF…` playlist), `fetchVideoDetails` (length, views), `fetchUploadsWithDetails` |
| `video-feed.js` | Merges channels' videos, caches each channel for 3 hours (`videos2:<id>`), pagination |
| `format.js` | `formatDuration`, `formatViews`, `timeAgo` |
| `youtube-iframe-api.js` | Loads the IFrame Player API once |
| `back-button.js` | Android back button via `@capacitor/app` |
| `ui/*.js` | One file per screen, plus `video-card.js` and `nav.js` |

## Keeping to approved channels

- **No Shorts:** every channel `UC<id>` has a playlist `UULF<id>` holding only regular
  uploads (no Shorts, no lives). The app reads only that playlist.
- **Inside the player:** `rel=0` limits YouTube's suggestions to the same channel. On every
  `PLAYING` event the app checks the video ID: a video from the loaded approved feed is
  opened normally; anything else is swapped back to the expected video.
- **End screen:** covered by the app's own Replay / Play next overlay.
- **Android:** `GuardedWebViewClient` refuses navigations that would leave the app.

## Quota

`playlistItems.list`, `videos.list` and `channels.list` cost 1 unit each, so one channel
refresh costs 2 units; a 10,000-unit daily quota is plenty. Lists are cached 3 hours.
