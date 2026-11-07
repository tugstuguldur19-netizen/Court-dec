// End-to-end test of the built app in Chromium with the YouTube Data API and
// IFrame player mocked. Run with `npm run test:e2e` (builds first).
import { spawn, execSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const PORT = 4173;
const BASE = `http://localhost:${PORT}/`;
const SHOTS = new URL('./screenshots/', import.meta.url).pathname;
mkdirSync(SHOTS, { recursive: true });

const CHANNELS = {
  '@KidsSongs': { id: 'UCkids0000000000000000ab', title: 'Kids Songs', color: '#ff9f1c' },
  '@ScienceKids': { id: 'UCscience00000000000000ab', title: 'Science Kids', color: '#3d7cff' },
};

const VIDEO_TITLES = {
  UCkids0000000000000000ab: ['Wheels on the Bus', 'Five Little Ducks', 'Counting to Ten', 'Old Farm Song'],
  UCscience00000000000000ab: ['Why Is the Sky Blue?', 'How Volcanoes Work', 'Planets for Kids'],
};

const channelOf = (videoId) => Object.values(CHANNELS).find((c) => videoId.startsWith(c.id.slice(2, 6)));
const requested = { playlists: [], videoDetails: 0 };

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
    requested.playlists.push(playlistId);
    const channelId = `UC${playlistId.slice(4)}`;
    const titles = VIDEO_TITLES[channelId];
    // First page: all but the last video, then a second page with the last one.
    const secondPage = url.searchParams.get('pageToken') === 'PAGE2';
    const offset = secondPage ? titles.length - 1 : 0;
    return json({
      nextPageToken: secondPage ? undefined : 'PAGE2',
      items: (secondPage ? titles.slice(-1) : titles.slice(0, -1)).map((title, i) => {
        const n = offset + i;
        const videoId = `${channelId.slice(2, 6)}vid${String(n).padStart(4, '0')}`;
        const day = 20 - n * 2 - (channelId.includes('science') ? 1 : 0);
        return {
          snippet: {
            title,
            videoOwnerChannelId: channelId,
            videoOwnerChannelTitle: channelOf(videoId).title,
            resourceId: { videoId },
            thumbnails: { medium: { url: `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg` } },
          },
          contentDetails: { videoPublishedAt: `2026-10-${String(day).padStart(2, '0')}T10:00:00Z` },
        };
      }),
    });
  }
  if (url.pathname.endsWith('/videos')) {
    requested.videoDetails++;
    const ids = url.searchParams.get('id').split(',');
    return json({
      items: ids.map((id, i) => ({
        id,
        contentDetails: { duration: `PT${3 + i}M${10 + i}S` },
        statistics: { viewCount: String(1_200_000 + i * 345_000) },
      })),
    });
  }
  return json({ error: { message: 'unexpected' } }, 500);
}

function placeholderImage(route) {
  const url = route.request().url();
  const channel = Object.values(CHANNELS).find((c) => url.includes(c.id) || url.includes(c.id.slice(2, 6)));
  const color = channel?.color ?? '#999';
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect width="320" height="180" fill="${color}"/></svg>`;
  return route.fulfill({ status: 200, contentType: 'image/svg+xml', body: svg });
}

// Stands in for YouTube's player and lets the test drive state changes.
const FAKE_IFRAME_API = `
window.YT = {
  PlayerState: { UNSTARTED: -1, ENDED: 0, PLAYING: 1, PAUSED: 2, BUFFERING: 3, CUED: 5 },
  Player: class {
    constructor(el, opts) {
      this.opts = opts;
      this.videoId = opts.videoId;
      this.loads = [];
      el.textContent = 'video ' + opts.videoId;
      el.style.cssText += ';color:#fff;display:grid;place-items:center;font:14px sans-serif';
      window.__fakePlayer = this;
    }
    emit(state) { this.opts.events.onStateChange({ target: this, data: state }); }
    getVideoData() { return { video_id: this.videoId }; }
    loadVideoById(id) { this.videoId = id; this.loads.push(id); }
    seekTo() {}
    playVideo() { this.emit(1); }
    destroy() { if (window.__fakePlayer === this) window.__fakePlayer = null; }
  },
};
window.onYouTubeIframeAPIReady && window.onYouTubeIframeAPIReady();
`;

const titles = (page, sel = '.video-card .video-title') => page.locator(sel).allTextContents();

async function main() {
  execSync('npx vite build', { stdio: 'inherit' });
  const server = spawn('npx', ['vite', 'preview', '--port', String(PORT), '--strictPort'], { stdio: 'ignore' });
  const browser = await chromium.launch();
  try {
    await waitForServer();
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('dialog', (d) => d.accept());
    await page.route('https://www.googleapis.com/youtube/v3/**', fakeYouTubeApi);
    await page.route('https://www.youtube.com/iframe_api', (r) =>
      r.fulfill({ status: 200, contentType: 'text/javascript', body: FAKE_IFRAME_API }),
    );
    await page.route(/https:\/\/(i\.ytimg\.com|yt3\.ggpht\.com)\/.*/, placeholderImage);
    await page.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\/.*/, (r) => r.fulfill({ status: 200, body: '' }));
    await page.clock.setFixedTime(new Date('2026-10-29T09:00:00Z'));

    // First launch opens Channels with the key form ready.
    await page.goto(BASE);
    await page.getByRole('heading', { name: 'Channels' }).waitFor();
    assert.ok(await page.locator('#api-key').isVisible(), 'key form open on first launch');
    await page.locator('#channel-input').fill('@KidsSongs');
    await page.getByRole('button', { name: 'Add', exact: true }).click();
    await page.getByText('Add your YouTube API key first').waitFor();
    await page.locator('#api-key').fill('AIzaTEST');
    await page.getByRole('button', { name: 'Save', exact: true }).click();
    await page.getByText('Saved.').waitFor();
    await page.locator('#channel-input').fill('https://www.youtube.com/shorts/abc');
    await page.getByRole('button', { name: 'Add', exact: true }).click();
    await page.getByText('Paste a channel link or @handle').waitFor();
    for (const [input, name] of [
      ['https://www.youtube.com/@KidsSongs', 'Kids Songs'],
      ['@ScienceKids', 'Science Kids'],
    ]) {
      await page.locator('#channel-input').fill(input);
      await page.getByRole('button', { name: 'Add', exact: true }).click();
      await page.getByText(`Added ${name}.`).waitFor();
    }
    await page.locator('#channel-input').fill('@nobody');
    await page.getByRole('button', { name: 'Add', exact: true }).click();
    await page.getByText("Couldn't find that channel").waitFor();
    await page.locator('#channel-input').fill('');
    await page.locator('.settings-row summary').click(); // collapse the key form
    await page.screenshot({ path: `${SHOTS}4-channels.png` });

    // Home: newest first across channels, with length, views and age.
    await page.getByRole('button', { name: 'Home' }).click();
    await page.locator('.video-card').first().waitFor();
    assert.deepEqual(await titles(page), [
      'Wheels on the Bus',
      'Why Is the Sky Blue?',
      'Five Little Ducks',
      'How Volcanoes Work',
      'Counting to Ten',
    ]);
    assert.ok(requested.playlists.every((id) => id.startsWith('UULF')), `only Shorts-free playlists: ${requested.playlists}`);
    assert.ok(requested.videoDetails >= 2, 'video lengths and views fetched');
    assert.equal(await page.locator('.video-card .duration').first().textContent(), '3:10');
    assert.equal(await page.locator('.video-card .video-meta').first().textContent(), 'Kids Songs · 1.2M views · 1 week ago');
    await page.screenshot({ path: `${SHOTS}1-home.png` });

    await page.getByRole('button', { name: 'Science Kids', exact: true }).click();
    assert.deepEqual(await titles(page), ['Why Is the Sky Blue?', 'How Volcanoes Work']);
    await page.getByRole('button', { name: 'All', exact: true }).click();
    await page.getByRole('button', { name: 'Show more videos' }).click();
    await page.locator('.video-card').nth(6).waitFor();
    assert.ok(await page.getByRole('button', { name: 'Show more videos' }).isHidden());

    // Watch: up next prefers the same channel; only approved videos can play.
    await page.locator('.video-card').first().click();
    await page.locator('.watch-title').waitFor();
    assert.equal(await page.locator('.watch-title').textContent(), 'Wheels on the Bus');
    await page.locator('.compact-card').first().waitFor();
    const upNext = await titles(page, '.compact-card .video-title');
    assert.deepEqual(upNext.slice(0, 3), ['Five Little Ducks', 'Counting to Ten', 'Old Farm Song']);
    await page.waitForFunction(() => window.__fakePlayer);
    await page.screenshot({ path: `${SHOTS}2-watch.png` });

    await page.evaluate(() => {
      window.__fakePlayer.videoId = 'notApproved1';
      window.__fakePlayer.emit(1);
    });
    assert.deepEqual(await page.evaluate(() => window.__fakePlayer.loads), ['kidsvid0000'], 'unapproved video swapped back');

    await page.evaluate(() => {
      window.__fakePlayer.videoId = 'scievid0001';
      window.__fakePlayer.emit(1);
    });
    await page.locator('.watch-title', { hasText: 'How Volcanoes Work' }).waitFor();

    await page.waitForFunction(() => window.__fakePlayer);
    await page.evaluate(() => window.__fakePlayer.emit(0));
    await page.getByRole('button', { name: 'Play next' }).waitFor();
    await page.screenshot({ path: `${SHOTS}3-ended.png` });
    await page.getByRole('button', { name: 'Play next' }).click();
    await page.locator('.watch-title', { hasText: 'Why Is the Sky Blue?' }).waitFor();

    // Back returns to the feed (the player swaps used replace, not new entries).
    await page.getByRole('button', { name: 'Back' }).first().click();
    await page.locator('.video-card').first().waitFor();

    // Search only covers approved channels.
    await page.getByRole('button', { name: 'Search' }).click();
    await page.locator('#search-input').fill('volcano');
    await page.locator('.compact-card').first().waitFor();
    assert.deepEqual(await titles(page, '.compact-card .video-title'), ['How Volcanoes Work']);
    await page.screenshot({ path: `${SHOTS}5-search.png` });
    await page.locator('#search-input').fill('dinosaur');
    await page.getByText('No videos match "dinosaur".').waitFor();
    await page.goBack();
    await page.locator('.video-card').first().waitFor();

    // Reload keeps you where you were.
    await page.locator('.video-card').nth(1).click();
    await page.locator('.watch-title').waitFor();
    await page.reload();
    await page.locator('.watch-title', { hasText: 'Why Is the Sky Blue?' }).waitFor();
    await page.goBack();
    await page.locator('.video-card').first().waitFor();

    // Removing a channel removes its videos.
    await page.getByRole('button', { name: 'Channels' }).click();
    await page.getByRole('button', { name: 'Remove Science Kids' }).click();
    await page.getByText('Removed Science Kids.').waitFor();
    await page.getByRole('button', { name: 'Home' }).click();
    await page.locator('.video-card').first().waitFor();
    const channelsShown = await page.locator('.video-card .video-meta').allTextContents();
    assert.ok(channelsShown.every((m) => m.startsWith('Kids Songs')), channelsShown.join());
    assert.equal(await page.locator('.chips').count(), 0, 'no chips with a single channel');
    assert.ok(!(await page.locator('#app').evaluate((el) => [...el.childNodes].some((n) => n.nodeType === 3))), 'no stray text');

    // Dark mode and a wide screen.
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.screenshot({ path: `${SHOTS}6-home-dark.png` });
    await page.emulateMedia({ colorScheme: 'light' });
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.screenshot({ path: `${SHOTS}7-home-wide.png` });

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
