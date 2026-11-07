import { describe, it, expect } from 'vitest';
import { formatDuration, formatViews, timeAgo } from '../src/format.js';

describe('formatDuration', () => {
  it.each([
    ['PT3M12S', '3:12'],
    ['PT45S', '0:45'],
    ['PT10M', '10:00'],
    ['PT1H2M3S', '1:02:03'],
    ['PT2H', '2:00:00'],
    ['P1DT1M', '24:01:00'],
    ['P0D', ''],
    ['', ''],
    [undefined, ''],
  ])('%s → %j', (iso, expected) => {
    expect(formatDuration(iso)).toBe(expected);
  });
});

describe('formatViews', () => {
  it.each([
    [0, '0 views'],
    [1, '1 view'],
    [999, '999 views'],
    [1000, '1K views'],
    [1234, '1.2K views'],
    [12_345, '12K views'],
    [345_678, '345K views'],
    [1_200_000, '1.2M views'],
    [25_000_000, '25M views'],
    [3_400_000_000, '3.4B views'],
    [undefined, ''],
  ])('%s → %j', (n, expected) => {
    expect(formatViews(n)).toBe(expected);
  });
});

describe('timeAgo', () => {
  const now = Date.parse('2026-11-07T12:00:00Z');
  it.each([
    ['2026-11-07T11:59:30Z', 'just now'],
    ['2026-11-07T11:59:00Z', '1 minute ago'],
    ['2026-11-07T09:00:00Z', '3 hours ago'],
    ['2026-11-06T12:00:00Z', '1 day ago'],
    ['2026-10-24T12:00:00Z', '2 weeks ago'],
    ['2026-08-01T12:00:00Z', '3 months ago'],
    ['2024-11-01T12:00:00Z', '2 years ago'],
    ['', ''],
  ])('%s → %j', (date, expected) => {
    expect(timeAgo(date, now)).toBe(expected);
  });
});
