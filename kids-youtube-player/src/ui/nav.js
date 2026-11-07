import { h, icon } from '../dom.js';

/** Bottom tab bar: Home and Channels. There is deliberately no Shorts tab. */
export function bottomNav(app, current) {
  const tab = (screen, label, iconName) =>
    h(
      'button',
      {
        class: 'tab',
        type: 'button',
        'aria-current': current === screen ? 'page' : null,
        onClick: () => current !== screen && app.go(screen, {}, { replace: true }),
      },
      icon(current === screen ? `${iconName}Filled` : iconName),
      h('span', {}, label),
    );
  return h('nav', { class: 'bottom-nav', 'aria-label': 'Main' }, tab('home', 'Home', 'home'), tab('channels', 'Channels', 'channels'));
}

export function logo() {
  return h('h1', { class: 'logo' }, h('span', { class: 'logo-mark' }, icon('play')), 'Curated');
}
