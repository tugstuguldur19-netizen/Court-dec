# Kids Player

An Android YouTube player for children:

- **Only channels you approve.** The child can't search YouTube.
- **No Shorts and no live streams.** Only regular videos appear.
- **No hopping between videos.** Once a video starts, the child can't leave it
  until it has actually played for 1 minute. Paused time doesn't count. Closing
  and reopening the app brings back the same video.
- **Parent PIN** protects the settings. You can also use the PIN to end the
  1-minute lock early.

Design notes are in [DESIGN.md](DESIGN.md).

## Install on the phone

1. On the Android phone, open this repository's **Releases** page on GitHub.
   Open the newest "Kids Player build" and tap **kids-player.apk**.
2. Open the downloaded file. Android will ask you to allow installing apps from
   your browser. Allow it and tap **Install**.
3. Open **Kids Player**, choose a parent PIN, and follow the steps below.

A new APK is built automatically each time the code in `kids-youtube-player/`
changes (see `.github/workflows/kids-player-android.yml`).

## First-time setup (parent)

1. **Get a free YouTube API key** (about 5 minutes, easiest on a computer):
   1. Go to <https://console.cloud.google.com> and sign in.
   2. Create a project (any name).
   3. Open **APIs & Services → Library**, search **YouTube Data API v3** and
      press **Enable**.
   4. Open **APIs & Services → Credentials → Create credentials → API key**.
   5. Copy the key (it starts with `AIza`).
2. In the app's parent settings, paste the key and press **Save**.
3. Add channels. Paste a channel link (`https://www.youtube.com/@SomeChannel`)
   or type its handle (`@SomeChannel`). Tap the trash icon to remove one.
4. Tap **Done**. Your child now sees the videos.

To get back to the settings later, tap the lock icon at the top right and enter
your PIN. After 5 wrong PIN attempts, the PIN pad locks for 5 minutes.

## Keep your child inside the app

An app can't stop the Home button. Android can:

- **App pinning:** Settings → Security (or "Security & privacy → More") → App
  pinning → On. Open Kids Player, open Recent apps, tap the app's icon and
  choose **Pin**. Unpinning needs your phone's lock screen PIN.
- **Google Family Link** can also block or time-limit the real YouTube app.

## Development

```bash
npm install
npm run dev        # run in a browser at http://localhost:5173
npm test           # unit tests (Vitest)
npm run test:e2e   # full flow in Chromium with YouTube mocked; screenshots in e2e/screenshots/
npm run android:sync && (cd android && ./gradlew assembleDebug)   # APK; needs the Android SDK
```

The web app is plain JavaScript (Vite). Capacitor wraps it as an Android app.
`android/app/src/main/java/com/kidsplayer/app/GuardedWebViewClient.java` blocks
links that would leave the app.

## Known limits

- Some channels don't allow their videos to play inside other apps. Those
  videos show "This channel doesn't let its videos play in other apps".
- Playback inside the app depends on YouTube accepting the app as an embedder.
  The app identifies itself as `https://com.kidsplayer.app`, which is the usual
  fix for YouTube "Error 152/153". If those errors still appear, tell me.
- The APK is a debug build signed with a debug key. That's fine for
  installing on your own phones, but not for the Play Store.
