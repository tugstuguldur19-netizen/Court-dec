import './styles.css';
import { createStorage } from './storage.js';
import { createVideoFeed } from './video-feed.js';
import { fetchUploadsWithDetails } from './youtube-api.js';
import { initBackButton, minimizeApp } from './back-button.js';
import { renderHome } from './ui/home.js';
import { renderWatch } from './ui/watch.js';
import { renderSearch } from './ui/search.js';
import { renderChannels } from './ui/channels.js';

const SCREENS = { home: renderHome, watch: renderWatch, search: renderSearch, channels: renderChannels };

const root = document.getElementById('app');
const storage = createStorage();
let cleanup = null;
let feedResult = null;

const app = {
  storage,
  feed: createVideoFeed({
    storage,
    fetchPage: (channelId, pageToken) => fetchUploadsWithDetails(storage.get('apiKey', ''), channelId, pageToken),
  }),

  channels: () => storage.get('channels', []),
  channelThumb: (channelId) => app.channels().find((c) => c.id === channelId)?.thumbnail ?? '',

  async loadFeed(options) {
    feedResult = await app.feed.load(app.channels(), options);
    return feedResult;
  },
  async loadMore() {
    feedResult = await app.feed.loadMore(app.channels());
    return feedResult;
  },
  findVideo: (id) => feedResult?.videos.find((v) => v.id === id) ?? null,

  // Screens live in browser history, so the browser's back (and Android's
  // back button) step back through them.
  go(screen, params = {}, { replace = false } = {}) {
    const depth = (history.state?.depth ?? 0) + (replace ? 0 : 1);
    const state = { screen, params, depth };
    if (replace) history.replaceState(state, '');
    else history.pushState(state, '');
    render(state);
  },
  back() {
    if ((history.state?.depth ?? 0) > 0) history.back();
    else app.go('home', {}, { replace: true });
  },
  /** Updates the current screen's saved params without re-rendering. */
  setParams(params) {
    history.replaceState({ ...history.state, params: { ...history.state?.params, ...params } }, '');
  },
};

function render(state) {
  cleanup?.();
  root.replaceChildren();
  root.dataset.screen = state.screen;
  window.scrollTo(0, 0);
  cleanup = (SCREENS[state.screen] ?? renderHome)(root, app, state.params ?? {}) ?? null;
}

window.addEventListener('popstate', (event) => render(event.state ?? { screen: 'home', params: {}, depth: 0 }));
initBackButton(() => (history.state?.screen === 'home' ? minimizeApp() : app.back()));

if (history.state?.screen) render(history.state);
else app.go(storage.get('apiKey') && app.channels().length ? 'home' : 'channels', {}, { replace: true });
