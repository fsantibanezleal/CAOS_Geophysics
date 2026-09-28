/** Local rendered gate for the six-route shell foundation. Uses built preview, not a deployment. */
import { chromium } from '@playwright/test';
import { readFileSync, existsSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const routes = JSON.parse(readFileSync(join(frontend, 'src/lib/routes.json'), 'utf8'));
const base = process.env.QA_BASE ?? 'http://127.0.0.1:5179';
const builtHtml = readFileSync(join(frontend, 'dist/index.html'), 'utf8');
const mode = process.env.QA_DEPLOYMENT_MODE ?? (builtHtml.includes('src="/assets/') ? 'single-origin' : 'legacy');
const shots = process.env.QA_OUTPUT ? resolve(process.env.QA_OUTPUT) : mkdtempSync(join(tmpdir(), 'geophysics-foundation-'));
const errors = [];
const checks = [];

function assert(ok, message) { if (!ok) errors.push(message); }

assert(['legacy', 'single-origin'].includes(mode), `unknown QA mode ${mode}`);
if (mode === 'legacy') {
  assert(builtHtml.includes('./assets/'), 'legacy build lost its relative asset base');
  for (const route of routes.slice(1))
    assert(existsSync(join(frontend, 'dist', route.path.slice(1), 'index.html')), `missing legacy entrypoint ${route.path}`);
} else {
  assert(builtHtml.includes('/assets/'), 'single-origin build lacks root asset paths');
  for (const route of routes.slice(1))
    assert(!existsSync(join(frontend, 'dist', route.path.slice(1), 'index.html')), `target build retained a legacy entrypoint ${route.path}`);
}

async function pointerClick(page, locator) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (!box) throw new Error('Navigation target has no visible bounds');
  const x = box.x + box.width / 2, y = box.y + box.height / 2;
  await page.mouse.move(x, y, { steps: 5 });
  await page.mouse.down();
  await page.mouse.up();
}

async function checkRoute(page, route, label) {
  await page.waitForURL(url => url.pathname.replace(/\/$/, '') === (route.path === '/' ? '' : route.path), { timeout: 12000 });
  await page.locator('main').waitFor();
  if (route.id === 'app') {
    await page.locator('section.instrument-main [role="tablist"]').first().waitFor({ timeout: 20000 });
    assert(await page.locator('section.instrument-main [role="alert"]').count() === 0, `${label} app: artifact loading failed`);
  }
  if (route.id === 'benchmark') {
    await page.locator('table.cmp-table tbody tr').first().waitFor({ timeout: 20000 });
    const rows = await page.locator('table.cmp-table tbody tr').count();
    assert(rows >= 1, `${label} benchmark: no hydrated case rows`);
    assert(await page.locator('.benchmark-controls select[aria-label="Method"], .benchmark-controls select[aria-label="Método"]').first().locator('option').count() >= 1,
      `${label} benchmark: no hydrated methods`);
  }
  const state = await page.evaluate(() => ({
    path: location.pathname,
    width: document.documentElement.scrollWidth,
    viewport: innerWidth,
    height: document.documentElement.scrollHeight,
    viewportHeight: innerHeight,
    text: document.querySelector('main')?.textContent?.trim().length ?? 0,
    links: [...document.querySelectorAll('nav.main-nav a')].map(a => a.getAttribute('href')),
    theme: document.documentElement.dataset.theme,
  }));
  assert(state.width <= state.viewport, `${label} ${route.id}: horizontal document overflow ${state.width}/${state.viewport}`);
  if (route.id === 'app') assert(state.height <= state.viewportHeight + 1, `${label} app: document taller than viewport ${state.height}/${state.viewportHeight}`);
  assert(state.text > 100, `${label} ${route.id}: content did not render (${state.text} chars)`);
  assert(state.links.length === 6, `${label} ${route.id}: expected six shell nav links`);
  checks.push({ label, route: route.id, path: state.path, width: state.width, viewport: state.viewport, contentChars: state.text, theme: state.theme });
}

const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader'] });
try {
  for (const viewport of [{ name: 'desktop', width: 1600, height: 900 }, { name: 'phone', width: 390, height: 844 }]) {
    for (const theme of ['light', 'dark']) {
      for (const lang of ['en', 'es']) {
        const label = `${viewport.name}/${theme}/${lang}`;
        const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, reducedMotion: 'reduce' });
        await context.addInitScript(({ theme, lang }) => {
          localStorage.setItem('caos.theme', theme);
          localStorage.setItem('caos.lang', lang);
        }, { theme, lang });
        const page = await context.newPage();
        page.on('pageerror', error => errors.push(`${label}: ${error.message}`));
        page.on('response', response => { if (response.status() >= 400 && response.url().startsWith(base)) errors.push(`${label}: HTTP ${response.status()} ${response.url()}`); });
        await page.goto(base, { waitUntil: 'domcontentloaded' });
        await checkRoute(page, routes[0], label);
        assert(await page.evaluate(() => document.documentElement.dataset.theme) === theme, `${label}: theme did not switch`);
        const navLabel = await page.locator('nav.main-nav a').nth(1).innerText();
        assert(navLabel === (lang === 'es' ? 'Introducción' : 'Introduction'), `${label}: navigation language ${navLabel}`);
        const catalog = await page.evaluate(async () => {
          const response = await fetch('/data/v2/catalog.json');
          if (!response.ok) return { status: response.status, cases: 0 };
          const value = await response.json();
          return { status: response.status, cases: value.cases?.length ?? 0 };
        });
        assert(catalog.status === 200 && catalog.cases >= 20, `${label}: legacy scientific catalogue not hydrated ${JSON.stringify(catalog)}`);

        // Two full physical-pointer journeys; other combinations still get direct-route checks.
        if ((viewport.name === 'desktop' && theme === 'light' && lang === 'en') || (viewport.name === 'phone' && theme === 'dark' && lang === 'es')) {
          for (const route of routes.slice(1)) {
            const link = page.locator('nav.main-nav a').filter({ hasText: lang === 'es' ? route.es : route.en }).first();
            await pointerClick(page, link);
            await checkRoute(page, route, `${label}/pointer`);
          }
          await pointerClick(page, page.locator('a.brand'));
          await checkRoute(page, routes[0], `${label}/pointer-return`);
        }

        for (const route of routes.slice(1)) {
          await page.goto(base + route.path, { waitUntil: 'domcontentloaded' });
          await checkRoute(page, route, `${label}/direct`);
        }
        await page.goto(base, { waitUntil: 'networkidle' });
        await checkRoute(page, routes[0], `${label}/screenshot`);
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        await page.screenshot({ path: join(shots, `${label.replaceAll('/', '-')}-app.png`) });
        const architecture = page.locator('button[aria-label*="rchitecture"], button[aria-label*="rquitectura"]').first();
        await pointerClick(page, architecture);
        const dialog = page.getByRole('dialog');
        await dialog.locator('svg.arch-svg').first().waitFor();
        assert(await dialog.getByRole('tab').count() === 5, `${label}: architecture has wrong tab count`);
        const tabRows = await dialog.getByRole('tab').evaluateAll(tabs => new Set(tabs.map(tab => Math.round(tab.getBoundingClientRect().top))).size);
        assert(tabRows === 1, `${label}: architecture tabs wrap into ${tabRows} rows`);
        await dialog.screenshot({ path: join(shots, `${label.replaceAll('/', '-')}-architecture.png`) });
        await context.close();
      }
    }
  }
} finally {
  await browser.close();
}
writeFileSync(join(shots, 'report.json'), JSON.stringify({ base, mode, checks, errors }, null, 2));
console.log(`Foundation screenshots and report: ${shots}`);
if (errors.length) {
  console.error(errors.join('\n'));
  process.exitCode = 1;
} else console.log(`Foundation rendered QA PASS: ${checks.length} route checks across desktop/phone, EN/ES and light/dark.`);
