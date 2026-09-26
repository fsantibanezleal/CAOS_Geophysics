/** Route, tab, architecture, mobile controls and rendered screenshot audit. */
import { chromium } from '@playwright/test';
import { mkdirSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const base = process.env.QA_BASE ?? 'http://127.0.0.1:5179';
const output = process.env.QA_OUTPUT ? resolve(process.env.QA_OUTPUT) : mkdtempSync(join(tmpdir(), 'geophysics-frontend-qa-'));
mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader'] });
const failures = [];
const screenshots = [];

async function capture(page, name) {
  const path = join(output, `${name}.png`);
  await page.screenshot({ path, fullPage: false });
  screenshots.push(path);
}
async function openPage(width, height) {
  const context = await browser.newContext({ viewport: { width, height } });
  const page = await context.newPage();
  page.on('pageerror', error => failures.push(String(error)));
  page.on('response', response => { if (response.status() >= 400) failures.push(`${response.status()} ${response.url()}`); });
  return { page, context };
}
async function tabs(page, route) {
  const outer = page.locator('main [role="tablist"]:visible').first();
  if (!await outer.count()) return;
  const count = await outer.getByRole('tab').count();
  for (let i = 0; i < count; i++) {
    const tab = outer.getByRole('tab').nth(i);
    const name = await tab.textContent();
    await tab.click();
    if (await tab.getAttribute('aria-selected') !== 'true') failures.push(`${route}: tab ${name} not selected`);
    const nested = page.locator('main [role="tablist"]:visible').nth(1);
    if (!await nested.count()) continue;
    const subCount = await nested.getByRole('tab').count();
    for (let j = 0; j < subCount; j++) {
      const sub = nested.getByRole('tab').nth(j);
      await sub.click();
      if (await sub.getAttribute('aria-selected') !== 'true') failures.push(`${route}: nested tab ${j} not selected`);
      const visibleText = await page.locator('main [role="tabpanel"]:visible').last().innerText();
      if (visibleText.length < 20) failures.push(`${route}: nested tab ${j} empty`);
    }
  }
  console.log('TABS', JSON.stringify({ route, outer: count }));
}
async function architecture(page, language) {
  const label = language === 'es' ? 'Arquitectura / Cómo funciona' : 'Architecture / How it works';
  await page.getByRole('button', { name: label, exact: true }).click();
  const dialog = page.getByRole('dialog', { name: label });
  await dialog.waitFor();
  const tabs = dialog.getByRole('tab');
  const count = await tabs.count();
  for (let i = 0; i < count; i++) {
    await tabs.nth(i).click();
    await dialog.locator('svg').first().waitFor({ state: 'visible' });
    if (!await dialog.getByRole('tabpanel').innerText()) failures.push(`Architecture ${language} tab ${i} lacks explanation`);
  }
  await dialog.getByRole('button', { name: language === 'es' ? 'cerrar' : 'close' }).click();
  console.log('ARCHITECTURE', JSON.stringify({ language, tabs: count }));
}

const desktop = await openPage(1600, 900);
for (const route of ['', 'introduction', 'methodology', 'implementation', 'experiments', 'benchmark']) {
  await desktop.page.goto(`${base}/${route}`, { waitUntil: 'networkidle' });
  await desktop.page.locator('main h1').first().waitFor();
  await tabs(desktop.page, route || 'app');
  if (route === 'experiments') {
    await desktop.page.getByRole('tab', { name: 'MT forward and EDI evidence', exact: true }).click();
    await desktop.page.getByRole('tab', { name: 'EDI fixtures and inversion', exact: true }).click();
    await desktop.page.getByText('Original synthetic EDI fixture', { exact: true }).first().waitFor();
    const manifest = await (await desktop.page.request.get(`${base}/data/v2/edi/manifest.json`)).json();
    if (manifest.field_screens?.length) {
      const measured = desktop.page.locator('[data-source-kind="measured-edi-screen"]');
      await measured.waitFor();
      if (await measured.getByText('No 1D inversion was performed').count() !== 1) failures.push('Measured EDI no-inverse status missing');
      if (await measured.getByText('Selected final model').count()) failures.push('Measured EDI incorrectly shows inverse model');
      await measured.scrollIntoViewIfNeeded();
      await capture(desktop.page, 'desktop-measured-edi');
      await measured.locator('.science-plot').first().scrollIntoViewIfNeeded();
      await capture(desktop.page, 'desktop-measured-edi-plots');
    } else console.log('MEASURED_EDI', 'canonical field screen not in this checkout');
    await capture(desktop.page, 'desktop-edi');
    await desktop.page.locator('.science-plot').first().scrollIntoViewIfNeeded();
    await capture(desktop.page, 'desktop-edi-plots');
  }
}
await desktop.page.goto(base, { waitUntil: 'networkidle' });
await capture(desktop.page, 'desktop-workbench');
await architecture(desktop.page, 'en');
await desktop.context.close();

const mobile = await openPage(390, 844);
await mobile.page.goto(base, { waitUntil: 'networkidle' });
await mobile.page.getByRole('button', { name: 'Switch language' }).click();
await mobile.page.getByRole('button', { name: 'Cambiar claro / oscuro' }).click();
await capture(mobile.page, 'mobile-es-dark-workbench');
await mobile.page.getByRole('button', { name: /Controles de experimento y método/ }).click();
const expanded = await mobile.page.evaluate(() => {
  const rail = document.querySelector('.instrument-sidebar');
  return { viewport: [innerWidth, innerHeight], document: [document.documentElement.scrollWidth, document.documentElement.scrollHeight], rail: [rail.clientHeight, rail.scrollHeight] };
});
if (expanded.document[0] !== 390 || expanded.document[1] !== 844) failures.push(`Mobile expanded document overflow ${expanded.document}`);
if (expanded.rail[1] > expanded.rail[0] + 1) failures.push(`Mobile expanded rail scroll ${expanded.rail}`);
await capture(mobile.page, 'mobile-es-dark-expanded');
for (const name of ['Reproducción', 'Evidencia', 'Experimento']) {
  const button = mobile.page.getByRole('group', { name: 'Secciones de control' }).getByRole('button', { name, exact: true });
  await button.click();
  if (await button.getAttribute('aria-pressed') !== 'true') failures.push(`Mobile ${name} panel not selected`);
}
await mobile.page.getByRole('button', { name: /Cerrar controles/ }).click();
await architecture(mobile.page, 'es');
await mobile.context.close();
await browser.close();
console.log('SCREENSHOTS', JSON.stringify(screenshots));
console.log('MOBILE_EXPANDED', JSON.stringify(expanded));
console.log('FAILURES', JSON.stringify(failures));
if (failures.length) process.exitCode = 1;
