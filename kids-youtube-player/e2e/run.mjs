// End-to-end test of the built app in Chromium with the YouTube Data API and
// IFrame player mocked. Run with `npm run test:e2e` (builds first).
import { spawn, execSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const PORT = 4173;
const BASE = `http://localhost:${PORT}`;
const SHOTS = new URL('./screenshots/', import.meta.url).pathname;
mkdirSync(SHOTS, { recursive: true });

const CHANNELS = {
  '@KidsSongs': { id: 'UCkids0000000000000000ab', title: 'Kids Songs', color: '#ff9f1c' },
  '@ScienceKids': { id: 'UCscience00000000000000ab', title: 'Science Kids', color: '#3d7cff' },
};

const VIDEO_TITLES = {
  UCkids0000000000000000ab: ['Wheels on the Bus', 'Five Little Ducks', 'Baby Shark Dance', 'Old MacDonald'],
  UCscience00000000000000ab: ['Why Is the Sky Blue?', 'How Volcanoes Work', 'Planets for Kids'],
};

const requestedPlaylists = [];

function fakeYouTubeApi(route) {
  const url = new URL(route.request().url());
  const json = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
  if (url.pathname.endsWith('/channels')) {
    const channel = CHANNELS[url.searchParams.get('forHandle')];
    if (!channel) return json({ items: [] });
    return json({
      items: [{ id: channel.id, snippet: { title: channel.title, thumbnails: { medium: { url: `https://yt3.ggpht.com/${channel.id}` } } } }],
    });
  }
  if (url.pathname.endsWith('/playlistItems')) {
    const playlistId = url.searchParams.get('playlistId');
    requestedPlaylists.push(playlistId);
    const channelId = `UC${playlistId.slice(4)}`;
    const titles = VIDEO_TITLES[channelId];
    // First page: all but the last video, then a second page with the last one.
    const secondPage = url.searchParams.get('pageToken') === 'PAGE2';
    const pageTitles = secondPage ? titles.slice(-1) : titles.slice(0, -1);
    const offset = secondPage ? titles.length - 1 : 0;
    return json({
      nextPageToken: secondPage ? undefined : 'PAGE2',
      items: pageTitles.map((title, i) => {
        const n = offset + i;
        const videoId = `${channelId.slice(2, 6)}vid${String(n).padStart(4, '0')}`;
        return {
          snippet: {
            title,
            videoOwnerChannelId: channelId,
            videoOwnerChannelTitle: Object.values(CHANNELS).find((c) => c.id === channelId).title,
            resourceId: { videoId },
            thumbnails: { medium: { url: `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg` } },
          },
          contentDetails: { videoPublishedAt: `2026-10-${String(20 - n * 2 - (channelId.includes('science') ? 1 : 0)).padStart(2, '0')}T10:00:00Z` },
        };
      }),
    });
  }
  return json({ error: { message: 'unexpected' } }, 500);
}

function placeholderImage(route) {
  const url = route.request().url();
  const channel = Object.values(CHANNELS).find((c) => url.includes(c.id) || url.includes(c.id.slice(2, 6)));
  const color = channel?.color ?? '#999';
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect width="320" height="180" fill="${color}"/><circle cx="160" cy="90" r="34" fill="rgba(255,255,255,.85)"/><path d="M150 72v36l30-18z" fill="${color}"/></svg>`;
  return route.fulfill({ status: 200, contentType: 'image/svg+xml', body: svg });
}

// Stands in for YouTube's player: records what the app asks for and lets the
// test drive state changes through window.__fakePlayer.
const FAKE_IFRAME_API = `
window.YT = {
  PlayerState: { UNSTARTED: -1, ENDED: 0, PLAYING: 1, PAUSED: 2, BUFFERING: 3, CUED: 5 },
  Player: class {
    constructor(el, opts) {
      this.opts = opts;
      this.videoId = opts.videoId;
      this.loads = [];
      el.textContent = 'fake player: ' + opts.videoId;
      el.style.cssText += ';color:#fff;display:grid;place-items:center;font:16px sans-serif';
      window.__fakePlayer = this;
    }
    emit(state) { this.opts.events.onStateChange({ target: this, data: state }); }
    getVideoData() { return { video_id: this.videoId }; }
    loadVideoById(id) { this.videoId = id; this.loads.push(id); }
    seekTo() {}
    playVideo() { this.emit(1); }
    destroy() { window.__fakePlayer = null; }
  },
};
window.onYouTubeIframeAPIReady && window.onYouTubeIframeAPIReady();
`;

async function enterPin(page, pin) {
  for (const digit of pin) await page.locator('.pin-overlay .pin-key', { hasText: new RegExp(`^${digit}$`) }).click();
  await page.locator('.pin-overlay .pin-ok').click();
}

const emit = (page, state) => page.evaluate((s) => window.__fakePlayer.emit(s), state);
const backLabel = (page) => page.locator('.back-label').textContent();

async function main() {
  execSync('npx vite build', { stdio: 'inherit' });
  const server = spawn('npx', ['vite', 'preview', '--port', String(PORT), '--strictPort'], { stdio: 'ignore' });
  const browser = await chromium.launch();
  try {
    await waitForServer();
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('dialog', (d) => d.accept());
    await page.route('https://www.googleapis.com/youtube/v3/**', fakeYouTubeApi);
    await page.route('https://www.youtube.com/iframe_api', (r) =>
      r.fulfill({ status: 200, contentType: 'text/javascript', body: FAKE_IFRAME_API }),
    );
    await page.route(/https:\/\/(i\.ytimg\.com|yt3\.ggpht\.com)\/.*/, placeholderImage);
    await page.clock.install({ time: new Date('2026-10-29T09:00:00Z') });

    // First launch: choose the PIN (with one mismatch first).
    await page.goto(BASE);
    await page.getByRole('heading', { name: 'Choose a parent PIN (4–6 digits)' }).waitFor();
    await page.screenshot({ path: `${SHOTS}1-pin-setup.png` });
    await enterPin(page, '1357');
    await enterPin(page, '1358');
    await page.getByText("The PINs didn't match. Try again.").waitFor();
    await enterPin(page, '1357');
    await enterPin(page, '1357');

    // Parent settings: key first, then channels.
    await page.getByRole('heading', { name: 'Parent settings' }).waitFor();
    await page.locator('#channel-input').fill('@KidsSongs');
    await page.getByRole('button', { name: 'Add', exact: true }).click();
    await page.getByText('Save your YouTube API key first.').waitFor();
    await page.locator('#api-key').fill('AIzaTEST');
    await page.getByRole('button', { name: 'Save', exact: true }).click();
    await page.getByText('Saved.').waitFor();
    await page.locator('#channel-input').fill('https://www.youtube.com/watch?v=abc');
    await page.getByRole('button', { name: 'Add', exact: true }).click();
    await page.getByText('Paste a channel link or @handle').waitFor();
    await page.locator('#channel-input').fill('https://www.youtube.com/@KidsSongs');
    await page.getByRole('button', { name: 'Add', exact: true }).click();
    await page.getByText('Added Kids Songs.').waitFor();
    await page.locator('#channel-input').fill('@ScienceKids');
    await page.getByRole('button', { name: 'Add', exact: true }).click();
    await page.getByText('Added Science Kids.').waitFor();
    await page.locator('#channel-input').fill('@nobody');
    await page.getByRole('button', { name: 'Add', exact: true }).click();
    await page.getByText("Couldn't find that channel").waitFor();
    await page.screenshot({ path: `${SHOTS}2-parent.png`, fullPage: true });
    await page.getByRole('button', { name: 'Done' }).click();

    // Home: newest first across both channels, Shorts-free playlists only.
    await page.locator('.card').first().waitFor();
    assert.equal(await page.locator('.card').count(), 5);
    assert.deepEqual(
      await page.locator('.card-title').allTextContents(),
      ['Wheels on the Bus', 'Why Is the Sky Blue?', 'Five Little Ducks', 'How Volcanoes Work', 'Baby Shark Dance'],
    );
    assert.ok(requestedPlaylists.every((id) => id.startsWith('UULF')), `only UULF playlists: ${requestedPlaylists}`);
    await page.getByRole('button', { name: 'Load more videos' }).click();
    await page.locator('.card').nth(6).waitFor();
    assert.equal(await page.locator('.card').count(), 7);
    assert.ok(await page.getByRole('button', { name: 'Load more videos' }).isHidden());
    await page.getByRole('button', { name: 'Science Kids', exact: true }).click();
    assert.equal(await page.locator('.card').count(), 3);
    await page.getByRole('button', { name: 'All', exact: true }).click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: `${SHOTS}3-home.png` });

    // Player: locked until 60 s of actual playing.
    await page.locator('.card').first().click();
    await page.locator('.back-button').waitFor();
    assert.equal(await backLabel(page), '60s');
    assert.ok(await page.locator('.back-button').isDisabled());
    await page.waitForFunction(() => window.__fakePlayer);
    await emit(page, 1);
    await page.clock.runFor(30_250); // one 250 ms tick of slack
    assert.equal(await backLabel(page), '30s');
    await page.screenshot({ path: `${SHOTS}4-player-locked.png` });

    // Pausing stops the countdown.
    await emit(page, 2);
    await page.clock.runFor(60_000);
    assert.equal(await backLabel(page), '30s');
    assert.ok(await page.locator('.back-button').isDisabled());

    // Reopening the app comes back to the same locked video.
    await page.reload();
    await page.locator('.back-button').waitFor();
    assert.equal(await page.locator('.video-title').textContent(), 'Wheels on the Bus');
    assert.equal(await backLabel(page), '30s');
    await page.waitForFunction(() => window.__fakePlayer);

    // A suggestion inside the player switching videos gets switched back.
    await page.evaluate(() => {
      window.__fakePlayer.videoId = 'someOtherVid';
    });
    await emit(page, 1);
    const loads = await page.evaluate(() => window.__fakePlayer.loads);
    assert.equal(loads.length, 1);
    assert.match(loads[0], /^kidsvid/);
    await page.clock.runFor(5_000);
    assert.equal(await backLabel(page), '30s', 'the switched video does not count');

    await emit(page, 1);
    await page.clock.runFor(31_000);
    assert.equal(await backLabel(page), 'Back');
    assert.ok(await page.locator('.back-button').isEnabled());
    await page.screenshot({ path: `${SHOTS}5-player-unlocked.png` });
    await page.locator('.back-button').click();
    await page.locator('.card').first().waitFor();
    assert.equal(await page.evaluate(() => localStorage.getItem('kyp:lockSession')), null);

    // A video that ends early unlocks and shows our own end screen.
    await page.locator('.card').nth(1).click();
    await page.waitForFunction(() => window.__fakePlayer);
    await emit(page, 1);
    await page.clock.runFor(5_000);
    await emit(page, 0);
    await page.getByText('All done!').waitFor();
    assert.ok(await page.locator('.back-button').isEnabled());
    await page.screenshot({ path: `${SHOTS}6-player-ended.png` });
    await page.locator('.player-overlay').getByRole('button', { name: 'Back to videos' }).click();

    // A parent can unlock early with the PIN.
    await page.locator('.card').nth(2).click();
    await page.waitForFunction(() => window.__fakePlayer);
    await page.getByRole('button', { name: 'Parent unlock' }).click();
    await enterPin(page, '0000');
    await page.getByText('Wrong PIN').waitFor();
    await enterPin(page, '1357');
    await page.locator('.back-button:not([disabled])').waitFor();
    await page.locator('.back-button').click();

    // Parent area from home; removing a channel removes its videos.
    await page.getByRole('button', { name: 'Parent settings' }).click();
    await enterPin(page, '1357');
    await page.getByRole('button', { name: 'Remove Science Kids' }).click();
    await page.getByText('Removed Science Kids.').waitFor();
    await page.getByRole('button', { name: 'Done' }).click();
    await page.locator('.card').first().waitFor();
    const titles = await page.locator('.card-channel').allTextContents();
    assert.ok(titles.length > 0 && titles.every((t) => t === 'Kids Songs'), titles.join());
    assert.ok(await page.locator('.chips').isHidden());

    // Landscape player.
    await page.setViewportSize({ width: 844, height: 390 });
    await page.locator('.card').first().click();
    await page.waitForFunction(() => window.__fakePlayer);
    await page.screenshot({ path: `${SHOTS}7-player-landscape.png` });

    assert.deepEqual(errors, []);
    console.log('E2E passed. Screenshots in', SHOTS);
  } finally {
    await browser.close();
    server.kill();
  }
}

async function waitForServer() {
  for (let i = 0; i < 50; i++) {
    try {
      if ((await fetch(BASE)).ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error('preview server did not start');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
