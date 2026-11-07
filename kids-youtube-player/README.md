# Curated

YouTube without Shorts, showing only the channels you approve.

- A YouTube-style feed, watch page and search, with videos only from your approved channels.
- No Shorts and no live streams: the app reads each channel's list of regular videos only.
- "Up next" and search never show anything outside your channels. If a link inside the
  player tries to open a video from another channel, the app switches back.
- Light and dark mode follow the phone's setting.

Design notes are in [DESIGN.md](DESIGN.md).

## iPhone and iPad

The iPhone version is a web app you add to the home screen. It opens full screen like a
normal app, with no App Store or Apple account needed.

1. On the iPhone, open **https://tugstuguldur19-netizen.github.io/Court-dec/** in **Safari**.
2. Tap the **Share** button, then **Add to Home Screen**, then **Add**.
3. Open **Curated** from the home screen. The Channels tab opens first: paste your
   YouTube API key (steps below), then add channels.

Each phone keeps its own channel list and key. The web app is rebuilt and republished
automatically whenever code in `kids-youtube-player/` changes
(`.github/workflows/curated-web.yml`). It is served from the repository's `gh-pages` branch.

## Android

Open this repository's **Releases** page on the phone, open the newest "Curated build" and
tap **curated.apk** to install it (`.github/workflows/kids-player-android.yml` builds it).
The Android app uses the same code as the web app.

## Get a free YouTube API key (about 5 minutes)

1. Go to <https://console.cloud.google.com> and sign in.
2. Create a project (any name).
3. Open **APIs & Services → Library**, search **YouTube Data API v3** and press **Enable**.
4. Open **APIs & Services → Credentials → Create credentials → API key**. Copy the key
   (it starts with `AIza`).
5. Recommended: open the key, set **Application restrictions → Websites** and add
   `https://tugstuguldur19-netizen.github.io/*`, and set **API restrictions** to
   *YouTube Data API v3*. Then nobody else can use your key from another site.
   (Leave application restrictions off if you also use the Android app with the same key.)

The key is stored only on your phone; it is never put in the code.

## Development

```bash
npm install
npm run dev        # run in a browser at http://localhost:5173
npm test           # unit tests (Vitest)
npm run test:e2e   # full flow in Chromium with YouTube mocked; screenshots in e2e/screenshots/
npm run android:sync && (cd android && ./gradlew assembleDebug)   # Android APK; needs the Android SDK
```

Plain JavaScript and Vite. Capacitor wraps the same build as the Android app;
`android/app/src/main/java/com/kidsplayer/app/GuardedWebViewClient.java` stops links
from leaving it.

## Known limits

- Search looks through the videos the app has loaded (the newest 50 per channel, more after
  "Show more videos"), so very old videos may not show up in search until loaded.
- Some channels don't allow their videos to play in other apps; those show a message.
- On iPhone, Safari may not start a video with sound until you tap play.
