import { h, icon } from '../dom.js';

const MAX_DIGITS = 6;
const MIN_DIGITS = 4;

/**
 * Full-screen number pad. `onSubmit(pin)` resolves to true to accept, or to an
 * error string to show and clear the entry. On accept the pad closes and then
 * `onDone(pin)` runs. Returns a function that closes the pad.
 */
export function openPinPad(app, { title, message = '', onSubmit = async () => true, onDone, onCancel }) {
  let pin = '';
  let busy = false;

  const dots = h('div', { class: 'pin-dots', 'aria-live': 'polite' });
  const note = h('p', { class: 'pin-message', role: 'status' }, message);
  const ok = h('button', { class: 'pin-key pin-ok', type: 'button', onClick: submit, 'aria-label': 'OK' }, 'OK');

  const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9'].map(digitKey);
  const erase = h(
    'button',
    { class: 'pin-key pin-erase', type: 'button', 'aria-label': 'Delete', onClick: () => setPin(pin.slice(0, -1)) },
    icon('erase'),
  );
  const overlay = h(
    'div',
    { class: 'pin-overlay', role: 'dialog', 'aria-modal': 'true', 'aria-label': title },
    h(
      'div',
      { class: 'pin-panel' },
      h('div', { class: 'pin-icon' }, icon('lock')),
      h('h2', {}, title),
      dots,
      note,
      h('div', { class: 'pin-keys' }, ...keys, erase, digitKey('0'), ok),
      onCancel && h('button', { class: 'link-button', type: 'button', onClick: cancel }, 'Cancel'),
    ),
  );

  function digitKey(d) {
    return h('button', { class: 'pin-key', type: 'button', onClick: () => setPin(pin + d) }, d);
  }

  function setPin(next) {
    if (busy || next.length > MAX_DIGITS) return;
    pin = next;
    dots.replaceChildren(
      ...Array.from({ length: Math.max(MIN_DIGITS, pin.length) }, (_, i) =>
        h('span', { class: i < pin.length ? 'filled' : '' }),
      ),
    );
    ok.disabled = pin.length < MIN_DIGITS;
  }

  async function submit() {
    if (busy || pin.length < MIN_DIGITS) return;
    busy = true;
    const result = await onSubmit(pin);
    busy = false;
    if (result === true) {
      close();
      onDone?.(pin);
      return;
    }
    note.textContent = result;
    note.classList.add('error');
    overlay.querySelector('.pin-panel').animate(
      [{ transform: 'translateX(0)' }, { transform: 'translateX(-10px)' }, { transform: 'translateX(10px)' }, { transform: 'translateX(0)' }],
      { duration: 250 },
    );
    setPin('');
  }

  function onKey(event) {
    if (/^\d$/.test(event.key)) setPin(pin + event.key);
    else if (event.key === 'Backspace') setPin(pin.slice(0, -1));
    else if (event.key === 'Enter') submit();
    else if (event.key === 'Escape' && onCancel) cancel();
  }

  function cancel() {
    close();
    onCancel();
  }

  function close() {
    document.removeEventListener('keydown', onKey);
    app.popBack(cancelOrIgnore);
    overlay.remove();
  }

  // Back while the pad is open cancels it (or does nothing if it can't be cancelled).
  const cancelOrIgnore = () => onCancel && cancel();

  setPin('');
  document.addEventListener('keydown', onKey);
  app.pushBack(cancelOrIgnore);
  document.body.append(overlay);
  return close;
}
