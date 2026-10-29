export function isValidPin(pin) {
  return /^\d{4,6}$/.test(pin);
}

export async function createPinRecord(pin) {
  const salt = toHex(crypto.getRandomValues(new Uint8Array(16)));
  return { salt, hash: await hashPin(pin, salt) };
}

export async function verifyPin(pin, record) {
  if (!record) return false;
  return (await hashPin(pin, record.salt)) === record.hash;
}

async function hashPin(pin, salt) {
  const data = new TextEncoder().encode(`${salt}:${pin}`);
  return toHex(new Uint8Array(await crypto.subtle.digest('SHA-256', data)));
}

function toHex(bytes) {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}
