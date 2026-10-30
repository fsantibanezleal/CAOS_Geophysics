/** Rendered viewport, condition, and transfer audit against a local preview. */
import { chromium } from '@playwright/test';
import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const base = (process.env.QA_BASE ?? 'http://127.0.0.1:5179').replace(/\/+$/, '');
const output = resolve(process.env.QA_OUTPUT ?? '../data/experiments/browser-viewport');
mkdirSync(output, { recursive: true });
const launchBrowser = () => chromium.launch({ headless: true, args: ['--use-angle=swiftshader'] });
const failures = [];
const measurements = [];
const performanceRows = [];
const caseVariations = [];
const progress = { family: null, variant: null, completedFamilies: 0, completedConditions: 0 };
const reportPath = resolve(output, 'report.json');
const writeReport = () => writeFileSync(reportPath, JSON.stringify({ base, measurements, performanceRows, caseVariations, progress, failures }, null, 2));
const recordHarnessError = (error) => {
  failures.push(`${progress.family ?? 'layout'}/${progress.variant ?? 'setup'}: ${error?.stack ?? String(error)}`);
  writeReport();
  console.error('QA_HARNESS_ERROR', error);
  process.exit(1);
};
process.on('uncaughtException', recordHarnessError);
process.on('unhandledRejection', recordHarnessError);
const defaultFamilies = [
  'GRAVITY_INTRUSION', 'GRAVITY_DEEP_BODY', 'GRAVITY_NOISY', 'GRAVITY_TILTED',
  'MAGNETIC_DYKE', 'MAGNETIC_REMANENCE', 'MAGNETIC_DEEP', 'MAGNETIC_NOISY',
  'MT_RESISTIVE', 'MT_CONDUCTIVE', 'MT_MIXED', 'MT_NOISY',
  'FWI_LAYERED', 'FWI_FAULT', 'FWI_CYCLE_SKIP', 'FWI_NOISY',
  'JOINT_SHARED', 'JOINT_CONFLICT', 'LEARNED_CNN', 'LEARNED_AUTOENCODER',
];
const families = (process.env.QA_CASE_FAMILIES ?? defaultFamilies.join(','))
  .split(',').map(value => value.trim()).filter(Boolean);
const variants = ['reference', 'contrast', 'noise', 'acquisition', 'coverage', 'regularization'];
const layoutViewports = (process.env.QA_LAYOUT_VIEWPORTS ?? '1280x800,1600x900,2560x1440')
  .split(',').map(value => value.trim().split('x').map(Number));

async function paint(page) {
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function transferSummary(responses) {
  const completed = await Promise.all(responses.map(async (response) => {
    try {
      await response.finished();
      const sizes = await response.request().sizes();
      return { url: response.url().slice(base.length), bodyBytes: sizes.responseBodySize, headerBytes: sizes.responseHeadersSize };
    } catch { return null; }
  }));
  const entries = completed.filter(Boolean);
  return { bodyBytes: entries.reduce((sum, entry) => sum + entry.bodyBytes, 0),
    headerBytes: entries.reduce((sum, entry) => sum + entry.headerBytes, 0),
    requests: entries.length,
    largest: entries.sort((a, b) => b.bodyBytes - a.bodyBytes).slice(0, 5) };
}

async function createPage(browser, width, height, theme) {
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
  await context.addInitScript((chosen) => {
    localStorage.setItem('caos.theme', chosen);
    localStorage.setItem('caos.lang', 'en');
  }, theme);
  const page = await context.newPage();
  page.on('pageerror', (error) => {
    if (page.url() !== 'about:blank') failures.push(`${width}x${height} ${theme}: ${String(error)}`);
  });
  page.on('response', (response) => {
    if (response.status() >= 400) failures.push(`${width}x${height} ${theme}: HTTP ${response.status()} ${response.url()}`);
  });
  return { page, context };
}

async function layout(page, name, width, height, theme) {
  const value = await page.evaluate(() => {
    const doc = document.documentElement;
    const rail = document.querySelector('.instrument-sidebar');
    const rect = (element) => {
      const r = element.getBoundingClientRect();
      return { width: Math.round(r.width), height: Math.round(r.height), area: Math.round(r.width * r.height) };
    };
    const views = [...document.querySelectorAll('.earth-scene, .wave-stage, .mt-view, .layer-stack, .science-plot, .heatmap-area')]
      .filter((element) => {
        const r = element.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && r.top < innerHeight && r.bottom > 0;
      }).map((element) => ({ selector: element.className, ...rect(element) }));
    const tabRows = [...document.querySelectorAll('[role="tablist"]')].filter((list) => list.getAttribute('aria-orientation') !== 'vertical').map((list) =>
      new Set([...list.querySelectorAll('[role="tab"]')].map((tab) => Math.round(tab.getBoundingClientRect().top))).size);
    return {
      theme: doc.dataset.theme,
      viewport: [innerWidth, innerHeight],
      document: [doc.scrollWidth, doc.scrollHeight],
      rail: rail ? { height: rail.clientHeight, content: rail.scrollHeight } : null,
      tabRows,
      views: views.sort((a, b) => b.area - a.area).slice(0, 3),
    };
  });
  measurements.push({ name, width, height, theme, ...value });
  if (value.theme !== theme) failures.push(`${name}: requested ${theme}, rendered ${value.theme}`);
  if (value.document[0] !== width || value.document[1] !== height)
    failures.push(`${name}: document ${value.document.join('x')} != viewport ${width}x${height}`);
  if (value.tabRows.some((rows) => rows > 1)) failures.push(`${name}: wrapped tab row ${value.tabRows.join(',')}`);
  if (value.rail && value.rail.content > value.rail.height + 1)
    failures.push(`${name}: rail content ${value.rail.content}px > ${value.rail.height}px`);
  if (name.includes('/ model') && value.views[0] && value.views[0].area / (width * height) < 0.5)
    failures.push(`${name}: largest visualization ${(100 * value.views[0].area / (width * height)).toFixed(1)}% < 50%`);
  console.log('LAYOUT', JSON.stringify(measurements.at(-1)));
}

for (const [width, height] of layoutViewports) {
  for (const theme of ['light', 'dark']) {
    const browser = await launchBrowser();
    const { page, context } = await createPage(browser, width, height, theme);
    page.setDefaultNavigationTimeout(60000);
    await page.goto(`${base}/app`, { waitUntil: 'domcontentloaded' });
    await page.locator('.earth-scene canvas').waitFor();
    await layout(page, 'app / model', width, height, theme);
    for (const route of ['introduction', 'methodology', 'implementation', 'experiments', 'benchmark']) {
      await page.goto(`${base}/${route}`, { waitUntil: 'domcontentloaded' });
      await page.locator('main h1').waitFor();
      await layout(page, route, width, height, theme);
    }
    await page.goto('about:blank');
    await context.close();
    await browser.close();
  }
}

for (const [width, height] of [[390, 844], [1600, 900]]) {
  const browser = await launchBrowser();
  const { page, context } = await createPage(browser, width, height, 'light');
  page.setDefaultNavigationTimeout(60000);
  const transfers = [];
  page.on('response', (response) => { if (response.url().startsWith(base)) transfers.push(response); });
  let start = performance.now();
  await page.goto(`${base}/app`, { waitUntil: 'domcontentloaded' });
  await page.locator('.earth-scene canvas').waitFor();
  await paint(page);
  const defaultMs = Math.round(performance.now() - start);
  await page.waitForLoadState('networkidle');
  const defaultTransfer = await transferSummary(transfers);
  const defaultCanvas = await page.locator('.earth-scene canvas').evaluate((canvas) => ({ width: canvas.width, height: canvas.height }));
  performanceRows.push({ width, case: 'GRAVITY_INTRUSION', firstPaintReadyMs: defaultMs, ...defaultTransfer, canvas: defaultCanvas });
  console.log('PERFORMANCE', JSON.stringify(performanceRows.at(-1)));
  transfers.length = 0;
  start = performance.now();
  await page.getByRole('combobox', { name: 'Geological case', exact: true }).selectOption('FWI_LAYERED');
  await page.locator('.seismic-view canvas').first().waitFor();
  await page.getByText('Loading numerical result…').waitFor({ state: 'hidden' });
  await paint(page);
  const fwiMs = Math.round(performance.now() - start);
  await page.waitForLoadState('networkidle');
  const fwiTransfer = await transferSummary(transfers);
  const fwiCanvas = await page.locator('.seismic-view canvas').first().evaluate((canvas) => ({ width: canvas.width, height: canvas.height }));
  performanceRows.push({ width, case: 'FWI_LAYERED', firstPaintReadyMs: fwiMs, incrementalTransfer: fwiTransfer, canvas: fwiCanvas });
  console.log('PERFORMANCE', JSON.stringify(performanceRows.at(-1)));
  await page.goto('about:blank');
  await context.close();
  await browser.close();
}

const rendered = { gravity: '.earth-scene', magnetics: '.earth-scene', mt: '.mt-view', seismic: '.seismic-view', joint: '.earth-scene', learned: '.learned-view' };
for (const id of families) {
  progress.family = id;
  progress.variant = null;
  writeReport();
  // Release every case's Three.js/WebGL resources before loading another case.
  // A single 120-condition page accumulates SwiftShader allocations until
  // Chromium loses the context, which turns an otherwise useful matrix into a
  // timeout rather than a scientific/UI finding.
  const browser = await launchBrowser();
  const { page, context } = await createPage(browser, 1600, 900, 'light');
  page.setDefaultNavigationTimeout(60000);
  const conditionResponses = new Map();
  page.on('response', (response) => {
    const match = response.url().match(/\/data\/v2\/([A-Z_]+)\/(reference|contrast|noise|acquisition|coverage|regularization)\.json(?:\.gz)?$/);
    if (match) conditionResponses.set(`${match[1]}/${match[2]}`, response);
  });
  await page.goto(`${base}/app`, { waitUntil: 'domcontentloaded' });
  await page.locator('.earth-scene canvas').waitFor();
  if (await page.getByRole('combobox', { name: 'Geological case', exact: true }).inputValue() !== id) await Promise.all([
    page.waitForResponse((response) => response.url().endsWith(`/data/v2/${id}/reference.json`) || response.url().endsWith(`/data/v2/${id}/reference.json.gz`)),
    page.getByRole('combobox', { name: 'Geological case', exact: true }).selectOption(id),
  ]);
  const visualHashes = new Set();
  const metricHashes = new Set();
  for (const variant of variants) {
    progress.variant = variant;
    writeReport();
    let experimentControl = page.locator('[data-control="experiment"]');
    if (!await experimentControl.count()) {
      const openControls = page.getByRole('button', { name: 'Experiment controls', exact: true });
      if (await openControls.count()) await openControls.click();
      if (!await page.locator('[data-control="experiment"]').count())
        await page.getByRole('button', { name: 'Experiment', exact: true }).click();
      experimentControl = page.locator('[data-control="experiment"]');
      await experimentControl.waitFor({ state: 'visible' });
    }
    if (variant !== 'reference') await Promise.all([
      page.waitForResponse((response) => response.url().endsWith(`/data/v2/${id}/${variant}.json`) || response.url().endsWith(`/data/v2/${id}/${variant}.json.gz`)),
      experimentControl.selectOption(variant),
    ]);
    await page.getByText('Loading numerical result…').waitFor({ state: 'hidden' });
    await paint(page);
    const alert = await page.locator('main [role="alert"]').allTextContents();
    if (alert.length) failures.push(`${id}/${variant}: ${alert.join(' ')}`);
    // Some non-spatial workflows close the compact controls after hydrating a
    // result. The requested artifact response below is the authoritative
    // selection evidence; requiring the transient select to remain mounted
    // incorrectly fails those layouts.
    const artifact = conditionResponses.get(`${id}/${variant}`);
    if (!artifact) failures.push(`${id}/${variant}: no matching artifact response`);
    // Chromium evicts large FWI response bodies from the inspector cache after
    // navigation. The observed browser request proves hydration; independently
    // fetch its URL for the identity/metric assertion without that cache limit.
    const run = artifact ? await (await fetch(artifact.url())).json() : null;
    if (run && (run.id !== id || run.variant !== variant)) failures.push(`${id}/${variant}: artifact identity ${run.id}/${run.variant}`);
    const methodCount = Object.keys(run?.methods ?? {}).length;
    if (methodCount < 1) failures.push(`${id}/${variant}: artifact has no implemented methods`);
    if (id === 'LEARNED_AUTOENCODER') {
      const verdict = run?.methods?.autoencoder?.evaluation;
      if (verdict?.status !== 'unresolved' || !verdict.reason_codes?.includes('case-score-not-calibrated-as-geology'))
        failures.push(`${id}/${variant}: calibrated-geology limitation is absent from the method record`);
    }
    const viz = page.locator(rendered[id.startsWith('GRAVITY') ? 'gravity' : id.startsWith('MAGNETIC') ? 'magnetics' : id.startsWith('MT_') ? 'mt' : id.startsWith('FWI') ? 'seismic' : id.startsWith('JOINT') ? 'joint' : 'learned']).first();
    await viz.waitFor({ state: 'visible' });
    if (variant === 'reference' && /^(GRAVITY|MAGNETIC|JOINT)/.test(id) && Number(await viz.getAttribute('data-visible-cells')) < 1)
      failures.push(`${id}/reference: no model cells above the default physical threshold`);
    const visualHash = createHash('sha256').update(await viz.screenshot()).digest('hex').slice(0, 12);
    visualHashes.add(visualHash);
    const metrics = Object.fromEntries(Object.entries(run?.methods ?? {}).map(([method, value]) => [method, value.metrics ?? {}]));
    const metricHash = createHash('sha256').update(JSON.stringify(metrics)).digest('hex').slice(0, 12);
    metricHashes.add(metricHash);
    console.log('CONDITION', JSON.stringify({ id, variant, methods: methodCount, visualHash, metricHash, metricCount: Object.keys(metrics).length }));
    progress.completedConditions++;
    writeReport();
  }
  if (visualHashes.size < 2) failures.push(`${id}: all six rendered visualizations identical`);
  caseVariations.push({ id, distinctVisuals: visualHashes.size, distinctMetricViews: metricHashes.size });
  progress.completedFamilies++;
  progress.family = null;
  progress.variant = null;
  writeReport();
  console.log('FAMILY_VARIATION', JSON.stringify(caseVariations.at(-1)));
  await page.goto('about:blank');
  await context.close();
  await browser.close();
}
writeFileSync(reportPath, JSON.stringify({ base, measurements, performanceRows, caseVariations, progress, failures }, null, 2));
console.log('FAILURES', JSON.stringify(failures));
if (failures.length) process.exitCode = 1;
