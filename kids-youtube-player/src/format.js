/** "PT1H2M3S" → "1:02:03", "PT3M12S" → "3:12". Empty for live/unknown. */
export function formatDuration(iso) {
  const m = /^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$/.exec(iso ?? '');
  if (!m) return '';
  const [days, hours, minutes, seconds] = m.slice(1).map((x) => Number(x ?? 0));
  const total = ((days * 24 + hours) * 60 + minutes) * 60 + seconds;
  if (!total) return '';
  const h = Math.floor(total / 3600);
  const min = Math.floor((total % 3600) / 60);
  const s = String(total % 60).padStart(2, '0');
  return h ? `${h}:${String(min).padStart(2, '0')}:${s}` : `${min}:${s}`;
}

const VIEW_UNITS = [
  [1e9, 'B'],
  [1e6, 'M'],
  [1e3, 'K'],
];

/** 1234 → "1.2K views", like YouTube. */
export function formatViews(count) {
  if (count == null || Number.isNaN(Number(count))) return '';
  const n = Number(count);
  for (const [size, suffix] of VIEW_UNITS) {
    if (n >= size) {
      const value = n / size;
      const shown = value < 10 ? Math.floor(value * 10) / 10 : Math.floor(value);
      return `${shown}${suffix} views`;
    }
  }
  return n === 1 ? '1 view' : `${n} views`;
}

const AGO_UNITS = [
  ['year', 365 * 86400],
  ['month', 30 * 86400],
  ['week', 7 * 86400],
  ['day', 86400],
  ['hour', 3600],
  ['minute', 60],
];

/** "2 weeks ago". */
export function timeAgo(date, now = Date.now()) {
  const then = Date.parse(date);
  if (Number.isNaN(then)) return '';
  const seconds = Math.max(0, (now - then) / 1000);
  for (const [unit, size] of AGO_UNITS) {
    const n = Math.floor(seconds / size);
    if (n >= 1) return `${n} ${unit}${n === 1 ? '' : 's'} ago`;
  }
  return 'just now';
}
