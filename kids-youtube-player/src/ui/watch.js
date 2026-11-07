import { h, icon } from '../dom.js';
import { loadIframeApi } from '../youtube-iframe-api.js';
import { compactCard, avatar, stats } from './video-card.js';

const UP_NEXT_COUNT = 20;

const ERROR_MESSAGES = {
  100: 'This video was removed or made private.',
  101: "This channel doesn't let its videos play in other apps.",
  150: "This channel doesn't let its videos play in other apps.",
};

/** Plays one video, with "Up next" drawn only from approved channels. */
export function renderWatch(root, app, { video }) {
  let player = null;
  let upNext = [];

  const holder = h('div', { id: 'yt-player' });
  const overlay = h('div', { class: 'player-overlay', hidden: true });
  const list = h('ul', { class: 'compact-list' });

  root.append(
    h(
      'div',
      { class: 'player-sticky' },
      h(
        'div',
        { class: 'player-frame' },
        holder,
        overlay,
        h('button', { class: 'icon-button player-back', type: 'button', 'aria-label': 'Back', onClick: () => app.back() }, icon('down')),
      ),
    ),
    h(
      'main',
      { class: 'watch' },
      h('h1', { class: 'watch-title' }, video.title),
      h('p', { class: 'video-meta' }, stats(video)),
      h(
        'div',
        { class: 'channel-row' },
        avatar(app, video.channelId, 'avatar large'),
        h(
          'span',
          { class: 'channel-row-text' },
          h('span', { class: 'channel-name' }, video.channelTitle, h('span', { class: 'approved', title: 'Approved channel' }, icon('check'))),
          h('span', { class: 'video-meta' }, 'Approved channel'),
        ),
        h(
          'button',
          { class: 'pill', type: 'button', onClick: () => app.go('home', { channel: video.channelId }, { replace: true }) },
          'All videos',
        ),
      ),
      h('h2', { class: 'section-title' }, 'Up next'),
      list,
    ),
  );

  app.loadFeed().then((result) => {
    // The same channel first, then everything else, newest first.
    const others = result.videos.filter((v) => v.id !== video.id);
    upNext = [...others.filter((v) => v.channelId === video.channelId), ...others.filter((v) => v.channelId !== video.channelId)].slice(
      0,
      UP_NEXT_COUNT,
    );
    list.replaceChildren(...upNext.map((v) => compactCard(app, v, { replace: true })));
  });

  loadIframeApi()
    .then((YT) => {
      player = new YT.Player(holder, {
        videoId: video.id,
        width: '100%',
        height: '100%',
        playerVars: { autoplay: 1, playsinline: 1, rel: 0, iv_load_policy: 3, fs: 1, origin: window.location.origin },
        events: {
          onStateChange: (event) => onStateChange(YT, event),
          onError: (event) => showOverlay(ERROR_MESSAGES[event.data] ?? "This video can't play right now.", false),
        },
      });
    })
    .catch((error) => showOverlay(error.message, false));

  function onStateChange(YT, event) {
    if (event.data === YT.PlayerState.PLAYING) {
      // Links inside YouTube's player (end screens, cards) can switch videos.
      // Allow it only for videos from approved channels.
      const current = player?.getVideoData?.()?.video_id;
      if (current && current !== video.id) {
        const known = app.findVideo(current);
        if (known) app.go('watch', { video: known }, { replace: true });
        else player.loadVideoById(video.id);
      }
    }
    if (event.data === YT.PlayerState.ENDED) showOverlay('', true);
  }

  function showOverlay(message, ended) {
    const next = upNext[0];
    overlay.replaceChildren(
      ended && next
        ? h(
            'div',
            { class: 'overlay-next' },
            h('p', { class: 'overlay-label' }, 'Up next'),
            h('p', { class: 'overlay-title' }, next.title),
            h(
              'div',
              { class: 'overlay-buttons' },
              h('button', { class: 'pill', type: 'button', onClick: replay }, icon('replay'), 'Replay'),
              h('button', { class: 'pill primary', type: 'button', onClick: () => app.go('watch', { video: next }, { replace: true }) }, icon('play'), 'Play next'),
            ),
          )
        : h(
            'div',
            { class: 'overlay-next' },
            h('p', { class: 'overlay-title' }, message || 'That’s the end of this video.'),
            h(
              'div',
              { class: 'overlay-buttons' },
              ended && h('button', { class: 'pill', type: 'button', onClick: replay }, icon('replay'), 'Replay'),
              h('button', { class: 'pill primary', type: 'button', onClick: () => app.back() }, 'Back'),
            ),
          ),
    );
    overlay.hidden = false;
  }

  function replay() {
    overlay.hidden = true;
    player.seekTo(0, true);
    player.playVideo();
  }

  return () => player?.destroy?.();
}
