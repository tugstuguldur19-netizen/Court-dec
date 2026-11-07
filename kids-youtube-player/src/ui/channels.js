import { h, icon } from '../dom.js';
import { bottomNav } from './nav.js';
import { parseChannelInput } from '../channel-input.js';
import { resolveChannel } from '../youtube-api.js';

/** Approved channels and the API key. */
export function renderChannels(root, app) {
  const { storage } = app;
  let channels = app.channels();

  const channelInput = h('input', {
    id: 'channel-input',
    class: 'field',
    type: 'text',
    autocomplete: 'off',
    autocapitalize: 'off',
    spellcheck: false,
    placeholder: 'Paste a channel link or @handle',
  });
  const addButton = h('button', { class: 'pill dark', type: 'submit' }, 'Add');
  const channelStatus = h('p', { class: 'field-status', role: 'status' });
  const list = h('ul', { class: 'channel-list' });

  const keyInput = h('input', {
    id: 'api-key',
    class: 'field mono',
    type: 'text',
    autocomplete: 'off',
    autocapitalize: 'off',
    spellcheck: false,
    placeholder: 'AIza…',
    value: storage.get('apiKey', ''),
  });
  const keyStatus = h('p', { class: 'field-status', role: 'status' });
  const keyState = h('span', { class: 'video-meta' });
  const keySection = h(
    'details',
    { class: 'settings-row', open: !storage.get('apiKey') },
    h(
      'summary',
      {},
      icon('key'),
      h('span', { class: 'settings-row-text' }, h('span', {}, 'YouTube API key'), keyState),
      icon('right'),
    ),
    h(
      'form',
      { class: 'row', onSubmit: saveKey },
      h('label', { class: 'visually-hidden', for: 'api-key' }, 'API key'),
      keyInput,
      h('button', { class: 'pill dark', type: 'submit' }, 'Save'),
    ),
    keyStatus,
    h(
      'ol',
      { class: 'help' },
      h('li', {}, 'On a computer, open console.cloud.google.com and sign in.'),
      h('li', {}, 'Create a project (any name).'),
      h('li', {}, 'APIs & Services → Library → enable “YouTube Data API v3”.'),
      h('li', {}, 'APIs & Services → Credentials → Create credentials → API key.'),
      h('li', {}, 'Copy the key (it starts with AIza) and paste it here.'),
    ),
  );

  root.append(
    h('header', { class: 'topbar' }, h('h1', { class: 'page-title' }, 'Channels')),
    h(
      'main',
      { class: 'channels' },
      h(
        'section',
        { class: 'add-channel' },
        h(
          'form',
          { class: 'row', onSubmit: addChannel },
          h('label', { class: 'visually-hidden', for: 'channel-input' }, 'Channel link or handle'),
          channelInput,
          addButton,
        ),
        channelStatus,
        h('p', { class: 'muted small' }, 'Only these channels appear in the app. Shorts and live streams are never shown.'),
      ),
      list,
      h('section', { class: 'settings' }, h('h2', { class: 'settings-title' }, 'Settings'), keySection),
    ),
    bottomNav(app, 'channels'),
  );

  renderKeyState();
  renderList();

  function setStatus(el, text, kind = '') {
    el.textContent = text;
    el.className = `field-status ${kind}`;
  }

  function renderKeyState() {
    const saved = Boolean(storage.get('apiKey'));
    keyState.textContent = saved ? 'Saved' : 'Needed to list videos';
    keyState.className = `video-meta ${saved ? 'ok' : 'error'}`;
  }

  function saveKey(event) {
    event.preventDefault();
    const key = keyInput.value.trim();
    storage.set('apiKey', key);
    setStatus(keyStatus, key ? 'Saved.' : 'Key removed.', 'ok');
    renderKeyState();
  }

  async function addChannel(event) {
    event.preventDefault();
    const apiKey = storage.get('apiKey', '');
    if (!apiKey) {
      keySection.open = true;
      return setStatus(channelStatus, 'Add your YouTube API key first (under Settings below).', 'error');
    }
    const ref = parseChannelInput(channelInput.value);
    if (!ref) return setStatus(channelStatus, 'Paste a channel link or @handle, for example @NASA.', 'error');
    addButton.disabled = true;
    setStatus(channelStatus, 'Looking up the channel…');
    try {
      const channel = await resolveChannel(apiKey, ref);
      if (channels.some((c) => c.id === channel.id)) {
        setStatus(channelStatus, `${channel.title} is already on the list.`);
      } else {
        channels = [...channels, { ...channel, handle: ref.type === 'handle' ? ref.value : '' }];
        storage.set('channels', channels);
        channelInput.value = '';
        setStatus(channelStatus, `Added ${channel.title}.`, 'ok');
        renderList();
      }
    } catch (error) {
      setStatus(channelStatus, error.message, 'error');
    } finally {
      addButton.disabled = false;
    }
  }

  function removeChannel(channel) {
    if (!window.confirm(`Remove ${channel.title}? Its videos will disappear from the app.`)) return;
    channels = channels.filter((c) => c.id !== channel.id);
    storage.set('channels', channels);
    app.feed.forget(channel.id);
    setStatus(channelStatus, `Removed ${channel.title}.`);
    renderList();
  }

  function renderList() {
    list.replaceChildren(
      ...channels.map((channel) =>
        h(
          'li',
          {},
          h('img', { class: 'avatar large', src: channel.thumbnail, alt: '', referrerPolicy: 'no-referrer' }),
          h(
            'button',
            {
              class: 'channel-link',
              type: 'button',
              onClick: () => app.go('home', { channel: channel.id }, { replace: true }),
            },
            h('span', { class: 'channel-name' }, channel.title),
            channel.handle && h('span', { class: 'video-meta' }, channel.handle),
          ),
          h(
            'button',
            { class: 'icon-button', type: 'button', 'aria-label': `Remove ${channel.title}`, onClick: () => removeChannel(channel) },
            icon('trash'),
          ),
        ),
      ),
    );
    if (!channels.length) list.append(h('li', { class: 'muted small empty-row' }, 'No channels yet. Add one above.'));
  }
}
