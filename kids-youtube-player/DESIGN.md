# Kids YouTube Player: design

An Android app that plays YouTube videos for a child, limited to channels a
parent has approved.

## Goals

- The child can only watch regular videos (no Shorts, no live streams) from
  channels the parent approved.
- Once a video starts, the child cannot leave it until it has actually played
  for 60 seconds. Paused time does not count. A video shorter than 60 seconds
  unlocks when it ends.
- The parent manages everything behind a PIN.
- Nothing inside the app leads out to YouTube, a browser or another video.

Out of scope: stopping the child from leaving the app with the Home button.
Android's screen pinning or Google Family Link covers that (see README).

## Stack

- Vanilla JavaScript + Vite, wrapped as an Android app with Capacitor 8.
- YouTube Data API v3 (the parent's own free key) for channel and video lists.
- YouTube IFrame Player API for playback.
- Vitest for unit tests, Playwright for an end-to-end test against the built
  app with the YouTube APIs mocked.
- GitHub Actions builds a debug APK.

## Screens

1. **PIN setup** (first launch): parent picks a 4–6 digit PIN, entered twice.
2. **Home** (child): grid of videos from all approved channels, newest first,
   with channel chips to filter, "Load more" at the bottom and a small lock
   button that opens the parent area after the PIN. No search.
3. **Player** (child): the video, a countdown ring on the Back button, and a
   small lock button so a parent can end the lock early with the PIN. When the
   video ends, an overlay with "Watch again" and "Back to videos" covers
   YouTube's end screen.
4. **Parent area**: API key, add a channel (by `@handle`, channel URL or `UC…`
   ID), see and remove channels, refresh videos, change PIN.

## Modules (`src/`)

| Module | Job |
| --- | --- |
| `storage.js` | JSON get/set over `localStorage`, namespaced keys |
| `pin.js` | Salted SHA-256 PIN hashing and verification |
| `pin-gate.js` | PIN checks with a 5-minute lockout after 5 wrong tries (survives restarts) |
| `channel-input.js` | Turns what the parent typed into `{type: 'handle'|'id'|'username', value}` |
| `youtube-api.js` | `resolveChannel`, `fetchUploads` (the channel's `UULF…` playlist, which YouTube keeps free of Shorts and lives) |
| `video-feed.js` | Merges channels' videos, caches each channel for 3 hours, pagination |
| `watch-lock.js` | Pure lock logic: counts playing time, unlocked state, remaining seconds |
| `back-button.js` | Android back button via `@capacitor/app` |
| `ui/*.js` | One file per screen plus the PIN pad. `ui/player.js` also saves the active lock (`lockSession`) so killing and reopening the app resumes the same video |

## Shorts filtering

Every channel `UC<id>` has a playlist `UULF<id>` that holds only its regular
long-form uploads, leaving out Shorts and live streams. The app reads only this
playlist. Private and deleted entries are dropped.

## Escape routes and how they are closed

- **YouTube logo/title links in the player:** `GuardedWebViewClient` (native,
  replaces Capacitor's default WebView client) refuses every top-level
  navigation that leaves the app and every non-http(s) link such as
  `intent://`, so nothing opens the YouTube app or a browser.
- **Suggested videos inside the player:** `rel=0` limits them to the same
  channel; on every `PLAYING` event the app checks the video ID and reloads the
  expected video if it changed; the end screen is covered by the app's own
  overlay.
- **Back button / gesture during the lock:** handled in JS and ignored.
- **Killing the app during the lock:** the lock session is saved; on reopen the
  same video comes back with the remaining time.

## Embedding inside an app

YouTube may refuse to play embeds that lack an identifying Referer (errors
152/153). The app is served from `https://com.kidsplayer.app/` (Capacitor
`server.hostname`), so YouTube sees the app's ID as the referrer, and the
player is given that `origin`. This must be confirmed on a real device.

## Error handling

- No API key or no channels: the home screen tells the child to ask a parent.
- API errors (bad key, quota, network): shown on the home screen; cached videos
  are used when present.
- Player errors: the overlay offers "Back to videos" and the lock is released.

## API quota

`playlistItems.list` and `channels.list` cost 1 unit each, so a 10,000-unit
daily quota covers thousands of refreshes. Channel lists are cached 3 hours.
