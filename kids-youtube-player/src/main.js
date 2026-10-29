import './styles.css';
import { createStorage } from './storage.js';
import { createVideoFeed } from './video-feed.js';
import { fetchUploads } from './youtube-api.js';
import { createPinGate } from './pin-gate.js';
import { initBackButton } from './back-button.js';
import { renderSetup } from './ui/setup.js';
import { renderHome } from './ui/home.js';
import { renderPlayer } from './ui/player.js';
import { renderParent } from './ui/parent.js';

const SCREENS = { setup: renderSetup, home: renderHome, player: renderPlayer, parent: renderParent };

const root = document.getElementById('app');
const storage = createStorage();
const backStack = [];
let cleanup = null;

const app = {
  storage,
  pinGate: createPinGate({ storage }),
  feed: createVideoFeed({
    storage,
    fetchPage: (channelId, pageToken) => fetchUploads(storage.get('apiKey', ''), channelId, pageToken),
  }),
  homeFilter: 'all',
  onBack: null,

  go(screen, params = {}) {
    cleanup?.();
    app.onBack = null;
    root.replaceChildren();
    root.dataset.screen = screen;
    window.scrollTo(0, 0);
    cleanup = SCREENS[screen](root, app, params) ?? null;
  },

  // Overlays (the PIN pad) take the back button while they are open.
  pushBack(handler) {
    backStack.push(handler);
  },
  popBack(handler) {
    const index = backStack.lastIndexOf(handler);
    if (index !== -1) backStack.splice(index, 1);
  },
};

initBackButton(() => (backStack.length ? backStack.at(-1)() : app.onBack?.()));

const session = storage.get('lockSession');
if (!storage.get('pin')) app.go('setup');
else if (session?.video) app.go('player', session);
else app.go('home');
