import { h, icon } from '../dom.js';
import { openPinPad } from './pin-pad.js';
import { parseChannelInput } from '../channel-input.js';
import { resolveChannel } from '../youtube-api.js';
import { createPinRecord } from '../pin.js';

/** Parent settings: API key, approved channels, refresh, PIN. */
export function renderParent(root, app) {
  const { storage } = app;
  let channels = storage.get('channels', []);

  const keyInput = h('input', {
    id: 'api-key',
    class: 'input mono',
    type: 'text',
    autocomplete: 'off',
    spellcheck: false,
    placeholder: 'AIza…',
    value: storage.get('apiKey', ''),
  });
  const keyStatus = h('p', { class: 'field-status', role: 'status' });

  const channelInput = h('input', {
    id: 'channel-input',
    class: 'input',
    type: 'text',
    autocomplete: 'off',
    spellcheck: false,
    placeholder: '@channelhandle or channel link',
  });
  const addButton = h('button', { class: 'button primary', type: 'submit' }, 'Add');
  const channelStatus = h('p', { class: 'field-status', role: 'status' });
  const channelList = h('ul', { class: 'channel-list' });
  const refreshStatus = h('p', { class: 'field-status', role: 'status' });
  const pinStatus = h('p', { class: 'field-status', role: 'status' });

  root.append(
    h(
      'header',
      { class: 'topbar' },
      h('h1', { class: 'page-title' }, 'Parent settings'),
      h('button', { class: 'button primary', type: 'button', onClick: done }, 'Done'),
    ),
    h(
      'main',
      { class: 'parent' },
      ...(storage.get('apiKey') ? [channelSection(), keySection()] : [keySection(), channelSection()]),
      section(
        'Videos',
        'Video lists refresh by themselves every 3 hours.',
        h('button', { class: 'button', type: 'button', onClick: refresh }, icon('refresh'), 'Refresh videos now'),
        refreshStatus,
      ),
      section(
        'Parent PIN',
        '',
        h('button', { class: 'button', type: 'button', onClick: changePin }, icon('lock'), 'Change PIN'),
        pinStatus,
      ),
      section(
        'Keep your child in this app',
        '',
        h(
          'p',
          { class: 'hint' },
          'Turn on Android "App pinning": Settings → Security → App pinning. Then open Recent apps, tap this app’s icon and choose Pin. ' +
            'Your child cannot leave the app until you unpin it. Google Family Link can also block the real YouTube app.',
        ),
      ),
    ),
  );

  app.onBack = done;
  renderChannels();

  function channelSection() {
    return section(
      'Approved channels',
      'Only regular videos from these channels appear. Shorts and live streams never show.',
      h(
        'form',
        { class: 'row', onSubmit: addChannel },
        h('label', { class: 'visually-hidden', for: 'channel-input' }, 'Channel'),
        channelInput,
        addButton,
      ),
      channelStatus,
      channelList,
    );
  }

  function keySection() {
    return section(
      'YouTube API key',
      'The app needs your own free key to list videos.',
      h(
        'form',
        { class: 'row', onSubmit: saveKey },
        h('label', { class: 'visually-hidden', for: 'api-key' }, 'API key'),
        keyInput,
        h('button', { class: 'button', type: 'submit' }, 'Save'),
      ),
      keyStatus,
      h(
        'details',
        { class: 'help' },
        h('summary', {}, 'How to get a free key (5 minutes)'),
        h(
          'ol',
          {},
          h('li', {}, 'On a computer, open console.cloud.google.com and sign in with a Google account.'),
          h('li', {}, 'Create a project (any name).'),
          h('li', {}, 'Go to "APIs & Services" → "Library", search "YouTube Data API v3" and press Enable.'),
          h('li', {}, 'Go to "APIs & Services" → "Credentials" → "Create credentials" → "API key".'),
          h('li', {}, 'Copy the key (starts with AIza) and paste it here.'),
        ),
      ),
    );
  }

  function section(title, intro, ...content) {
    return h('section', { class: 'card-section' }, h('h2', {}, title), intro && h('p', { class: 'hint' }, intro), ...content);
  }

  function setStatus(el, text, kind = '') {
    el.textContent = text;
    el.className = `field-status ${kind}`;
  }

  function saveKey(event) {
    event.preventDefault();
    const key = keyInput.value.trim();
    storage.set('apiKey', key);
    setStatus(keyStatus, key ? 'Saved.' : 'Key removed.', 'ok');
  }

  async function addChannel(event) {
    event.preventDefault();
    const apiKey = storage.get('apiKey', '');
    if (!apiKey) return setStatus(channelStatus, 'Save your YouTube API key first.', 'error');
    const ref = parseChannelInput(channelInput.value);
    if (!ref) {
      return setStatus(channelStatus, 'Paste a channel link or @handle, for example @PeppaPigOfficial.', 'error');
    }
    addButton.disabled = true;
    setStatus(channelStatus, 'Looking up the channel…');
    try {
      const channel = await resolveChannel(apiKey, ref);
      if (channels.some((c) => c.id === channel.id)) {
        setStatus(channelStatus, `${channel.title} is already on the list.`);
      } else {
        channels = [...channels, channel];
        storage.set('channels', channels);
        channelInput.value = '';
        setStatus(channelStatus, `Added ${channel.title}.`, 'ok');
        renderChannels();
      }
    } catch (error) {
      setStatus(channelStatus, error.message, 'error');
    } finally {
      addButton.disabled = false;
    }
  }

  function removeChannel(channel) {
    if (!window.confirm(`Remove ${channel.title}?`)) return;
    channels = channels.filter((c) => c.id !== channel.id);
    storage.set('channels', channels);
    app.feed.forget(channel.id);
    setStatus(channelStatus, `Removed ${channel.title}.`);
    renderChannels();
  }

  function renderChannels() {
    channelList.replaceChildren(
      ...channels.map((channel) =>
        h(
          'li',
          {},
          h('img', { src: channel.thumbnail, alt: '', referrerPolicy: 'no-referrer' }),
          h('span', { class: 'channel-name' }, channel.title),
          h(
            'button',
            { class: 'icon-button danger', type: 'button', 'aria-label': `Remove ${channel.title}`, onClick: () => removeChannel(channel) },
            icon('trash'),
          ),
        ),
      ),
    );
    if (!channels.length) channelList.append(h('li', { class: 'hint' }, 'No channels yet.'));
  }

  async function refresh() {
    if (!channels.length) return setStatus(refreshStatus, 'Add a channel first.', 'error');
    setStatus(refreshStatus, 'Refreshing…');
    const result = await app.feed.load(channels, { force: true });
    if (result.errors.length) setStatus(refreshStatus, result.errors[0], 'error');
    else setStatus(refreshStatus, `${result.videos.length} videos ready.`, 'ok');
  }

  function changePin() {
    openPinPad(app, {
      title: 'New PIN (4–6 digits)',
      onCancel: () => {},
      onDone: (first) =>
        openPinPad(app, {
          title: 'Enter the new PIN again',
          onCancel: () => {},
          onDone: async (second) => {
            if (first !== second) return setStatus(pinStatus, "The PINs didn't match. PIN not changed.", 'error');
            storage.set('pin', await createPinRecord(second));
            setStatus(pinStatus, 'PIN changed.', 'ok');
          },
        }),
    });
  }

  function done() {
    app.go('home');
  }
}
