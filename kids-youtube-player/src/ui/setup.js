import { h } from '../dom.js';
import { openPinPad } from './pin-pad.js';
import { createPinRecord } from '../pin.js';

/** First launch: the parent picks a PIN, then goes straight to settings. */
export function renderSetup(root, app) {
  root.append(
    h(
      'main',
      { class: 'setup' },
      h('h1', {}, 'Welcome to Kids Player'),
      h('p', {}, 'Parents: choose a PIN. You will need it to pick channels and change settings.'),
    ),
  );

  let closePad = null;
  const askFirst = (message = 'You will need it to choose channels and change settings.') => {
    closePad = openPinPad(app, { title: 'Choose a parent PIN (4–6 digits)', message, onDone: askConfirm });
  };
  const askConfirm = (first) => {
    closePad = openPinPad(app, {
      title: 'Enter the PIN again',
      onDone: async (pin) => {
        if (pin !== first) return askFirst("The PINs didn't match. Try again.");
        app.storage.set('pin', await createPinRecord(pin));
        app.go('parent');
      },
    });
  };
  askFirst();
  return () => closePad?.();
}
