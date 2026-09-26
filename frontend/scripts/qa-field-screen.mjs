/** Render the published measured-EDI screen from candidate artifacts. */
import { chromium } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const base = process.env.QA_BASE ?? 'http://127.0.0.1:5179';
const output = resolve(process.env.QA_OUTPUT ?? '../data/experiments/browser-field-screen');
mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader'] });
const rows = [];
const errors = [];
try {
  for (const item of [
    { name: 'desktop-en-light', width: 1440, height: 960, lang: 'en', theme: 'light' },
    { name: 'mobile-es-dark', width: 390, height: 844, lang: 'es', theme: 'dark' },
  ]) {
    const context = await browser.newContext({ viewport: { width: item.width, height: item.height } });
    await context.addInitScript(({ lang, theme }) => {
      localStorage.setItem('caos.lang', lang);
      localStorage.setItem('caos.theme', theme);
    }, item);
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(`${item.name}: ${error}`));
    page.on('response', response => { if (response.status() >= 400) errors.push(`${item.name}: HTTP ${response.status()} ${response.url()}`); });
    await page.goto(`${base}/experiments`, { waitUntil: 'networkidle' });
    await page.getByRole('tab', { name: item.lang === 'es' ? 'MT directo y evidencia EDI' : 'MT forward and EDI evidence', exact: true }).click();
    await page.getByRole('tab', { name: item.lang === 'es' ? 'Archivos EDI e inversión' : 'EDI fixtures and inversion', exact: true }).click();
    const screen = page.locator('[data-source-kind="measured-edi-screen"]');
    await screen.waitFor();
    if (await screen.getByText('WRMS Zxx').count() !== 1) errors.push(`${item.name}: missing measured tensor score`);
    if (await screen.getByText('42', { exact: true }).count() !== 1) errors.push(`${item.name}: frequency count is not 42`);
    if (await screen.getByText('No', { exact: true }).count() < 1) errors.push(`${item.name}: screen does not disclose absent inversion`);
    const link = screen.locator('a[href="https://doi.org/10.5066/P14KAQ3M"]');
    if (await link.count() !== 1) errors.push(`${item.name}: missing USGS release DOI link`);
    const measured = await screen.evaluate(element => ({ text: element.textContent, width: element.getBoundingClientRect().width }));
    if (!measured.text.includes('267.6')) errors.push(`${item.name}: measured antisymmetry score absent`);
    await screen.scrollIntoViewIfNeeded();
    const layout = await page.evaluate(() => {
      const box = document.querySelector('[data-source-kind="measured-edi-screen"]').getBoundingClientRect();
      return { documentWidth: document.documentElement.scrollWidth, documentHeight: document.documentElement.scrollHeight,
        screenTop: Math.round(box.top + scrollY), screenHeight: Math.round(box.height) };
    });
    await page.screenshot({ path: resolve(output, `${item.name}.png`), fullPage: false });
    rows.push({ ...item, screenWidth: measured.width, ...layout });
    await context.close();
  }
} finally {
  await browser.close();
}
writeFileSync(resolve(output, 'report.json'), JSON.stringify({ rows, errors }, null, 2));
if (errors.length) throw new Error(errors.join('\n'));
console.log('Measured EDI screen rendered with source DOI, failed 1D criterion and no field inversion', JSON.stringify(rows));
