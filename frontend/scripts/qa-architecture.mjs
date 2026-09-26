/** Render and gate the five ADR-0058 SVGs in both shell themes and languages.
 * Start `npm run preview -- --port 5179`, then run `node scripts/qa-architecture.mjs`.
 * Screenshots go to the OS temp directory, never the repository.
 */
import { chromium } from '@playwright/test';
import { readFileSync, mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const frontend = resolve(here, '..');
const base = process.env.QA_BASE ?? 'http://127.0.0.1:5179';
const files = ['01-the-app.svg', '02-lanes.svg', '03-web-flow.svg', '04-the-science.svg', '05-data-contracts.svg'];
const labels = [
  'Geophysical models, result structure, and build lifecycle',
  'Offline computation, artifact bridge, static hosts, and browser execution lanes',
  'Browser control dependency graph for selecting, replaying, viewing, and exporting geophysical results',
  'Forward, inverse, joint, and learned geophysics methods with validation limits',
  'Input and release data contracts separating local survey, measured EDI, and synthetic cases',
];
const raw = files.map((file) => readFileSync(join(frontend, 'public/svg/tech', file), 'utf8'));
const shots = process.env.QA_OUTPUT ? resolve(process.env.QA_OUTPUT) : mkdtempSync(join(tmpdir(), 'geophysics-architecture-'));
mkdirSync(shots, { recursive: true });
const errors = [];
const checks = [];

raw.forEach((svg, i) => {
  if (/#[0-9a-f]{3,8}\b/i.test(svg)) errors.push(`${files[i]}: hard-coded colour`);
  if (!/class="arch-svg"/.test(svg) || !/width="880"/.test(svg)) errors.push(`${files[i]}: ADR canvas missing`);
  if ((svg.match(/class="bx\b/g) ?? []).length < 5) errors.push(`${files[i]}: fewer than five semantic boxes`);
  if (!svg.includes('var(--color-') || !svg.includes('class="flow"') || !svg.includes('class="cd'))
    errors.push(`${files[i]}: token/flow/code-path vocabulary missing`);
});

const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader'] });
try {
  for (const theme of ['light', 'dark']) {
    for (const lang of ['en', 'es']) {
      const context = await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
      await context.addInitScript(({ theme, lang }) => {
        localStorage.setItem('caos.theme', theme);
        localStorage.setItem('caos.lang', lang);
      }, { theme, lang });
      const page = await context.newPage();
      page.on('pageerror', (error) => errors.push(`${theme}/${lang}: ${error.message}`));
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      await page.locator('button[aria-label*="rchitecture"], button[aria-label*="rquitectura"]').first().click();
      const dialog = page.getByRole('dialog');
      await dialog.waitFor();
      const shell = await page.evaluate(() => document.documentElement.dataset.theme);
      if (shell !== theme) errors.push(`${theme}/${lang}: shell theme is ${shell}`);
      for (let i = 0; i < files.length; i++) {
        await dialog.getByRole('tab').nth(i).click();
        const panel = dialog.getByRole('tabpanel');
        const svg = panel.locator(`svg.arch-svg[aria-label="${labels[i]}"]`);
        await svg.waitFor();
        const result = await svg.evaluate((root, requested) => {
          const lang = root.closest('[data-arch-lang]')?.getAttribute('data-arch-lang');
          const texts = [...root.querySelectorAll('text')];
          const rects = [...root.querySelectorAll('rect')].map((rect) => ({
            x: Number(rect.getAttribute('x') ?? 0), y: Number(rect.getAttribute('y') ?? 0),
            w: Number(rect.getAttribute('width')), h: Number(rect.getAttribute('height')),
          }));
          const groups = new Map();
          const violations = [];
          let visibleEn = 0, visibleEs = 0;
          for (const node of texts) {
            const kind = ['l-en', 'l-es', 'l-neutral'].filter((c) => node.classList.contains(c));
            if (kind.length !== 1) violations.push(`untagged/ambiguous text: ${node.textContent}`);
            if (kind[0] !== 'l-neutral') {
              const key = `${node.getAttribute('x')}|${node.getAttribute('y')}|${node.parentElement?.getAttribute('transform') ?? ''}`;
              const slot = groups.get(key) ?? {};
              slot[kind[0]] = node.textContent;
              groups.set(key, slot);
            }
            if (getComputedStyle(node).display === 'none') continue;
            if (kind[0] === 'l-en') visibleEn++;
            if (kind[0] === 'l-es') visibleEs++;
            const box = node.getBBox();
            const vb = root.viewBox.baseVal;
            if (box.x < 12 || box.y < 0 || box.x + box.width > vb.width - 12 || box.y + box.height > vb.height - 1)
              violations.push(`canvas overflow: ${node.textContent}`);
            // The smallest rect containing the text origin is its semantic card; band nesting is intentional.
            const x = Number(node.getAttribute('x')), y = Number(node.getAttribute('y'));
            const card = rects.filter((r) => x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h)
              .sort((a, b) => a.w * a.h - b.w * b.h)[0];
            if (card && (box.x + box.width > card.x + card.w - 5 || box.y + box.height > card.y + card.h - 3))
              violations.push(`card overflow: ${node.textContent}`);
          }
          for (const [xy, pair] of groups) {
            if (!pair['l-en'] || !pair['l-es']) violations.push(`unpaired ${xy}`);
            else if (pair['l-en'] === pair['l-es']) violations.push(`identical translation ${xy}: ${pair['l-en']}`);
          }
          if (lang !== requested) violations.push(`panel language ${lang}`);
          if (requested === 'en' ? visibleEn < 15 || visibleEs !== 0 : visibleEs < 15 || visibleEn !== 0)
            violations.push(`visible labels en=${visibleEn} es=${visibleEs}`);
          return { pairs: groups.size, visibleEn, visibleEs, violations };
        }, lang);
        for (const violation of result.violations) errors.push(`${files[i]} ${theme}/${lang}: ${violation}`);
        checks.push({ file: files[i], theme, lang, pairs: result.pairs, visibleLabels: lang === 'en' ? result.visibleEn : result.visibleEs, violations: result.violations });
        if (i === 0 && lang === 'es') {
          const title = await dialog.getByRole('tab').first().innerText();
          if (!/Modelos físicos/.test(title)) errors.push(`Spanish tab did not change: ${title}`);
        }
        console.log(JSON.stringify({ file: files[i], theme, lang, pairs: result.pairs, visible: lang === 'en' ? result.visibleEn : result.visibleEs, issues: result.violations.length }));
        await dialog.screenshot({ path: join(shots, `${String(i + 1).padStart(2, '0')}-modal-${theme}-${lang}.png`) });
        // Full drawing, not just the clipped modal viewport: inspect exact shell tokens and all labels.
        const standalone = await context.newPage();
        await standalone.setContent(`<html data-theme="${theme}"><body style="margin:0;padding:16px;background:var(--color-bg)"><div data-arch-lang="${lang}">${raw[i]}</div></body></html>`);
        await standalone.addStyleTag({ path: join(frontend, 'node_modules/@fasl-work/caos-app-shell/styles.css') });
        await standalone.locator('svg').screenshot({ path: join(shots, `${String(i + 1).padStart(2, '0')}-${theme}-${lang}.png`) });
        await standalone.close();
      }
      await context.close();
      const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
      await mobile.addInitScript(({ theme, lang }) => {
        localStorage.setItem('caos.theme', theme);
        localStorage.setItem('caos.lang', lang);
      }, { theme, lang });
      const phone = await mobile.newPage();
      await phone.goto(base, { waitUntil: 'domcontentloaded' });
      await phone.locator('button[aria-label*="rchitecture"], button[aria-label*="rquitectura"]').first().click();
      for (let i = 0; i < files.length; i++) {
        const dialog = phone.getByRole('dialog');
        await dialog.getByRole('tab').nth(i).click();
        await dialog.locator(`svg.arch-svg[aria-label="${labels[i]}"]`).waitFor();
        await dialog.getByRole('button', { name: lang === 'es' ? 'Leer a tamaño completo' : 'Read at full size' }).click();
        const widths = await dialog.locator('[role="region"]').evaluate((region) => {
          region.scrollLeft = region.scrollWidth - region.clientWidth;
          return {
            client: region.clientWidth,
            scroll: region.scrollWidth,
            reachedRight: region.scrollLeft,
            diagram: region.querySelector('.caos-architecture-diagram')?.getBoundingClientRect().width,
          };
        });
        if (!(widths.scroll > widths.client && widths.reachedRight > 0 && Math.abs(widths.diagram - 880) < 2))
          errors.push(`${files[i]} mobile ${theme}/${lang}: full-size scroll ${JSON.stringify(widths)}`);
        if (i === 3) await dialog.screenshot({ path: join(shots, `04-modal-mobile-${theme}-${lang}.png`) });
      }
      await mobile.close();
    }
  }
} finally {
  await browser.close();
}
writeFileSync(join(shots, 'report.json'), JSON.stringify({ base, checks, mobileFullSizeInteractions: 20, errors }, null, 2));
console.log(`Architecture screenshots: ${shots}`);
if (errors.length) {
  console.error(errors.join('\n'));
  process.exitCode = 1;
} else {
  console.log('Architecture SVG / i18n / bounds / modal QA PASS (20 desktop renders + 20 mobile full-size interactions).');
}
