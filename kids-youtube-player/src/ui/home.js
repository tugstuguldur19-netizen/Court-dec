import { h, icon } from '../dom.js';
import { bottomNav, logo } from './nav.js';
import { videoCard } from './video-card.js';

/** The feed: every approved channel's regular videos, newest first. */
export function renderHome(root, app, { channel = 'all' }) {
  const channels = app.channels();
  if (channel !== 'all' && !channels.some((c) => c.id === channel)) channel = 'all';

  const list = h('ul', { class: 'feed' });
  const status = h('p', { class: 'status', role: 'status' });
  const more = h('button', { class: 'pill more', type: 'button', hidden: true, onClick: loadMore }, 'Show more videos');

  const header = h(
    'header',
    { class: 'topbar' },
    logo(),
    h('button', { class: 'icon-button', type: 'button', 'aria-label': 'Search', onClick: () => app.go('search') }, icon('search')),
  );
  root.append(header);
  if (channels.length > 1) root.append(chips());
  root.append(h('main', { class: 'home' }, status, list, more), bottomNav(app, 'home'));

  if (!app.storage.get('apiKey') || !channels.length) {
    status.replaceWith(
      h(
        'div',
        { class: 'empty' },
        h('p', {}, 'No channels yet'),
        h('p', { class: 'muted' }, 'Add the YouTube channels you want to see. Only their regular videos will show up here.'),
        h('button', { class: 'pill primary', type: 'button', onClick: () => app.go('channels', {}, { replace: true }) }, 'Add channels'),
      ),
    );
    return;
  }

  status.textContent = 'Loading…';
  app.loadFeed().then(show);

  async function loadMore() {
    more.disabled = true;
    show(await app.loadMore());
  }

  function show(result) {
    const videos = channel === 'all' ? result.videos : result.videos.filter((v) => v.channelId === channel);
    list.replaceChildren(...videos.map((v) => videoCard(app, v)));
    more.hidden = !result.hasMore;
    more.disabled = false;
    status.classList.toggle('error', result.errors.length > 0);
    status.textContent = result.errors[0] ?? (videos.length ? '' : 'No videos yet.');
  }

  function chips() {
    const chip = (id, label) =>
      h(
        'button',
        {
          class: 'chip',
          type: 'button',
          'aria-pressed': String(channel === id),
          onClick: () => app.go('home', { channel: id }, { replace: true }),
        },
        h('span', {}, label),
      );
    return h(
      'nav',
      { class: 'chips', 'aria-label': 'Filter by channel' },
      chip('all', 'All'),
      ...channels.map((c) => chip(c.id, c.title)),
    );
  }
}
