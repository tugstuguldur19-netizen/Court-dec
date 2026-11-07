import { h, icon } from '../dom.js';
import { compactCard } from './video-card.js';

/**
 * Searches the titles of videos already loaded from approved channels.
 * Nothing outside those channels can ever appear.
 */
export function renderSearch(root, app, { q = '' }) {
  const input = h('input', {
    id: 'search-input',
    class: 'search-input',
    type: 'search',
    enterKeyHint: 'search',
    autocomplete: 'off',
    placeholder: 'Search your channels',
    value: q,
    onInput: update,
  });
  const clear = h(
    'button',
    {
      class: 'icon-button small',
      type: 'button',
      'aria-label': 'Clear search',
      onClick: () => {
        input.value = '';
        update();
        input.focus();
      },
    },
    icon('close'),
  );
  const hint = h('p', { class: 'search-hint' });
  const list = h('ul', { class: 'compact-list' });
  let videos = [];

  root.append(
    h(
      'header',
      { class: 'topbar search-bar' },
      h('button', { class: 'icon-button', type: 'button', 'aria-label': 'Back', onClick: () => app.back() }, icon('back')),
      h(
        'form',
        { class: 'search-field', role: 'search', onSubmit: (e) => (e.preventDefault(), input.blur()) },
        h('label', { class: 'visually-hidden', for: 'search-input' }, 'Search your channels'),
        input,
        clear,
      ),
    ),
    h('main', { class: 'search' }, hint, list),
  );

  const count = app.channels().length;
  hint.textContent = `Showing results from your ${count} approved channel${count === 1 ? '' : 's'} only`;
  app.loadFeed().then((result) => {
    videos = result.videos;
    update();
  });
  queueMicrotask(() => input.focus());

  function update() {
    const query = input.value.trim();
    clear.hidden = !query;
    app.setParams({ q: query });
    const words = query.toLowerCase().split(/\s+/).filter(Boolean);
    if (!words.length) return list.replaceChildren();
    const matches = videos.filter((v) => {
      const text = `${v.title} ${v.channelTitle}`.toLowerCase();
      return words.every((w) => text.includes(w));
    });
    list.replaceChildren(
      ...(matches.length ? matches.map((v) => compactCard(app, v)) : [h('li', { class: 'status' }, `No videos match "${query}".`)]),
    );
  }
}
