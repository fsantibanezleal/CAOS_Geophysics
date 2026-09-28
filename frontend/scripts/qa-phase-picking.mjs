/** Local built-preview gate for source-backed M08/M13 content. No picker is executed. */
import { chromium } from '@playwright/test';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const base = process.env.QA_BASE ?? 'http://127.0.0.1:5179';
const output = process.env.QA_OUTPUT ? resolve(process.env.QA_OUTPUT) : mkdtempSync(join(tmpdir(), 'geophysics-phase-content-'));
const errors = [];
const checks = [];
function assert(ok, message) { if (!ok) errors.push(message); }

async function pointerClick(page, locator) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (!box) throw new Error('Visible navigation target has no bounds');
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 5 });
  await page.mouse.down();
  await page.mouse.up();
}

async function tab(page, list, name) {
  const target = page.getByRole('tablist', { name: list }).getByRole('tab', { name });
  await pointerClick(page, target);
  assert(await target.getAttribute('aria-selected') === 'true', `${list}: ${name} did not activate`);
}

async function inspect(page, label, method, view, lang) {
  const article = page.locator(`article[data-picker="${method}"][data-view="${view}"]`);
  await article.locator('h2').waitFor();
  await article.locator('h2').scrollIntoViewIfNeeded();
  const groups = page.getByRole('tablist', { name: view === 'theory'
    ? (lang === 'es' ? 'Grupos de metodología' : 'Methodology groups')
    : (lang === 'es' ? 'Grupos de algoritmos' : 'Algorithm groups') });
  assert(await groups.evaluate(list => [...list.children].every(tab => {
    const bounds = list.getBoundingClientRect();
    const rect = tab.getBoundingClientRect();
    return rect.left >= bounds.left && rect.right <= bounds.right;
  })), `${label}: selected group displaces a peer outside the visible tab strip`);
  const state = await page.evaluate(() => ({
    width: document.documentElement.scrollWidth,
    viewport: innerWidth,
    height: document.documentElement.scrollHeight,
    viewportHeight: innerHeight,
    theme: document.documentElement.dataset.theme,
  }));
  assert(state.width <= state.viewport, `${label}: horizontal overflow ${state.width}/${state.viewport}`);
  assert(state.height <= state.viewportHeight + 1, `${label}: document taller than viewport ${state.height}/${state.viewportHeight}`);
  assert(await article.locator('p').count() >= 4, `${label}: shallow content`);
  assert(await article.locator('.equation').count() >= 2, `${label}: missing equations`);
  assert(await article.locator('.equation-caption').count() >= 2, `${label}: missing equation captions`);
  assert(await article.locator('svg.method-diagram[role="img"]').count() === 1, `${label}: missing original method schematic`);
  assert(await article.locator('button').count() === 0, `${label}: unexpected runnable control`);
  assert((await article.locator('.callout-honest .callout-body').innerText()).length > 100, `${label}: limitation callout absent`);
  const text = await article.innerText();
  assert(text.includes(method.toUpperCase()) || (method === 'm08' && text.includes('STA/LTA')),
    `${label}: method identity absent`);
  if (method === 'm08') {
    assert(text.includes('STA/LTA') && text.includes('m/s') && text.includes('UTC'), `${label}: M08 units or trigger explanation absent`);
  } else {
    assert(text.includes('100 Hz') && text.includes('3001') && text.includes('softmax'), `${label}: M13 reference architecture absent`);
    assert(text.includes(lang === 'es' ? 'no' : 'not'), `${label}: M13 non-claim absent`);
  }
  const refs = await article.locator('a[href^="https://doi.org/"], a[href^="https://docs.obspy.org/"], a[href^="https://github.com/AI4EPS/"]').count();
  assert(refs >= 2, `${label}: scoped primary references absent`);
  checks.push({ label, method, view, ...state, paragraphs: await article.locator('p').count(), equations: await article.locator('.equation').count(), refs });
  await page.screenshot({ path: join(output, `${label}.png`) });
  if (label.startsWith('desktop-light-en') || label.startsWith('phone-dark-es'))
    await article.locator('figure.figure').screenshot({ path: join(output, `${label}-diagram.png`) });
}

const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader'] });
try {
  for (const viewport of [{ name: 'desktop', width: 1600, height: 900 }, { name: 'phone', width: 390, height: 844 }]) {
    for (const theme of ['light', 'dark']) for (const lang of ['en', 'es']) {
      const label = `${viewport.name}-${theme}-${lang}`;
      const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, reducedMotion: 'reduce' });
      await context.addInitScript(({ theme, lang }) => {
        localStorage.setItem('caos.theme', theme);
        localStorage.setItem('caos.lang', lang);
      }, { theme, lang });
      const page = await context.newPage();
      page.on('pageerror', error => errors.push(`${label}: ${error.message}`));
      page.on('response', response => { if (response.status() >= 400 && response.url().startsWith(base)) errors.push(`${label}: HTTP ${response.status()} ${response.url()}`); });
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      await pointerClick(page, page.locator('nav.main-nav a').filter({ hasText: lang === 'es' ? 'Metodología' : 'Methodology' }).first());
      await page.waitForURL('**/methodology');
      const methods = lang === 'es' ? 'Grupos de metodología' : 'Methodology groups';
      const methodList = page.getByRole('tablist', { name: methods });
      await methodList.waitFor({ state: 'visible' });
      const methodTabs = methodList.locator(':scope > [role="tab"]');
      assert(await methodTabs.count() === 3, `${label}: methodology needs three groups`);
      assert(await methodTabs.evaluateAll(tabs => new Set(tabs.map(tab => Math.round(tab.getBoundingClientRect().top))).size) === 1,
        `${label}: methodology group tabs wrap`);
      assert(await methodList.evaluate(list => [...list.children].every(tab => {
        const bounds = list.getBoundingClientRect();
        const rect = tab.getBoundingClientRect();
        return rect.left >= bounds.left && rect.right <= bounds.right;
      })), `${label}: methodology group clipped`);
      await tab(page, lang === 'es' ? 'Métodos de campos y MT' : 'Field and MT methods', lang === 'es' ? 'Inversión estructural y petrofísica' : 'Structural and petrophysical inversion');
      assert(await page.getByRole('heading', { level: 2, name: lang === 'es' ? 'Inversión estructural y petrofísica' : 'Structural and petrophysical inversion' }).count() === 1,
        `${label}: released joint methodology lost`);
      await tab(page, methods, lang === 'es' ? 'Ondas' : 'Waves');
      await tab(page, lang === 'es' ? 'Métodos de ondas' : 'Waveform methods', lang === 'es' ? 'M08 · Llegadas P/S clásicas' : 'M08 · Classical P/S arrivals');
      await inspect(page, `${label}-methodology-m08`, 'm08', 'theory', lang);
      await tab(page, methods, lang === 'es' ? 'Aprendizaje' : 'Learning');
      await tab(page, lang === 'es' ? 'Métodos aprendidos' : 'Learned methods', lang === 'es' ? 'M13 · Detección P/S aprendida' : 'M13 · Learned P/S picking');
      await inspect(page, `${label}-methodology-m13`, 'm13', 'theory', lang);

      await pointerClick(page, page.locator('nav.main-nav a').filter({ hasText: lang === 'es' ? 'Implementación' : 'Implementation' }).first());
      await page.waitForURL('**/implementation');
      const algorithms = lang === 'es' ? 'Grupos de algoritmos' : 'Algorithm groups';
      const algorithmList = page.getByRole('tablist', { name: algorithms });
      await algorithmList.waitFor({ state: 'visible' });
      const algorithmTabs = algorithmList.locator(':scope > [role="tab"]');
      assert(await algorithmTabs.count() === 4, `${label}: implementation needs four groups`);
      assert(await algorithmTabs.evaluateAll(tabs => new Set(tabs.map(tab => Math.round(tab.getBoundingClientRect().top))).size) === 1,
        `${label}: implementation group tabs wrap`);
      assert(await algorithmList.evaluate(list => [...list.children].every(tab => {
        const bounds = list.getBoundingClientRect();
        const rect = tab.getBoundingClientRect();
        return rect.left >= bounds.left && rect.right <= bounds.right;
      })), `${label}: implementation group clipped`);
      await tab(page, lang === 'es' ? 'Algoritmos de campos por método' : 'Field algorithms by method', lang === 'es' ? 'Inversión estructural y petrofísica' : 'Structural and petrophysical inversion');
      await tab(page, lang === 'es' ? 'Algoritmos numéricos' : 'Numerical algorithms', lang === 'es' ? 'Inversión petrofísica de mezcla gaussiana' : 'Gaussian-mixture petrophysical inversion');
      assert(await page.getByRole('heading', { level: 2, name: lang === 'es' ? 'Inversión petrofísica de mezcla gaussiana' : 'Gaussian-mixture petrophysical inversion' }).count() === 1,
        `${label}: released joint algorithm lost`);
      await tab(page, algorithms, lang === 'es' ? 'Ondas' : 'Waves');
      await tab(page, lang === 'es' ? 'Algoritmos de ondas' : 'Waveform algorithms', lang === 'es' ? 'M08 · Llegadas P/S clásicas' : 'M08 · Classical P/S arrivals');
      await inspect(page, `${label}-implementation-m08`, 'm08', 'implementation', lang);
      await tab(page, algorithms, lang === 'es' ? 'Redes' : 'Models');
      await tab(page, lang === 'es' ? 'Algoritmos neuronales' : 'Neural algorithms', lang === 'es' ? 'M13 · Detección P/S aprendida' : 'M13 · Learned P/S picking');
      await inspect(page, `${label}-implementation-m13`, 'm13', 'implementation', lang);
      await context.close();
    }
  }
} finally {
  await browser.close();
}
writeFileSync(join(output, 'report.json'), JSON.stringify({ base, checks, errors }, null, 2));
console.log(`Phase-picking content screenshots and report: ${output}`);
if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
else console.log(`Phase-picking content rendered QA PASS: ${checks.length} views across desktop/phone, EN/ES and light/dark.`);
