import { h, icon } from '../dom.js';
import { openPinPad } from './pin-pad.js';
import { minimizeApp } from '../back-button.js';

/** The child's screen: approved videos, newest first, filterable by channel. */
export function renderHome(root, app) {
  const channels = app.storage.get('channels', []);
  const hasKey = Boolean(app.storage.get('apiKey'));
  let videos = [];
  let filter = app.homeFilter ?? 'all';
  if (filter !== 'all' && !channels.some((c) => c.id === filter)) filter = 'all';

  const chips = h('nav', { class: 'chips', 'aria-label': 'Channels' });
  const grid = h('ul', { class: 'grid' });
  const status = h('p', { class: 'status', role: 'status' });
  const more = h('button', { class: 'button more', type: 'button', hidden: true, onClick: loadMore }, 'Load more videos');

  root.append(
    h(
      'header',
      { class: 'topbar' },
      h('h1', { class: 'brand' }, h('span', { class: 'brand-mark' }, icon('play')), 'My Videos'),
      h('button', { class: 'icon-button', type: 'button', 'aria-label': 'Parent settings', onClick: openParent }, icon('lock')),
    ),
    h('main', { class: 'home' }, chips, status, grid, more),
  );

  app.onBack = minimizeApp;

  if (!hasKey || channels.length === 0) {
    status.textContent = 'No videos yet. Ask a grown-up to add some channels.';
    status.classList.add('empty');
    return;
  }

  renderChips();
  status.textContent = 'Loading videos…';
  app.feed.load(channels).then(show);

  function show(result) {
    videos = result.videos;
    more.hidden = !result.hasMore;
    more.disabled = false;
    renderGrid(result.errors);
  }

  async function loadMore() {
    more.disabled = true;
    show(await app.feed.loadMore(channels));
  }

  function renderChips() {
    const chip = (id, label, thumb) =>
      h(
        'button',
        {
          class: 'chip',
          type: 'button',
          'aria-pressed': String(filter === id),
          onClick: () => {
            filter = app.homeFilter = id;
            renderChips();
            renderGrid([]);
          },
        },
        thumb && h('img', { src: thumb, alt: '', loading: 'lazy', referrerPolicy: 'no-referrer' }),
        label,
      );
    chips.hidden = channels.length < 2;
    chips.replaceChildren(chip('all', 'All'), ...channels.map((c) => chip(c.id, c.title, c.thumbnail)));
  }

  function renderGrid(errors) {
    const shown = filter === 'all' ? videos : videos.filter((v) => v.channelId === filter);
    grid.replaceChildren(...shown.map(card));
    status.classList.toggle('error', errors.length > 0);
    status.classList.remove('empty');
    if (errors.length) status.textContent = errors[0];
    else if (!shown.length) status.textContent = 'No videos here yet.';
    else status.textContent = '';
  }

  function card(video) {
    return h(
      'li',
      {},
      h(
        'button',
        { class: 'card', type: 'button', onClick: () => app.go('player', { video }) },
        h(
          'span',
          { class: 'thumb' },
          h('img', { src: video.thumbnail, alt: '', loading: 'lazy', referrerPolicy: 'no-referrer' }),
        ),
        h('span', { class: 'card-title' }, video.title),
        h('span', { class: 'card-channel' }, video.channelTitle),
      ),
    );
  }

  function openParent() {
    openPinPad(app, {
      title: 'Parent PIN',
      onSubmit: async (pin) => {
        const result = await app.pinGate.attempt(pin);
        return result.ok || result.error;
      },
      onDone: () => app.go('parent'),
      onCancel: () => {},
    });
  }
}
