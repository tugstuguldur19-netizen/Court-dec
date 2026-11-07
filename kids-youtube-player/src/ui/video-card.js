import { h } from '../dom.js';
import { formatDuration, formatViews, timeAgo } from '../format.js';

function thumbnail(video, className) {
  const duration = formatDuration(video.duration);
  return h(
    'span',
    { class: className },
    h('img', { src: video.thumbnail, alt: '', loading: 'lazy', referrerPolicy: 'no-referrer' }),
    duration && h('span', { class: 'duration' }, duration),
  );
}

function stats(video) {
  return [formatViews(video.views), timeAgo(video.publishedAt)].filter(Boolean).join(' · ');
}

function avatar(app, channelId, className = 'avatar') {
  return h('img', { class: className, src: app.channelThumb(channelId), alt: '', loading: 'lazy', referrerPolicy: 'no-referrer' });
}

/** Full-width feed card, as on YouTube's home feed. */
export function videoCard(app, video) {
  return h(
    'li',
    {},
    h(
      'button',
      { class: 'video-card', type: 'button', onClick: () => app.go('watch', { video }) },
      thumbnail(video, 'thumb'),
      h(
        'span',
        { class: 'video-card-info' },
        avatar(app, video.channelId),
        h(
          'span',
          { class: 'video-card-text' },
          h('span', { class: 'video-title' }, video.title),
          h('span', { class: 'video-meta' }, [video.channelTitle, stats(video)].filter(Boolean).join(' · ')),
        ),
      ),
    ),
  );
}

/** Thumbnail-left row for "Up next" and search results. */
export function compactCard(app, video, { replace = false } = {}) {
  return h(
    'li',
    {},
    h(
      'button',
      { class: 'compact-card', type: 'button', onClick: () => app.go('watch', { video }, { replace }) },
      thumbnail(video, 'thumb small'),
      h(
        'span',
        { class: 'video-card-text' },
        h('span', { class: 'video-title small' }, video.title),
        h('span', { class: 'video-meta' }, video.channelTitle),
        h('span', { class: 'video-meta' }, stats(video)),
      ),
    ),
  );
}

export { avatar, stats };
