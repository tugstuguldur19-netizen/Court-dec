import { describe, it, expect } from 'vitest';
import { parseChannelInput } from '../src/channel-input.js';

const ID = 'UCbCmjCuTUZos6Inko4u57UQ';

describe('parseChannelInput', () => {
  it.each([
    ['@CoComelon', { type: 'handle', value: '@CoComelon' }],
    ['  @CoComelon  ', { type: 'handle', value: '@CoComelon' }],
    ['CoComelon', { type: 'handle', value: '@CoComelon' }],
    ['https://www.youtube.com/@CoComelon', { type: 'handle', value: '@CoComelon' }],
    ['https://m.youtube.com/@CoComelon/videos', { type: 'handle', value: '@CoComelon' }],
    ['youtube.com/@CoComelon?si=abc', { type: 'handle', value: '@CoComelon' }],
    ['https://www.youtube.com/@%D0%A2%D0%B5%D1%81%D1%82', { type: 'handle', value: '@Тест' }],
    [ID, { type: 'id', value: ID }],
    [`https://www.youtube.com/channel/${ID}`, { type: 'id', value: ID }],
    [`https://youtube.com/channel/${ID}/featured`, { type: 'id', value: ID }],
    ['https://www.youtube.com/user/PeppaPigOfficial', { type: 'username', value: 'PeppaPigOfficial' }],
  ])('parses %s', (input, expected) => {
    expect(parseChannelInput(input)).toEqual(expected);
  });

  it.each([
    '',
    '   ',
    'https://www.youtube.com/c/SomeCustomName',
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'https://www.youtube.com/shorts/abc',
    'https://example.com/@someone',
    'two words',
  ])('rejects %j', (input) => {
    expect(parseChannelInput(input)).toBeNull();
  });
});
