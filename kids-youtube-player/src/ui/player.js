import { h, icon } from '../dom.js';
import { WatchLock } from '../watch-lock.js';
import { loadIframeApi } from '../youtube-iframe-api.js';
import { openPinPad } from './pin-pad.js';

const TICK_MS = 250;
const RING = 2 * Math.PI * 20;

const ERROR_MESSAGES = {
  100: 'This video was removed or made private.',
  101: "This channel doesn't let its videos play in other apps.",
  150: "This channel doesn't let its videos play in other apps.",
};

/**
 * Plays one video. Leaving is blocked until the video has played for a
 * minute (or ends, or a parent unlocks with the PIN). The lock is saved so
 * closing and reopening the app comes back here.
 */
export function renderPlayer(root, app, { video, watchedSeconds = 0 }) {
  const lock = new WatchLock({ watchedSeconds });
  let playing = false;
  let player = null;
  let savedSecond = -1;

  const ringFill = svgCircle('ring-fill');
  const backLabel = h('span', { class: 'back-label' });
  const back = h(
    'button',
    { class: 'back-button', type: 'button', onClick: goBack },
    h('span', { class: 'ring', html: `<svg viewBox="0 0 48 48">${svgCircle('ring-track')}${ringFill}</svg>` }),
    icon('back'),
    backLabel,
  );
  const holder = h('div', { id: 'yt-player' });
  const overlay = h('div', { class: 'player-overlay', hidden: true });

  root.append(
    h(
      'header',
      { class: 'topbar player-bar' },
      back,
      h('button', { class: 'icon-button', type: 'button', 'aria-label': 'Parent unlock', onClick: parentUnlock }, icon('lock')),
    ),
    h(
      'main',
      { class: 'player' },
      h('div', { class: 'player-frame' }, holder, overlay),
      h('h1', { class: 'video-title' }, video.title),
      h('p', { class: 'video-channel' }, video.channelTitle),
    ),
  );

  app.onBack = goBack;
  const timer = setInterval(tick, TICK_MS);
  tick();

  loadIframeApi()
    .then((YT) => {
      player = new YT.Player(holder, {
        videoId: video.id,
        width: '100%',
        height: '100%',
        playerVars: {
          autoplay: 1,
          playsinline: 1,
          rel: 0,
          iv_load_policy: 3,
          fs: 1,
          origin: window.location.origin,
        },
        events: {
          onStateChange: (event) => onStateChange(YT, event),
          onError: (event) => fail(ERROR_MESSAGES[event.data] ?? "This video can't play right now."),
        },
      });
    })
    .catch((error) => fail(error.message));

  function onStateChange(YT, event) {
    playing = event.data === YT.PlayerState.PLAYING;
    // Suggestions inside YouTube's player can switch to another video; put ours back.
    const current = player?.getVideoData?.()?.video_id;
    if (playing && current && current !== video.id) {
      playing = false;
      player.loadVideoById(video.id);
      return;
    }
    if (event.data === YT.PlayerState.ENDED) {
      lock.finish();
      showOverlay('All done!', [
        h('button', { class: 'button', type: 'button', onClick: replay }, icon('replay'), 'Watch again'),
        h('button', { class: 'button primary', type: 'button', onClick: goBack }, 'Back to videos'),
      ]);
    }
    tick();
  }

  function tick() {
    lock.update(performance.now(), playing);
    const unlocked = lock.unlocked;
    back.disabled = !unlocked;
    back.setAttribute('aria-label', unlocked ? 'Back to videos' : `Back unlocks in ${lock.remainingSeconds} seconds`);
    backLabel.textContent = unlocked ? 'Back' : `${lock.remainingSeconds}s`;
    const progress = unlocked ? 1 : lock.watchedSeconds / lock.requiredSeconds;
    back.querySelector('.ring-fill').style.strokeDashoffset = String(RING * (1 - progress));
    back.classList.toggle('unlocked', unlocked);
    saveSession();
  }

  function saveSession() {
    if (lock.unlocked) {
      if (savedSecond !== Infinity) app.storage.remove('lockSession');
      savedSecond = Infinity;
      return;
    }
    const second = Math.floor(lock.watchedSeconds);
    if (second === savedSecond) return;
    savedSecond = second;
    app.storage.set('lockSession', { video, watchedSeconds: lock.watchedSeconds });
  }

  function fail(message) {
    lock.release();
    tick();
    showOverlay(message, [h('button', { class: 'button primary', type: 'button', onClick: goBack }, 'Back to videos')]);
  }

  function showOverlay(message, buttons) {
    overlay.replaceChildren(h('p', {}, message), h('div', { class: 'overlay-buttons' }, buttons));
    overlay.hidden = false;
  }

  function replay() {
    overlay.hidden = true;
    player.seekTo(0, true);
    player.playVideo();
  }

  function goBack() {
    if (lock.unlocked) app.go('home');
  }

  function parentUnlock() {
    openPinPad(app, {
      title: 'Parent PIN to unlock',
      onSubmit: async (pin) => {
        const result = await app.pinGate.attempt(pin);
        return result.ok || result.error;
      },
      onDone: () => {
        lock.release();
        tick();
      },
      onCancel: () => {},
    });
  }

  return () => {
    clearInterval(timer);
    player?.destroy?.();
  };
}

function svgCircle(cls) {
  return `<circle class="${cls}" cx="24" cy="24" r="20" stroke-dasharray="${RING}" />`;
}
