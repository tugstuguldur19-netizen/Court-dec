/** Small element builder: h('button', {class: 'x', onClick}, 'Label'). */
export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props ?? {})) {
    if (value == null || value === false) continue;
    if (key.startsWith('on')) el.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === 'class') el.className = value;
    else if (key === 'html') el.innerHTML = value;
    else if (key in el && !key.includes('-')) el[key] = value;
    else el.setAttribute(key, value === true ? '' : value);
  }
  el.append(...children.flat().filter((c) => c != null && c !== false));
  return el;
}

const ICONS = {
  play: '<path d="M8 5.5v13l11-6.5z" fill="currentColor" stroke="none"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/>',
  back: '<path d="M20 12H5M11 6l-6 6 6 6"/>',
  down: '<path d="M6 9l6 6 6-6"/>',
  right: '<path d="M9 6l6 6-6 6"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  home: '<path d="M4 10.5L12 4l8 6.5V20h-5.5v-6h-5v6H4z"/>',
  homeFilled: '<path d="M4 10.5L12 4l8 6.5V20h-5.5v-6h-5v6H4z" fill="currentColor"/>',
  channels: '<rect x="3.5" y="7" width="17" height="13" rx="2"/><path d="M7 4h10"/><path d="M10.5 11v5.5l4.5-2.75z" fill="currentColor"/>',
  channelsFilled:
    '<rect x="3.5" y="7" width="17" height="13" rx="2" fill="currentColor"/><path d="M7 4h10"/><path d="M10.5 11v5.5l4.5-2.75z" fill="var(--bg)" stroke="none"/>',
  replay: '<path d="M4 12a8 8 0 1 0 2.4-5.7"/><path d="M4 4v4.5h4.5"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l8-8M16 7l2 2M14 9l2 2"/>',
  check: '<circle cx="12" cy="12" r="10" fill="currentColor" stroke="none"/><path d="M7.5 12.5l3 3 6-6.5" stroke="var(--bg)"/>',
};

export function icon(name) {
  return h('span', {
    class: 'icon',
    'aria-hidden': 'true',
    html: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[name]}</svg>`,
  });
}
