// caos-shell-gate runner: measures a built CAOS product in a real browser and fails on what a reader would meet.
// Every check embeds a trap recorded in the 2026-10-04 failure history (failure class 10: gates that measured the
// wrong thing); the self-test in this repository plants one defect per check and requires each to fail (G15).
//
//   G1 subject identity      the brand must match --expect-brand; a check that finds no subject fails
//   G2 mode identity         theme and language set with the shell's own storage keys, then read back
//   G3 errors                console.error, page errors, any GET answered 400 or above
//   G4 deep links            every route loaded directly (and with a trailing slash), 200 and rendered; artifacts
//                            are JSON, not the HTML fallback; a missing asset answers 404; doc text clears a floor
//   G5 scroll and reach      boxes inside the viewport, the rail and their scrollers; tall views scroll; nothing is
//                            cut; truncated text carries its full text; a select shows its whole selected text (0.17.0); every control reachable by the pointer
//   G6 painted area          drawing surfaces have painted pixels, fill their stage, and cover at least half the
//                            viewport on the App route, measured on the screenshot, never on a host box
//   G7 walk everything       every route, tab, sub-tab and case, at five sizes, both themes, both languages,
//                            waiting for declared state (data-state, data-stale, data-drawn), never networkidle
//   G8 idle at rest          no sustained animation frames or DOM mutations after load and after a tab switch
//   G9 reactivity            each registered control changes the selection key and no view keeps an old one; the
//                            rendered case is the case asked for; a disabled control is not moved
//   G10 text in drawings     every label of a chart, an instrument SVG or a document figure inside the drawing and
//                            clear of the others, also when every page is rendered in a wider fallback font (the
//                            wide-font pass: Verdana, else DejaVu Sans, the Linux runner's font)
//   G11 Spanish numbers      a page in Spanish writes no decimal point (canvas text excepted)
//   G12 sticky lists         a vertical sub-tab list is still in view at the end of a long section
//   G13 contrast             every visible text at WCAG AA against the colour behind it (primary size, both themes; first language, and every language on a documentation route)
//   G14 captures index       gate-output/index.html shows every capture by route and mode, the failures first
//   G16 flip cards, decks    a flip card is a small card (title and back within the limits), a real button that turns with Enter and
//                            Space, its hidden face out of the accessibility tree; a carousel reaches every card, never scrolls sideways
//   G17 animated drawings    an animated SVG has its reduced-motion block, plays for 10 s at most and is still under reduced motion
//   G18 Focus mode           the App's Focus control opens the case's open group in the full viewport and returns to the same case and
//                            group (by the exit control and by Escape); no page scroll, the rail without scroll, one tab row; no stage
//                            control under the Focus chrome (label, HUD, actions); no Focus control inside the Focus frame
//                            on a surface App (--workbench '', --app-route; 0.16.0) the same for the views of its tab row: another view or
//                            sub-view in Focus or after the return, no ?focus=1 and view in the URL, no view that offers the control
//   G19 values whole         a short value (number, percentage, amount, unit) sits on one line in every state
//   G20 chart interactions   every chart is one tab stop with an accessible name, described by a table of its values and a one-line summary,
//                            and a zoomed chart resets (the + key zooms, the visible control shows, the 0 key resets); a chart that turns zoom
//                            off says why (12 letters and digits at least) and is listed among the waivers (0.19.0)
// plus the ADR-0071 and ADR-0017 measures (viewport, one-row tabs, rail without scroll, centred prose, captions,
// references).

import { existsSync, mkdirSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { decodePng, paintedBox, unionArea } from './png.mjs';
import { servePages } from './serve.mjs';
import { installLib } from './inpage.mjs';
import { DOC_ROUTES, FLIP_LIMITS, analyseSvgAnimation, animationFailures, docFloorFailures } from './areas.mjs';

export const DEFAULTS = {
  sizes: '390x844,768x1024,1280x800,1600x900,2560x1440',
  themes: 'light,dark',
  langs: 'en,es',
  workbench: '/app',
  appRoute: '/app',
  idleMs: 3000,
  settleMs: 15000,
  textFloor: 400,
  instrumentMin: 0.5,
  stageFillMin: 0.3,
  stageFloor: 140,
  viewportMinWidth: 1280,
  out: 'gate-output',
  maxShots: 40,
  wideFont: true,
  wideFontSizes: '390x844,1280x800',
  requireFocus: false,
};

/** The wide fallback font of the G10 pass: wider than the Windows and macOS sans fonts; DejaVu Sans is what a Linux
 * reader (and the CI runner) gets. Applied before the first frame, so a drawing that measures its text measures it. */
const WIDE_FONT = ':root, :root[data-theme] { --font-sans: Verdana, "DejaVu Sans", sans-serif !important; }';

const RATE_LIMIT = 5; // frames or mutations per second at rest above which a loop is reported (G8)

async function loadKeys() {
  try {
    return await import('@fasl-work/caos-app-shell/keys');
  } catch {
    throw new Error('caos-shell-gate: could not load the pinned shell package public ./keys export');
  }
}

/**
 * @param {object} o options (see bin/caos-shell-gate.mjs)
 * @returns {Promise<object>} the report; `report.ok` is false on any failure
 */
export async function runGate(o) {
  const opt = { ...DEFAULTS, ...o };
  if (!opt.expectBrand) throw new Error('caos-shell-gate: --expect-brand is required (G1: the gate never measures an unnamed subject)');
  if (!opt.url && !opt.serve) throw new Error('caos-shell-gate: --url or --serve is required (there is no default target)');
  let chromium;
  try {
    ({ chromium } = await import('playwright'));
  } catch {
    throw new Error('caos-shell-gate: install playwright in this project (npm i -D playwright) to run the gate');
  }
  const { THEME_STORAGE_KEY, LANG_STORAGE_KEY } = await loadKeys();

  const sizes = String(opt.sizes).split(',').map((s) => s.trim().split('x').map(Number));
  const themes = String(opt.themes).split(',').map((s) => s.trim());
  const langs = String(opt.langs).split(',').map((s) => s.trim());
  const workbenchRoute = String(opt.workbench).split(',')[0].trim() || '/app';
  // the App route of a product whose App is a surface (`--workbench ''`): G18 measures its Focus mode (shell 0.16.0)
  const appRoute = String(opt.appRoute ?? '').trim() || '/app';
  const workbenchRoutes = new Set(String(opt.workbench).split(',').map((s) => s.trim()).filter(Boolean));
  const primarySize = sizes.find(([w]) => w >= opt.viewportMinWidth) ?? sizes[0];
  const shotsDir = join(opt.out, 'shots');
  // Every run starts from an empty capture folder: a capture left by an earlier run is stale evidence.
  rmSync(shotsDir, { recursive: true, force: true });
  mkdirSync(shotsDir, { recursive: true });

  let server = null;
  let base = opt.url;
  if (opt.serve) {
    server = await servePages(opt.serve, opt.basePath ?? '/', 0, { spaFallback: Boolean(opt.spaFallback) });
    base = server.url;
  }
  base = base.endsWith('/') ? base : `${base}/`;
  const basePath = new URL(base).pathname;
  const urlFor = (route) => new URL(route.replace(/^\//, ''), base).href;
  const routeOf = (href) => {
    const p = new URL(href, base).pathname;
    return p.startsWith(basePath) ? `/${p.slice(basePath.length)}`.replace(/\/$/, '') || '/' : null;
  };

  const failures = [];
  const focusReported = new Set(); // G18: an App without a Focus control is reported once per route and mode
  const waivers = []; // ADR-0017 2.1: every waiver a documentation page declares, with its verdict
  // The smallest measured values against each floor, so a pass shows its margin (and a CI font change that eats it
  // is visible before it fails).
  const minima = { drawnShare: null, stageFill: null };
  const low = (k, value, where) => {
    if (minima[k] === null || value < minima[k].value) minima[k] = { value: Number(value.toFixed(4)), route: where.route, mode: where.mode, trail: where.trail };
  };
  let shots = 0;
  let states = 0;
  const fail = (check, where, message) => failures.push({ check, route: where.route ?? '', mode: where.mode ?? '', trail: where.trail ?? '', message });
  const artifacts = new Set();
  const artifactMeasurements = [];

  const browser = await chromium.launch();
  const openContext = async ([w, h], theme, lang, wide = false) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    if (wide) {
      await ctx.addInitScript((css) => {
        const add = () => {
          const st = document.createElement('style');
          st.setAttribute('data-caos-gate-font', '');
          st.textContent = css;
          document.documentElement.appendChild(st);
        };
        if (document.documentElement) add();
        else
          new MutationObserver((_, o) => {
            if (document.documentElement) {
              o.disconnect();
              add();
            }
          }).observe(document, { childList: true });
      }, WIDE_FONT);
    }
    await ctx.addInitScript(
      ([tk, lk, t, l]) => {
        try {
          localStorage.setItem(tk, t);
          localStorage.setItem(lk, l);
        } catch {
          /* storage unavailable: G2 reports the mode that came back */
        }
      },
      [THEME_STORAGE_KEY, LANG_STORAGE_KEY, theme, lang],
    );
    await ctx.addInitScript(installLib);
    return ctx;
  };

  const newPage = async (ctx) => {
    const page = await ctx.newPage();
    const sink = [];
    page.on('console', (m) => {
      if (m.type() === 'error') sink.push(`console.error: ${m.text().slice(0, 300)}`);
    });
    page.on('pageerror', (e) => sink.push(`page error: ${String(e).slice(0, 300)}`));
    page.on('response', (r) => {
      const req = r.request();
      if (req.method() !== 'GET') return;
      if (r.status() >= 400) sink.push(`HTTP ${r.status()} for ${r.url()}`);
      const type = req.resourceType();
      let pathname = '';
      try {
        pathname = new URL(r.url()).pathname;
      } catch {
        /* not a URL */
      }
      if ((type === 'fetch' || type === 'xhr') && pathname.endsWith('.json') && r.status() < 400 && !artifacts.has(pathname)) {
        artifacts.add(pathname);
      }
    });
    return { page, sink };
  };

  const settle = async (page) => {
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r(null))))).catch(() => undefined);
    const t0 = Date.now();
    let last = 'timeout';
    let streak = 0;
    while (Date.now() - t0 < opt.settleMs) {
      const why = await page.evaluate(() => (window.__caosGate && window.__caosGate.ready ? window.__caosGate.ready() : 'the gate library is not installed')).catch((e) => `evaluate failed: ${e.message}`);
      if (why === '') {
        streak += 1;
        if (streak >= 2) return '';
      } else {
        streak = 0;
        last = why;
      }
      await page.waitForTimeout(60);
    }
    return last;
  };

  const drain = (sink, where) => {
    for (const e of sink.splice(0)) fail('G3', where, e);
  };

  // Every route in every mode keeps its capture, for the person who reads them (the gate measures, it does not judge
  // content); only failure captures are capped, so a run with many failures does not fill the disk.
  const saveShot = async (page, name, failure = false) => {
    if (failure) {
      if (shots >= opt.maxShots) return;
      shots += 1;
    }
    await page.screenshot({ path: join(shotsDir, name) }).catch(() => undefined);
  };

  try {
    // ---- G4: a missing asset answers 404, not the HTML fallback.
    {
      const ctx = await browser.newContext();
      const res = await ctx.request.get(urlFor('/__caos_gate_missing__.json'), { maxRedirects: 0 }).catch((e) => ({ status: () => `error ${e.message}` }));
      if (res.status() !== 404) fail('G4', { route: '/__caos_gate_missing__.json' }, `a missing asset answered ${res.status()}, not 404 (an SPA fallback hides missing artifacts and broken deep links)`);
      await ctx.close();
    }

    // ---- G1: the subject, and the route list (from the header nav unless given).
    let routes = opt.routes ? String(opt.routes).split(',').map((r) => r.trim()).filter(Boolean) : null;
    {
      const ctx = await openContext(primarySize, themes[0], langs[0]);
      const { page, sink } = await newPage(ctx);
      await page.goto(urlFor('/'), { waitUntil: 'load', timeout: 30000 });
      const why = await settle(page);
      const id = await page.evaluate(() => window.__caosGate.identity());
      if (id.brand !== opt.expectBrand) {
        fail('G1', { route: '/' }, `the page at ${base} is "${id.brand ?? id.title}", not "${opt.expectBrand}"; nothing else is measured (a gate pointed at another product passes on it)`);
        await ctx.close();
        return finish();
      }
      if (why) fail('G7', { route: '/' }, `the landing route never settled: ${why}`);
      if (!routes) {
        const hrefs = await page.$$eval('header nav a[href]', (as) => as.map((a) => a.href));
        routes = [...new Set(hrefs.map(routeOf).filter(Boolean))];
      }
      sink.splice(0);
      await ctx.close();
    }

    // ---- G18 on a surface App: under --require-focus the App route must be among the measured routes, or nothing would be measured
    if (opt.requireFocus && workbenchRoutes.size === 0 && !routes.includes(appRoute)) {
      fail('G18', { route: appRoute, mode: 'routes' }, `the App route ${appRoute} is not among the measured routes (${routes.join(', ') || 'none'}): with --workbench '' and --require-focus the gate measures the App as a surface and must walk it; add it to --routes or name it with --app-route`);
    }

    // ---- G18 on a workbench App (shell 0.17.0): under --require-focus every workbench route must be among the measured routes, or no Focus would be measured
    if (opt.requireFocus) {
      for (const wr of workbenchRoutes) {
        if (!routes.includes(wr)) {
          fail('G18', { route: wr, mode: 'routes' }, `the workbench route ${wr} is not among the measured routes (${routes.join(', ') || 'none'}): with --require-focus the gate must walk the App to measure its Focus mode; add it to --routes or drop it from --workbench`);
        }
      }
    }

    // ---- Landing semantics follow the product contract: an Introduction landing when workbenchRoute is separate;
    //      a product whose approved App route is / opens that workbench directly.
    {
      const ctx = await openContext(primarySize, themes[0], langs[0]);
      const { page, sink } = await newPage(ctx);
      await page.goto(urlFor('/'), { waitUntil: 'load', timeout: 30000 }).catch(() => undefined);
      await settle(page);
      const at = { route: '/', mode: 'landing' };
      if (workbenchRoute === '/') {
        const rootFacts = await page.evaluate(() => window.__caosGate.facts());
        if (routeOf(page.url()) !== '/' || !rootFacts.workbench) fail('G4', at, `the approved root App did not render its workbench (reached ${routeOf(page.url()) ?? page.url()})`);
      } else if (routeOf(page.url()) !== '/introduction') {
        fail('G4', at, `the root opened ${routeOf(page.url()) ?? page.url()}, not the Introduction; every product lands on the Introduction (Landing of the shell on the root path)`);
      } else {
        const landed = await page.evaluate(() => window.__caosGate.docPage());
        if (!landed || landed.view !== 'executive' || !landed.executive || landed.executive.count !== 1) fail('G4', at, `the root opened the Introduction on the "${landed?.view ?? 'none'}" view; the landing opens its executive view`);
      }
      const old = await page.goto(`${urlFor('/')}?gate=landing#frag`, { waitUntil: 'load', timeout: 30000 }).catch(() => undefined);
      await settle(page);
      const u = new URL(page.url());
      if (routeOf(page.url()) !== workbenchRoute || u.searchParams.get('gate') !== 'landing' || u.hash !== '#frag') {
        fail('G4', { route: '/', mode: 'landing' }, `an old App link /?gate=landing#frag reached ${routeOf(page.url())}${u.search}${u.hash}; it must reach ${workbenchRoute} with its query string and hash kept (Landing keeps the query string and the hash)`);
      }
      void old;
      sink.splice(0);
      await ctx.close();
    }

    // ---- The walk: every mode, every route, every tab, every case (G2 to G9 and the ADR measures).
    for (const size of sizes) {
      for (const theme of themes) {
        for (const lang of langs) {
          const [w, h] = size;
          const mode = `${w}x${h} ${theme} ${lang}`;
          const primary = size === primarySize && theme === themes[0] && lang === langs[0];
          const idleHere = theme === themes[0] && lang === langs[0];
          const ctx = await openContext(size, theme, lang);
          const { page, sink } = await newPage(ctx);
          for (const route of routes) {
            const isWorkbench = workbenchRoutes.has(route);
            const at = { route, mode };
            // G13 runs in the first language; the documentation routes (the prose a reader reads) in every language
            const contrast = size === primarySize && (lang === langs[0] || DOC_ROUTES.includes(route));
            const res = await page.goto(urlFor(route), { waitUntil: 'load', timeout: 30000 }).catch((e) => e);
            const status = res && typeof res.status === 'function' ? res.status() : `error ${res?.message ?? res}`;
            if (status !== 200) {
              fail('G4', at, `loaded directly, ${urlFor(route)} answered ${status}`);
              drain(sink, at);
              continue;
            }
            const why = await settle(page);
            if (why) fail('G7', at, `never settled: ${why}`);
            const id = await page.evaluate(() => window.__caosGate.identity());
            if (id.brand !== opt.expectBrand) {
              fail('G1', at, `the route renders "${id.brand ?? id.title}", not "${opt.expectBrand}"`);
              drain(sink, at);
              continue;
            }
            if (id.theme !== theme) fail('G2', at, `asked for the ${theme} theme through ${THEME_STORAGE_KEY}; the document has data-theme=${id.theme}`);
            if (!String(id.lang ?? '').startsWith(lang)) fail('G2', at, `asked for ${lang} through ${LANG_STORAGE_KEY}; <html lang> is ${id.lang}`);
            if (id.activeHref && routeOf(id.activeHref) !== route) fail('G4', at, `loaded directly, the page shows route ${routeOf(id.activeHref)}`);

            // ADR-0017 2.1: the documentation floors are measured once per language, at the primary size and first theme
            const docFloors = size === primarySize && theme === themes[0] && DOC_ROUTES.includes(route);
            const walkState = { tested: new Set(), keyedViews: 0, controls: 0, tablists: 0, doc: docFloors ? [] : null };
            await processState(page, sink, { ...at, trail: '' }, { route, isWorkbench, primary, idle: idleHere, interact: idleHere, first: true, size, w, h, theme, lang, walkState, contrast });

            if (primary) {
              // G4: the trailing-slash form a static host serves for a materialised route.
              const slash = route === '/' ? urlFor(route) : `${urlFor(route)}/`;
              const r2 = await page.goto(slash, { waitUntil: 'load', timeout: 30000 }).catch((e) => e);
              const s2 = r2 && typeof r2.status === 'function' ? r2.status() : `error ${r2?.message ?? r2}`;
              if (s2 !== 200) fail('G4', at, `${slash} answered ${s2}`);
              else {
                await settle(page);
                const id2 = await page.evaluate(() => window.__caosGate.identity());
                if (id2.brand !== opt.expectBrand) fail('G4', at, `${slash} renders "${id2.brand ?? id2.title}"`);
                else if (id2.activeHref && routeOf(id2.activeHref) !== route) fail('G4', at, `${slash} shows route ${routeOf(id2.activeHref)}`);
              }
              drain(sink, { ...at, trail: 'trailing slash' });
              await page.goto(urlFor(route), { waitUntil: 'load', timeout: 30000 });
              await settle(page);
              sink.splice(0);
            }

            const leaves = await walkTabs(page, sink, { ...at }, [], new Set(), { route, isWorkbench, primary, idle: primary, interact: idleHere, size, w, h, theme, lang, walkState, contrast });
            if (walkState.doc) docResult(at, lang, walkState.doc, Math.max(1, leaves));

            if (isWorkbench) await walkCases(page, sink, at, { route, isWorkbench, primary, interact: idleHere, size, w, h, theme, lang, walkState, contrast });
            else if (workbenchRoutes.size === 0 && route === appRoute) await surfaceFocusWalk(page, sink, at, { route, isWorkbench, primary, interact: idleHere, size, w, h, theme, lang, walkState, contrast });

            if (primary && isWorkbench) {
              const f = await page.evaluate(() => window.__caosGate.facts());
              if (!f.workbench) fail('G9', at, 'no [data-case-workbench] on a workbench route');
              else if (!f.workbench.replayOnly) {
                if (walkState.controls === 0) fail('G9', at, 'the workbench has no registered control ([data-control]) and does not declare itself replay-only');
                if (walkState.keyedViews === 0) fail('G9', at, 'no view declares the selection key it shows (PlotCard or Readout dataKey); reactivity cannot be verified');
              }
              if (walkState.tablists === 0) fail('G7', at, 'the workbench shows no tab list to walk');
            }
          }

          if (primary) {
            // ADR-0071 rule 9 / G5: every header route reached by a real pointer click from the App route.
            for (const route of routes.filter((r) => r !== workbenchRoute)) {
              await page.goto(urlFor(workbenchRoute), { waitUntil: 'load', timeout: 30000 }).catch(() => undefined);
              await settle(page);
              const link = page.locator('header nav a[href]');
              const hrefs = await link.evaluateAll((as) => as.map((a) => a.href));
              const idx = hrefs.findIndex((href) => routeOf(href) === route);
              let ok = false;
              if (idx >= 0) {
                // A reader scrolls a narrow nav row to the link first; so does the gate, then clicks with the pointer.
                // A link that does not answer in time is a failure of this route, never an exception that ends the
                // whole run (a locator waited its default 30 s under load and aborted the gate, 0.9.0 self-test).
                await link.nth(idx).evaluate((el) => window.__caosGate.bringEl(el), undefined, { timeout: 10000 }).catch(() => undefined);
                const box = await link.nth(idx).boundingBox({ timeout: 10000 }).catch(() => null);
                if (box) {
                  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
                  await page.waitForURL((u) => routeOf(u.href) === route, { timeout: 3000 }).catch(() => undefined);
                  ok = routeOf(page.url()) === route;
                }
              }
              if (!ok) fail('G5', { route, mode }, 'not reachable by a pointer click on the header link from the App route');
              sink.splice(0);
            }
          }
          await ctx.close();
        }
      }
    }

    // ---- G10: the wide-font pass. Every route, tab and sampled case again, in Spanish (the longer labels) when it is
    // measured, rendered in the wide fallback font from the first frame: what a reader with wider fonts sees.
    if (opt.wideFont !== false && opt.wideFontSizes) {
      const wideSizes = String(opt.wideFontSizes).split(',').map((x) => x.trim()).filter(Boolean).map((x) => x.split('x').map(Number));
      const wlang = langs.includes('es') ? 'es' : langs[0];
      const theme = themes[0];
      for (const size of wideSizes) {
        const [w, h] = size;
        const mode = `${w}x${h} ${theme} ${wlang} wide-font`;
        const ctx = await openContext(size, theme, wlang, true);
        const { page, sink } = await newPage(ctx);
        for (const route of routes) {
          const isWorkbench = workbenchRoutes.has(route);
          const at = { route, mode };
          const res = await page.goto(urlFor(route), { waitUntil: 'load', timeout: 30000 }).catch((e) => e);
          const status = res && typeof res.status === 'function' ? res.status() : `error ${res?.message ?? res}`;
          if (status !== 200) {
            fail('G4', at, `loaded directly, ${urlFor(route)} answered ${status}`);
            drain(sink, at);
            continue;
          }
          const why = await settle(page);
          if (why) fail('G7', at, `never settled: ${why}`);
          const walkState = { tested: new Set(), keyedViews: 0, controls: 0, tablists: 0 };
          const s = { route, isWorkbench, primary: false, idle: false, size, w, h, theme, lang: wlang, walkState, wide: true };
          await processState(page, sink, { ...at, trail: '' }, { ...s, first: true });
          await walkTabs(page, sink, { ...at }, [], new Set(), s);
          if (isWorkbench) await walkCases(page, sink, at, s);
        }
        await ctx.close();
      }
    }

    // ---- G4: read JSON from the actual HTTP origin. Playwright can evict response bodies this large;
    //      this gate therefore performs a second real GET and measures its complete served body.
    const requiredFwi = ['FWI_LAYERED', 'FWI_FAULT', 'FWI_CYCLE_SKIP', 'FWI_NOISY'].map((id) => ({
      id,
      pathname: `/data/v2/${id}/reference.json`,
    }));
    for (const { id, pathname } of requiredFwi) {
      if (!artifacts.has(pathname)) fail('G4', { route: pathname }, `${id} was not fetched by the measured workbench states`);
    }
    const pathsToVerify = new Set([...artifacts, ...requiredFwi.map(({ pathname }) => pathname)]);
    for (const pathname of pathsToVerify) {
      try {
        const response = await fetch(urlFor(pathname));
        const body = Buffer.from(await response.arrayBuffer());
        const contentType = response.headers.get('content-type') ?? '';
        if (response.status !== 200) fail('G4', { route: pathname }, `the served JSON asset answered HTTP ${response.status}, expected 200`);
        if (!/^application\/json(?:\s*;|$)/i.test(contentType)) fail('G4', { route: pathname }, `the served asset Content-Type was "${contentType || '(missing)'}", expected application/json`);
        const declaredLength = response.headers.get('content-length');
        if (declaredLength !== null && Number(declaredLength) !== body.byteLength) {
          fail('G4', { route: pathname }, `the served body measured ${body.byteLength} bytes but Content-Length was ${declaredLength}`);
        }
        const parsed = JSON.parse(body.toString('utf8'));
        const fwi = requiredFwi.find((item) => item.pathname === pathname);
        if (fwi && (parsed.schema !== 'inverse-earth/v2' || parsed.id !== fwi.id)) {
          fail('G4', { route: pathname }, `the served JSON identity was schema=${parsed.schema ?? '(missing)'}, id=${parsed.id ?? '(missing)'}`);
        }
        artifactMeasurements.push({
          path: pathname,
          status: response.status,
          contentType,
          bytes: body.byteLength,
          sha256: createHash('sha256').update(body).digest('hex'),
          ...(fwi ? { id: fwi.id, schema: parsed.schema } : {}),
        });
      } catch (error) {
        fail('G4', { route: pathname }, `the served JSON response could not be read and parsed: ${error.message}`);
      }
    }
  } finally {
    await browser.close();
    if (server) await server.close();
  }
  return finish();

  // ------------------------------------------------------------------------------------------------------------
  async function processState(page, sink, where, s) {
    states += 1;
    // On a narrow screen the instrument stacks under the rail; a reader scrolls to the open view, and so does the gate.
    if (s.isWorkbench && s.w < opt.viewportMinWidth) {
      await page.evaluate(() => window.__caosGate.bring('[data-case-workbench] [role="tabpanel"]')).catch(() => undefined);
    }
    const f = await page.evaluate(() => window.__caosGate.facts());
    const big = s.w >= opt.viewportMinWidth;
    if (f.docW > f.vw + 1) fail('G5', where, `horizontal overflow: the document is ${f.docW}px wide in a ${f.vw}px viewport`);
    if (f.beyondCount) fail('G5', where, `${f.beyondCount} element(s) outside the viewport: ${f.beyond.join('; ')}`);
    if (big && f.docH > f.vh + 1) fail('ADR-0071.1', where, `the document scrolls: ${f.docH}px in a ${f.vh}px viewport (the page is the viewport)`);
    for (const r of f.rows) if (r.rows > 1) fail('ADR-0071.4', where, `tab row "${r.name}" wraps onto ${r.rows} rows`);
    for (const r of f.rows) if (r.cut > 1) fail('G5', where, `tab row "${r.name}" cuts its tabs by ${r.cut}px (a row shrunk under its panel)`);
    if (f.rail) {
      if (big && f.rail.scroll > f.rail.client + 1) fail('ADR-0071.6', where, `the rail scrolls: ${f.rail.scroll}px of content in ${f.rail.client}px`);
      if (f.rail.outsideCount) fail('G5', where, `${f.rail.outsideCount} rail element(s) outside the rail: ${f.rail.outside.join('; ')}`);
    }
    if (f.truncatedCount) fail('G5', where, `${f.truncatedCount} truncated text(s) without the full text in a title: ${f.truncated.join('; ')}`);
    if (f.cutSelectCount) fail('G5', where, `${f.cutSelectCount} select(s) cut the selected text (a case name cut in its box, or a display that names another case than the one the select holds, or a plain select with a text wider than its room): ${f.cutSelects.join('; ')}`);
    for (const c of f.clipped) fail('G5', where, c);
    if (f.offCentre !== null && f.offCentre > 2) fail('ADR-0017.1', where, `the prose page is off-centre by ${f.offCentre.toFixed(1)}px`);
    if (f.referenceLists) fail('ADR-0017.4', where, `${f.referenceLists} bibliography outside the end-of-page references block (a .reference-list); give each DocSection its refs and let the page list them once`);
    if (f.referencesNotLast) fail('ADR-0017.4', where, `${f.referencesNotLast} references block(s) with content after them; references must be the last block of the page or tab`);
    if (f.refsDeclaredNoBlock) fail('ADR-0017.4', where, `${f.refsDeclaredNoBlock} section(s) cite references the page never lists (no references block in their page or tab)`);
    if (f.uncaptioned) fail('ADR-0017.2', where, `${f.uncaptioned} equation(s) without a caption`);
    if (s.walkState?.doc) {
      const d = await page.evaluate(() => window.__caosGate.docPage());
      if (d) s.walkState.doc.push(d);
    }
    for (const r of f.repeatedTicks ?? []) {
      // named x ticks (UPlotChart declares the repeated names): a name used twice, wherever the two ticks sit on the axis
      if (r.names) fail('G6', where, `${r.label}: ${r.n} named x tick label(s) repeat another tick's label (${r.names.split('|').map((n) => `"${n}"`).join(', ')}); give every named tick a label of its own`);
      else fail('G6', where, `${r.label}: ${r.n} axis tick label(s) repeat the label before them (give the axis fixed decimals)`);
    }
    // G20 (0.19.0): every chart is a tab stop with a name, a table of its values, a summary and a reset; one that turns zoom off is listed with its reason
    for (const c of await page.evaluate((drive) => window.__caosGate.chartsTierA(drive), Boolean(s.interact))) {
      for (const m of c.problems) fail('G20', where, `${c.label} (${c.kind} chart): ${m}`);
      if (c.zoomOffSet) {
        // listed once per route and language (the first state), failed in every state while the reason is too short
        if (s.interact) waivers.push({ route: where.route, lang: s.lang, floor: 'chart zoom off', reason: c.zoomOff, valid: c.zoomOffValid });
        if (!c.zoomOffValid) fail('G20', where, `${c.label}: zoom is turned off with a reason of fewer than 12 letters and digits ("${c.zoomOff}"); say why the chart cannot be zoomed`);
      }
    }
    // a filling card whose note leaves its drawing under the floor (CAOS_APP_SHELL#95); below 1280 px the document scrolls
    if (big) for (const c of f.fillStages ?? []) if (c.h < opt.stageFloor) fail('G6', where, `the drawing of ${c.label} keeps ${Math.round(c.h)} px under its note (floor ${opt.stageFloor} px)`);
    for (const m of await page.evaluate(() => window.__caosGate.drawingText())) fail('G10', where, m);
    if (s.lang === 'es') for (const m of await page.evaluate(() => window.__caosGate.decimals())) fail('G11', where, m);
    for (const m of await page.evaluate(() => window.__caosGate.brokenValues())) fail('G19', where, m);
    if (s.w > 760) for (const m of await page.evaluate(() => window.__caosGate.sticky())) fail('G12', where, m);
    if (s.contrast) for (const m of await page.evaluate(() => window.__caosGate.contrast())) fail('G13', where, m);
    if (f.sectionsWithoutRefs) fail('ADR-0017.4', where, `${f.sectionsWithoutRefs} section(s) end without references or a stated reason`);
    if (s.first && !s.isWorkbench && f.pageText < opt.textFloor) fail('G4', where, `the page body holds ${f.pageText} characters of text (floor ${opt.textFloor}); the route rendered without its content`);

    if (s.isWorkbench) {
      if (!f.instrument) fail('G6', where, 'no [data-instrument] on a workbench route');
      else await paintedChecks(page, f, where, big);
      if (f.workbench && s.walkState) {
        const keyed = (await page.evaluate(() => window.__caosGate.views())).filter((v) => v.key);
        s.walkState.keyedViews += keyed.length;
      }
    }

    if (s.first) await saveShot(page, `${slug(s.route)}_${s.w}x${s.h}_${s.theme}_${s.lang}${s.wide ? '_wide' : ''}.png`);

    if (s.idle) {
      const idle = await page.evaluate((ms) => window.__caosGate.idle(ms), opt.idleMs);
      const secs = idle.ms / 1000;
      if (idle.raf / secs > RATE_LIMIT) fail('G8', where, `${idle.raf} animation frames in ${secs}s at rest (a loop runs with nothing to show)`);
      if (idle.mutations / secs > RATE_LIMIT) fail('G8', where, `${idle.mutations} DOM mutations in ${secs}s at rest: ${idle.sample.join('; ')}`);
    }

    for (const m of await page.evaluate(() => window.__caosGate.scrolls())) fail('G5', where, m);
    const reach = await page.evaluate(() => window.__caosGate.reach());
    if (reach.unreachableCount) fail('G5', where, `${reach.unreachableCount} control(s) not reachable by the pointer: ${reach.unreachable.join('; ')}`);

    await cardChecks(page, where, s);
    if (s.primary) await animationChecks(page, where);

    if (s.primary && s.isWorkbench && s.walkState) await reactivity(page, sink, where, s);
    drain(sink, where);
    const failedHere = failures.some((x) => x.route === where.route && x.mode === where.mode && x.trail === where.trail && x.check !== 'G3');
    if (failedHere) await saveShot(page, `fail_${slug(s.route)}_${s.w}x${s.h}_${s.theme}_${s.lang}${s.wide ? '_wide' : ''}_${shots + 1}.png`, true);
  }

  async function paintedChecks(page, f, where, big) {
    if (f.prose) return; // the context write-up is prose, measured as a document, not as a drawing
    if (f.surfaces.length === 0 && f.unavailable) {
      // a declared absence a reader can see and read (ADR-0080 decision 3): nothing to draw, every other check still ran
      if (f.drawn > 0) fail('G6', where, `a drawing is present but not visible beside a data-state="unavailable" note (${f.drawn} drawing element(s) rendered in the instrument, collapsed, hidden or too small to see): draw it, or remove it`);
      else if (f.unavailable === 'unexplained') fail('G6', where, 'the instrument declares data-state="unavailable" and draws nothing, but gives no reason (the text a reader sees needs at least 12 letters or digits in two words or more, saying why the data is absent)');
      else if (f.unavailable === 'unseen') fail('G6', where, 'the instrument declares data-state="unavailable" and draws nothing, but no reader can see the note (it needs a visible box of at least 40 x 12 px inside the instrument, not transparent, not clipped, not off-screen)');
      return;
    }
    if (f.surfaces.length === 0) {
      fail('G6', where, 'nothing is drawn in the instrument (no canvas, svg drawing, image or table)');
      return;
    }
    const clip = { x: Math.floor(f.instrument.x), y: Math.floor(f.instrument.y), width: Math.max(1, Math.floor(f.instrument.w)), height: Math.max(1, Math.floor(f.instrument.h)) };
    let img;
    try {
      img = decodePng(await page.screenshot({ clip }));
    } catch (e) {
      fail('G6', where, `the instrument could not be captured: ${e.message}`);
      return;
    }
    // Per stage: the painted extent of its drawings (union of their painted boxes), judged against the stage.
    const stages = new Map();
    for (const s of f.surfaces) {
      if (s.right > f.vw + 1) fail('G6', where, `${s.label} extends to ${Math.round(s.right)}px, past the ${f.vw}px page`);
      const st = stages.get(s.stageKey) ?? { label: s.label, kinds: new Set(), stage: s.stage, view: s.view, painted: [] };
      st.kinds.add(s.kind);
      const box = paintedBox(img, { x: s.x - clip.x, y: s.y - clip.y, w: s.w, h: s.h });
      if (box) st.painted.push({ x: box.x + clip.x, y: box.y + clip.y, w: box.w, h: box.h });
      stages.set(s.stageKey, st);
    }
    const counted = [];
    for (const st of stages.values()) {
      if (st.painted.length === 0) {
        fail('G6', where, `${st.label} (${[...st.kinds].join(', ')}, ${Math.round(st.stage.w)}x${Math.round(st.stage.h)}) is blank: nothing is painted on it`);
        continue;
      }
      const x0 = Math.min(...st.painted.map((b) => b.x));
      const y0 = Math.min(...st.painted.map((b) => b.y));
      const x1 = Math.max(...st.painted.map((b) => b.x + b.w));
      const y1 = Math.max(...st.painted.map((b) => b.y + b.h));
      const fill = ((x1 - x0) * (y1 - y0)) / Math.max(1, st.stage.w * st.stage.h);
      if (big) low('stageFill', fill, where);
      if (fill < opt.stageFillMin) {
        if (big) fail('G6', where, `${st.label} draws on ${(100 * fill).toFixed(0)}% of its stage (floor ${(100 * opt.stageFillMin).toFixed(0)}%)`);
        continue;
      }
      counted.push(st.view);
    }
    if (big) {
      // The instrument share counts only the views whose drawing passed: empty instrument space, and the cards of
      // blank or underfilled drawings, never count (ADR-0071 rule 8, measured on what is drawn).
      const share = unionArea(counted, f.vw, f.vh) / (f.vw * f.vh);
      low('drawnShare', share, where);
      if (share < opt.instrumentMin) fail('G6', where, `the drawn views cover ${(100 * share).toFixed(1)}% of the viewport (floor ${(100 * opt.instrumentMin).toFixed(0)}% on the App route, ADR-0071 rule 8)`);
    }
  }

  async function reactivity(page, sink, where, s) {
    const controls = await page.evaluate(() => window.__caosGate.controls());
    s.walkState.controls += controls.length;
    for (const c of controls) {
      if (s.walkState.tested.has(c.id)) continue;
      s.walkState.tested.add(c.id);
      const at = { ...where, trail: `${where.trail ? `${where.trail} > ` : ''}control ${c.id}` };
      const before = await workbenchKey(page);
      const changed = await changeControl(page, c).catch((e) => `error: ${e.message.split('\n')[0]}`);
      if (changed !== true) {
        fail('G9', at, `control "${c.id}" (${c.kind}) could not be changed: ${changed || 'no alternative value'}`);
        continue;
      }
      const why = await settle(page);
      if (why) {
        fail('G9', at, `after changing "${c.id}" the views did not settle: ${why}`);
        continue;
      }
      const after = await workbenchKey(page);
      if (after === before) fail('G9', at, `control "${c.id}" did not change the selection key (data-state-key stayed ${before})`);
      const old = (await page.evaluate(() => window.__caosGate.views())).filter((v) => v.key && v.key !== after);
      if (old.length) fail('G9', at, `${old.length} view(s) keep an earlier selection key after "${c.id}" changed: ${old.slice(0, 3).map((v) => v.label).join('; ')}`);
      drain(sink, at);
    }
  }

  /** Walks every tab of every list owned by `trail`; returns the number of leaf topics found (a tab with no list inside it is one; a list inside a documentation section adds none). */
  async function walkTabs(page, sink, where, trail, handled, s) {
    let leaves = 0;
    const lists = (await page.evaluate(() => window.__caosGate.tablists())).filter((l) => !handled.has(l.key) && !l.source);
    const parentKey = trail.length ? trail[trail.length - 1].key : null;
    const mine = lists.filter((l) => (parentKey ? l.owner === parentKey : l.owner === null));
    for (const tl of mine) {
      handled.add(tl.key);
      s.walkState.tablists += 1;
      for (let i = 0; i < tl.tabs.length; i += 1) {
        const label = tl.tabs[i];
        const here = [...trail, { key: tl.key, label }];
        const at = { ...where, trail: [...(where.case ? [`case ${where.case}`] : []), ...here.map((t) => t.label)].join(' > ') };
        if (i !== tl.active) {
          const tab = page.locator(tl.key).locator('[role="tab"]').filter({ visible: true }).nth(i);
          try {
            // a reader scrolls the tab clear of the sticky header first; so does the gate, then clicks it
            await tab.evaluate((el) => window.__caosGate.bringEl(el)).catch(() => undefined);
            await tab.click({ timeout: 5000 });
          } catch (e) {
            fail('G7', at, `the tab could not be clicked: ${e.message.split('\n')[0]}`);
            if (!tl.inSection) leaves += 1;
            continue;
          }
          const why = await settle(page);
          if (why) fail('G7', at, `never settled: ${why}`);
          await processState(page, sink, at, { ...s, first: false, idle: s.idle });
        }
        const inner = await walkTabs(page, sink, where, here, new Set(handled), s);
        // the tabs of a list inside a documentation section are visited, but they are parts of that section, not topics
        if (!tl.inSection) leaves += inner === 0 ? 1 : inner;
      }
      if (tl.active >= 0 && tl.tabs.length > 1) {
        await page.locator(tl.key).locator('[role="tab"]').filter({ visible: true }).nth(tl.active).click({ timeout: 5000 }).catch(() => undefined);
        await settle(page);
        sink.splice(0);
      }
    }
    return leaves;
  }

  /** ADR-0017 2.1: applies the area table (gate/areas.mjs) to what a documentation page showed in one language. */
  function docResult(at, lang, states, expectedTopics) {
    const r = docFloorFailures({ route: at.route, lang, states, expectedTopics });
    for (const f of r.failures) fail('ADR-0017.2', { ...at, trail: f.trail }, f.message);
    for (const w of r.waivers) waivers.push({ route: at.route, lang, ...w });
  }

  async function walkCases(page, sink, at, s) {
    const sources = (await page.evaluate(() => window.__caosGate.tablists())).find((l) => l.source);
    const sourceTabs = sources ? sources.tabs.map((_, i) => i) : [null];
    let total = 0;
    const sampleSet = opt.caseSample ? new Set(String(opt.caseSample).split(',').map((x) => x.trim())) : null;
    for (const si of sourceTabs) {
      if (si !== null && si !== sources.active) {
        await page.locator(sources.key).locator('[role="tab"]').nth(si).click({ timeout: 5000 }).catch(() => undefined);
        await settle(page);
      }
      const { kind, ids } = await page.evaluate(() => window.__caosGate.cases());
      total += ids.length;
      const pick = s.primary ? ids : sampleSet ? ids.filter((x) => sampleSet.has(x)) : [...new Set([ids[0], ids[ids.length - 1]])].filter(Boolean);
      for (const caseId of pick) {
        const where = { ...at, case: caseId, trail: `case ${caseId}` };
        try {
          if (kind === 'select') await page.locator('select[data-control="case"]').filter({ visible: true }).first().selectOption(caseId, { timeout: 5000 });
          else await page.locator(`[data-control="case"] [data-case="${caseId}"]`).filter({ visible: true }).first().click({ timeout: 5000 });
        } catch (e) {
          fail('G7', where, `the case could not be selected: ${e.message.split('\n')[0]}`);
          continue;
        }
        const why = await settle(page);
        if (why) fail('G7', where, `never settled: ${why}`);
        const shownCase = await page.evaluate(() => document.querySelector('[data-case-workbench]')?.getAttribute('data-case') ?? null);
        if (shownCase !== caseId) fail('G9', where, `asked for case ${caseId}; the workbench shows ${shownCase}`);
        await processState(page, sink, where, { ...s, first: false, idle: false });
        if (s.primary) await walkTabs(page, sink, where, [], new Set(), { ...s, idle: false });
        await focusVisit(page, sink, where, s, caseId, pickedIndex(pick, caseId), total);
      }
      if (s.primary && pick.length) {
        // A deep link selects the case it names (G9).
        const deep = pick[pick.length - 1];
        await page.goto(`${urlFor(s.route)}?case=${encodeURIComponent(deep)}`, { waitUntil: 'load', timeout: 30000 });
        await settle(page);
        const shownCase = await page.evaluate(() => document.querySelector('[data-case-workbench]')?.getAttribute('data-case') ?? null);
        if (shownCase !== deep) fail('G9', { ...at, trail: `?case=${deep}` }, `the deep link ?case=${deep} shows case ${shownCase}`);
        drain(sink, { ...at, trail: `?case=${deep}` });
        await page.goto(urlFor(s.route), { waitUntil: 'load', timeout: 30000 });
        await settle(page);
        sink.splice(0);
      }
    }
    if (total === 0 && !opt.singleCase) fail('G9', at, 'the workbench offers no case ([data-control="case"]); declare --single-case if it has one');
  }

  // ---------------------------------------------------------------------------------------------------- G16, G17, G18
  function pickedIndex(list, id) {
    return list.indexOf(id);
  }
  function idleAnimations(page) {
    return page.waitForFunction('document.getAnimations().filter((a) => a.transitionProperty === "transform" || a.transitionProperty === "visibility" || a.animationName === "caos-deck-in").length === 0', undefined, { timeout: 3000 }).catch(() => undefined);
  }

  /** G16: the flip cards and the card decks of the state (facts), and, in the first theme and language, their interactions. */
  async function cardChecks(page, where, s) {
    const f = await page.evaluate(() => window.__caosGate.cards());
    if (f.cards.length === 0 && f.decks.length === 0) return;
    for (const c of f.cards) {
      const tl = FLIP_LIMITS.title[f.lang];
      const bl = FLIP_LIMITS.back[f.lang];
      if (c.titleWords > tl) fail('G16', where, `flip card "${c.label}": a title of ${c.titleWords} words; the limit is ${tl} (${f.lang}); a flip card is a small card, a long one stays plain`);
      if (c.backWords > bl) fail('G16', where, `flip card "${c.label}": a back of ${c.backWords} words; the limit is ${bl} (${f.lang}); a flip card is a small card, a long one stays plain`);
      if (!c.buttons || !c.wired) fail('G16', where, `flip card "${c.label}": its faces are not real buttons with aria-expanded and aria-controls naming the back`);
      if (c.hiddenInTree) fail('G16', where, `flip card "${c.label}": the hidden ${c.open ? 'face' : 'back'} is in the accessibility tree (aria-hidden, inert or visibility must take it out)`);
      else if (c.hiddenFocusable) fail('G16', where, `flip card "${c.label}": the hidden ${c.open ? 'face' : 'back'} holds a control the keyboard reaches`);
    }
    for (const d of f.decks) {
      if (d.sideways) fail('G16', where, `card deck "${d.label}": the carousel scrolls sideways (${d.outside} card(s) past its box, the deck or its track wider than the page); it must page, never scroll`);
      if (d.docW > d.vw + 1) fail('G16', where, `card deck "${d.label}": the page is ${d.docW}px wide in a ${d.vw}px viewport`);
      if (d.mode === 'carousel' && d.visible.length === 0) fail('G16', where, `card deck "${d.label}": the carousel shows no card`);
      if (d.mode === 'carousel' && !d.controls) {
        for (let k = 0; k < d.total; k += 1) if (!d.visible.includes(k)) fail('G16', where, `card deck "${d.label}": card ${k + 1} of ${d.total} cannot be reached: the carousel hides it and shows no previous and next controls`);
      }
    }
    if (!s.interact) return;
    try {
      // a carousel pages through every card with its next button
      for (const d of f.decks) {
        if (d.mode !== 'carousel' || !d.controls) continue;
        const deck = page.locator('[data-card-deck]').nth(d.index);
        const reached = new Set(d.visible);
        let st = d;
        let guard = 0;
        while (!st.atStart && guard < d.total + 2) {
          await deck.locator('[data-deck-prev]').click({ timeout: 4000 });
          st = (await page.evaluate(() => window.__caosGate.cards())).decks[d.index];
          guard += 1;
        }
        for (const i of st.visible) reached.add(i);
        guard = 0;
        while (!st.atEnd && guard < d.total + 1) {
          await deck.locator('[data-deck-next]').click({ timeout: 4000 });
          await idleAnimations(page);
          st = (await page.evaluate(() => window.__caosGate.cards())).decks[d.index];
          for (const i of st.visible) reached.add(i);
          if (st.sideways) fail('G16', where, `card deck "${d.label}": the carousel scrolls sideways after the next button (${st.outside} card(s) past its box)`);
          guard += 1;
        }
        for (let k = 0; k < d.total; k += 1) if (!reached.has(k)) fail('G16', where, `card deck "${d.label}": card ${k + 1} of ${d.total} cannot be reached with the next button`);
        guard = 0;
        while (!st.atStart && guard < d.total + 2) {
          await deck.locator('[data-deck-prev]').click({ timeout: 4000 }).catch(() => undefined);
          st = (await page.evaluate(() => window.__caosGate.cards())).decks[d.index];
          guard += 1;
        }
      }
      // one flip card of each deck (and the loose ones): the face takes focus, Enter turns it, focus follows, Space turns it back
      const f2 = await page.evaluate(() => window.__caosGate.cards());
      const done = new Set();
      for (const c of f2.cards) {
        if (!c.shown || c.open || done.has(c.deck)) continue;
        done.add(c.deck);
        const card = page.locator('[data-flip-card]').nth(c.index);
        const toggle = card.locator('[data-flip-toggle="front"]');
        const focused = await toggle.evaluate((el) => { el.focus(); return document.activeElement === el; }).catch(() => false);
        if (!focused) {
          fail('G16', where, `flip card "${c.label}" does not turn with the keyboard: its face cannot take focus (it is not a button)`);
          continue;
        }
        await page.keyboard.press('Enter');
        await idleAnimations(page);
        const after = (await page.evaluate(() => window.__caosGate.cards())).cards[c.index];
        if (!after || !after.open) {
          fail('G16', where, `flip card "${c.label}" does not turn with the keyboard: Enter on its face left it closed`);
          continue;
        }
        const active = await page.evaluate(() => { const a = document.activeElement; return { visible: Boolean(a) && a.checkVisibility({ checkVisibilityCSS: true }), inCard: Boolean(a) && Boolean(a.closest('[data-flip-card]')) }; });
        if (!active.visible || !active.inCard) fail('G16', where, `flip card "${c.label}": after Enter, keyboard focus is not on a control of the face that shows`);
        if (after.hiddenInTree) fail('G16', where, `flip card "${c.label}": the hidden face is in the accessibility tree while the back shows`);
        if (!after.contentShown) fail('G16', where, `flip card "${c.label}": the back shows no content after it turns (its content has no visible box)`);
        if (s.contrast) for (const m of await page.evaluate(() => window.__caosGate.contrast())) fail('G13', where, `${m} (a flip card turned)`);
        if (!done.has('shot')) {
          done.add('shot');
          await saveShot(page, `flipcard_open_${slug(s.route)}_${s.w}x${s.h}_${s.theme}_${s.lang}.png`);
        }
        await page.keyboard.press('Space');
        await idleAnimations(page);
        const closed = (await page.evaluate(() => window.__caosGate.cards())).cards[c.index];
        if (!closed || closed.open) fail('G16', where, `flip card "${c.label}" does not turn back with the keyboard: Space on its back left it open`);
      }
    } catch (e) {
      fail('G16', where, `a flip card or a card deck could not be used: ${e.message.split('\n')[0]}`);
    }
  }

  /** G17: every animated SVG of the state has its reduced-motion block, plays for ten seconds at most and stands still under reduced motion. */
  async function animationChecks(page, where) {
    const a = await page.evaluate(() => window.__caosGate.animations());
    const animated = [];
    for (const it of a.items) {
      const analysis = analyseSvgAnimation(it.svg);
      for (const m of animationFailures(analysis, it.name)) fail('G17', where, m);
      if (analysis.animated) animated.push(it.name);
    }
    // a figure drawn by an img of an SVG file: the file is analysed (an img takes no page style, so its own block is what counts)
    const imgs = await page.evaluate(() => window.__caosGate.figureImages());
    for (const im of imgs) {
      const text = await page.evaluate(async (u) => { try { return await (await fetch(u)).text(); } catch (e) { return ''; } }, im.src);
      for (const m of animationFailures(analyseSvgAnimation(text), im.name)) fail('G17', where, m);
    }
    if (animated.length === 0) return;
    await page.emulateMedia({ reducedMotion: 'reduce' });
    try {
      await page.waitForTimeout(250);
      const b = await page.evaluate(() => window.__caosGate.animations());
      for (const it of b.items) {
        if (!animated.includes(it.name)) continue;
        if (it.runningCss > 0 || it.runningSmil) fail('G17', where, `illustration "${it.name}" keeps moving under reduced motion (${it.runningCss} CSS animation(s) running${it.smil ? `, SMIL ${it.runningSmil ? 'playing' : 'paused'}` : ''})`);
      }
    } finally {
      await page.emulateMedia({ reducedMotion: null });
    }
  }

  /**
   * G18: Focus mode of the cases, by clicking. The App is put on its last group, and on the last sub-view of a group that has
   * sub-views (the first group is where the walk leaves it, so a Focus that fell back to the first would go unseen); Focus must
   * open on that case, group and sub-view, keep the keyboard inside its frame, hold one landmark and return to the same place.
   */
  async function focusVisit(page, sink, where, s, caseId, index, total) {
    const enter = page.locator('[data-focus-enter]').filter({ visible: true }).first();
    if ((await enter.count()) === 0) {
      if (opt.requireFocus && !focusReported.has(`${s.route} ${where.mode}`)) {
        focusReported.add(`${s.route} ${where.mode}`);
        fail('G18', { ...where, trail: `case ${caseId} > Focus` }, 'the App offers no Focus control ([data-focus-enter]): ADR-0070 requires a visible control in the App that opens the selected case in focus mode');
      }
      return;
    }
    const tabs = page.locator('[data-case-workbench] [role="tablist"]').first().locator('[role="tab"]');
    const n = await tabs.count();
    const targets = n > 1 ? [n - 1] : [0];
    if (s.primary && n > 2) {
      // and the first group that holds sub-views
      for (let i = 0; i < n - 1; i += 1) {
        await tabs.nth(i).click({ timeout: 4000 }).catch(() => undefined);
        await settle(page);
        if ((await page.locator('[data-case-workbench] .subtablist').count()) > 0) {
          targets.push(i);
          break;
        }
      }
    }
    for (const [k, t] of targets.entries()) {
      await tabs.nth(t).click({ timeout: 4000 }).catch(() => undefined);
      await settle(page);
      const subs = page.locator('[data-case-workbench] .subtablist [role="tab"]');
      const sn = await subs.count();
      if (sn > 1) {
        await subs.nth(sn - 1).click({ timeout: 4000 }).catch(() => undefined);
        await settle(page);
      }
      await focusVisitOne(page, sink, where, s, { kind: 'case', id: caseId, total }, index + k, enter);
    }
    await tabs.nth(0).click({ timeout: 4000 }).catch(() => undefined);
    await settle(page);
  }

  async function focusVisitOne(page, sink, where, s, subject, index, enter) {
    const isView = subject.kind === 'view';
    const caseId = subject.id;
    const at = { ...where, trail: `${subject.kind} ${subject.id} > Focus` };
    const facts = () => page.evaluate(() => window.__caosGate.focusFacts());
    const label = `Focus mode of ${subject.kind} ${subject.id}`;
    const before = await facts();
    try {
      await enter.evaluate((el) => window.__caosGate.bringEl(el)).catch(() => undefined);
      await enter.click({ timeout: 5000 });
    } catch (e) {
      fail('G18', at, `${label}: the Focus control could not be clicked: ${e.message.split('\n')[0]}`);
      return;
    }
    const why = await settle(page);
    if (why) fail('G18', at, `${label}: never settled: ${why}`);
    const f = await facts();
    if (!f.focus) {
      fail('G18', at, `${label}: the Focus control did not open Focus mode`);
      return;
    }
    if (!isView && f.caseId !== caseId) fail('G18', at, `${label} shows case ${f.caseId}`);
    if (f.group !== before.group) fail('G18', at, `${label} shows ${isView ? 'view' : 'group'} ${f.group}, the App had ${before.group}`);
    if (f.subview !== before.subview) fail('G18', at, `${label} shows sub-view ${f.subview}, the App had ${before.subview}`);
    const q = new URLSearchParams(f.search);
    // the parameter the App holds Focus in (`focus`, or the product's own `param`), named by the Focus frame
    const fp = f.focusParam || 'focus';
    if (isView) {
      // the view the App held in its URL stays there (a surface that keeps its view out of the URL has none to keep)
      const param = before.viewParam || 'view';
      const held = new URLSearchParams(before.search).get(param);
      if (q.get(fp) !== '1' || (held !== null && q.get(param) !== held)) fail('G18', at, `${label}: the URL (${f.search || 'no query'}) does not hold ?${fp}=1 and the view (?${param}=)`);
    } else if (q.get(fp) !== '1' || (subject.total > 1 && q.get('case') !== caseId)) fail('G18', at, `${label}: the URL (${f.search || 'no query'}) does not hold ?${fp}=1 and the case`);
    if (f.docW > f.vw + 1 || f.docH > f.vh + 1) fail('G18', at, `${label}: the page scrolls (the document is ${f.docW}x${f.docH}px in a ${f.vw}x${f.vh}px viewport); Focus mode is the viewport`);
    if (f.nestedMain) fail('G18', at, `${label}: the page holds a main inside a main (the Focus frame must not be a second landmark inside the App's main)`);
    // the keyboard stays in the Focus frame: the App behind it is out of the tab order
    const strayed = [];
    for (let i = 0; i < 14; i += 1) {
      await page.keyboard.press('Tab');
      const where2 = await page.evaluate(() => { const a = document.activeElement; return !a || a === document.body || a.closest('[data-focus-shell]') ? '' : (a.getAttribute('aria-label') || a.textContent || a.tagName).trim().slice(0, 30); });
      if (where2) strayed.push(where2);
    }
    if (strayed.length) fail('G18', at, `${label}: Tab leaves the Focus frame (focus reached ${[...new Set(strayed)].slice(0, 4).map((x) => `"${x}"`).join(', ')} of the App behind it; make the rest of the page inert)`);
    const big = s.w >= opt.viewportMinWidth;
    if (big && f.rail && f.rail.scroll > f.rail.client + 1) fail('G18', at, `${label}: the rail scrolls (${f.rail.scroll}px of content in ${f.rail.client}px)`);
    if (f.tabRows.some((r) => r > 1)) fail('G18', at, `${label}: a tab row wraps onto ${Math.max(...f.tabRows)} rows`);
    if (big && f.share < opt.instrumentMin) fail('G18', at, `${label}: the stage covers ${(100 * f.share).toFixed(1)}% of the viewport (floor ${(100 * opt.instrumentMin).toFixed(0)}%)`);
    if (f.exitInside === false) fail('G18', at, `${label}: the exit control is outside the viewport`);
    for (const c of f.covered) fail('G18', at, `${label}: ${c.chrome} covers the control "${c.control}" (the stage must clear the Focus chrome)`);
    if (f.cutSelects.count) fail('G5', at, `${label}: ${f.cutSelects.count} select(s) cut the selected text (a case name cut in its box, or a display that names another case than the one the select holds, or a plain select with a text wider than its room): ${f.cutSelects.list.join('; ')}`);
    if (f.enterInside > 0) fail('G18', at, `${label}: the Focus control shows inside Focus mode (it opens the mode the reader is already in)`);
    for (const m of await page.evaluate(() => window.__caosGate.drawingText())) fail('G10', at, m);
    for (const m of await page.evaluate(() => window.__caosGate.brokenValues())) fail('G19', at, m);
    if (s.contrast) for (const m of await page.evaluate(() => window.__caosGate.contrast())) fail('G13', at, m);
    if (index === 0) await saveShot(page, `focus_${slug(s.route)}_${s.w}x${s.h}_${s.theme}_${s.lang}.png`);
    // leave: the exit control for one case, Escape for the next, so both ways are walked
    const byButton = index % 2 === 0;
    let left = true;
    if (byButton) {
      try {
        await page.locator('[data-focus-exit]').first().click({ timeout: 3000 });
      } catch (e) {
        fail('G18', at, `${label}: the exit control could not be used: ${e.message.split('\n')[0]}`);
        left = false;
      }
    } else {
      await page.keyboard.press('Escape');
    }
    if (!left) await page.keyboard.press('Escape');
    const why2 = await settle(page);
    if (why2) fail('G18', at, `${label}: never settled after leaving: ${why2}`);
    const g = await facts();
    if (g.focus) {
      fail('G18', at, `${label}: ${byButton && left ? 'the exit control' : 'Escape'} does not return to the App`);
      await page.goto(`${urlFor(s.route)}?${isView ? (before.viewParam || 'view') : 'case'}=${encodeURIComponent(caseId)}`, { waitUntil: 'load', timeout: 30000 }).catch(() => undefined);
      await settle(page);
    } else {
      if (!g.app) fail('G18', at, `${label}: back from Focus mode there is no App on the page`);
      if (!isView && g.caseId !== caseId) fail('G18', at, `${label}: back in the App on case ${g.caseId}, it was left on case ${caseId}`);
      if (g.group !== before.group) fail('G18', at, `${label}: back in the App on ${isView ? 'view' : 'group'} ${g.group}, it was left on ${isView ? 'view' : 'group'} ${before.group}`);
      if (g.subview !== before.subview) fail('G18', at, `${label}: back in the App on sub-view ${g.subview}, it was left on sub-view ${before.subview}`);
      if (new URLSearchParams(g.search).has(fp)) fail('G18', at, `${label}: the URL still holds ?${fp} after the return`);
    }
    drain(sink, at);
  }

  /**
   * G18 on an App that is a surface (`--workbench ''`, the App route `--app-route`, shell 0.16.0): every view of the surface's tab row is
   * opened and its tab row measured (the row and the head must not move between views: the Focus control must add no row, ADR-0071);
   * each view that offers the Focus control is entered from its last sub-view (the first view is where the walk leaves the App, so a
   * Focus that fell back to it would go unseen) and, in the primary mode, left both by the exit button and by Escape; outside the primary
   * mode, the last focusable view only. The same failures as for a workbench apply, with the view in place of the case and the group.
   */
  async function surfaceFocusWalk(page, sink, at, s) {
    const rowTabs = page.locator('[data-surface] > .caos-surface-body > .tabs > [role="tablist"] > [role="tab"]');
    const n = await rowTabs.count();
    const focusable = [];
    const rows = [];
    // the tab row and the head, from the surface's own top (the document may have scrolled)
    const geometry = () =>
      page.evaluate(() => {
        const surface = document.querySelector('[data-surface]');
        const list = document.querySelector('[data-surface] > .caos-surface-body > .tabs > [role="tablist"]');
        if (!surface || !list) return null;
        const top = surface.getBoundingClientRect().top;
        const r = list.getBoundingClientRect();
        const head = document.querySelector('[data-surface] > .caos-surface-head');
        const round = (x) => Math.round(x * 10) / 10;
        // the height the tabs themselves need (their lowest edge, the row's bottom padding and rule): anything above it is height something
        // else gave the row, such as a taller Focus control in the slot beside it
        const cs = getComputedStyle(list);
        // the tabs stretch to the row, so they are measured at their natural height (aligned to the start for this one reading)
        const before = list.style.alignItems;
        list.style.alignItems = 'flex-start';
        const lowest = Math.max(0, ...[...list.querySelectorAll('[role="tab"]')].map((b) => b.getBoundingClientRect().bottom));
        list.style.alignItems = before;
        const need = lowest - r.top + parseFloat(cs.paddingBottom) + parseFloat(cs.borderBottomWidth);
        return { top: round(r.top - top), height: round(r.height), head: head ? round(head.getBoundingClientRect().height) : 0, slack: round(r.height - need) };
      });
    for (let i = 0; i < n; i += 1) {
      await rowTabs.nth(i).click({ timeout: 4000 }).catch(() => undefined);
      await settle(page);
      const shown = (await page.locator('[data-focus-enter]').filter({ visible: true }).count()) > 0;
      const facts = await page.evaluate(() => window.__caosGate.focusFacts());
      if (shown) focusable.push({ index: i, id: facts.group });
      rows.push({ id: facts.group, geo: await geometry() });
    }
    if (focusable.length > 0 && rows[0]?.geo) {
      for (const r of rows.slice(1)) {
        if (!r.geo) continue;
        const g0 = rows[0].geo;
        if (r.geo.top !== g0.top || r.geo.height !== g0.height || r.geo.head !== g0.head) {
          fail('G18', { ...at, trail: `view ${r.id}` }, `the surface's tab row or head moves between views (view ${rows[0].id}: row at ${g0.top}px, ${g0.height}px high, head ${g0.head}px; view ${r.id}: row at ${r.geo.top}px, ${r.geo.height}px high, head ${r.geo.head}px): a view must not add a row or shift the tab row (ADR-0071); the Focus control sits on the tab row with its space reserved and adds none, and a per-view head is the product's to keep steady`);
          break;
        }
      }
    }
    if (focusable.length > 0) {
      const tall = rows.find((r) => r.geo && r.geo.slack > 3);
      if (tall) fail('G18', { ...at, trail: `view ${tall.id}` }, `the surface's tab row is ${tall.geo.slack}px taller than its tabs need (view ${tall.id}, row ${tall.geo.height}px): something beside the tabs, such as a taller Focus control in the tab row's slot, adds height to the row on every view (ADR-0071)`);
      const empty = (await page.evaluate(() => window.__caosGate.focusFacts())).emptyHead;
      if (empty !== null) fail('G18', { ...at, trail: 'surface head' }, `the surface renders a head with no title, lede or actions (an empty head row ${empty}px high): a surface without them has no head, and the Focus control sits on the tab row, never in a head of its own (ADR-0071)`);
    }
    if (focusable.length === 0) {
      if (opt.requireFocus) {
        fail('G18', { ...at, trail: 'surface > Focus' }, `the surface App (${at.route}) offers no Focus control ([data-focus-enter]) on any of its ${n} view(s): ADR-0070 requires a visible control on every view with a stage that opens it in focus mode (set TabDef.focus on the view and focus on the SurfacePage)`);
      }
      if (n > 0) await rowTabs.nth(0).click({ timeout: 4000 }).catch(() => undefined);
      await settle(page);
      return;
    }
    const targets = s.primary ? focusable : focusable.slice(-1);
    for (const [k, v] of targets.entries()) {
      // the primary mode leaves each focusable view twice: by the exit button (even index), then by Escape (odd index)
      for (const way of s.primary ? [0, 1] : [0]) {
        await rowTabs.nth(v.index).click({ timeout: 4000 }).catch(() => undefined);
        await settle(page);
        const subs = page.locator('[data-surface] .subtablist [role="tab"]');
        const sn = await subs.count();
        if (sn > 1) {
          await subs.nth(sn - 1).click({ timeout: 4000 }).catch(() => undefined);
          await settle(page);
        }
        const enter = page.locator('[data-focus-enter]').filter({ visible: true }).first();
        await focusVisitOne(page, sink, at, s, { kind: 'view', id: v.id }, 2 * k + way, enter);
      }
    }
    await rowTabs.nth(0).click({ timeout: 4000 }).catch(() => undefined);
    await settle(page);
  }

  async function workbenchKey(page) {
    return page.evaluate(() => document.querySelector('[data-case-workbench]')?.getAttribute('data-state-key') ?? null);
  }

  async function changeControl(page, c) {
    const host = page.locator(c.path);
    if (c.kind === 'range') {
      const input = (await host.evaluate((e) => e.matches('input'))) ? host : host.locator('input[type="range"]').first();
      const v = await input.evaluate((e) => ({ value: Number(e.value), max: e.max === '' ? 100 : Number(e.max) }));
      await input.focus();
      await page.keyboard.press(v.value >= v.max ? 'ArrowLeft' : 'ArrowRight');
      return true;
    }
    if (c.kind === 'select') {
      const sel = (await host.evaluate((e) => e.tagName === 'SELECT')) ? host : host.locator('select').first();
      const idx = await sel.evaluate((e) => [...e.options].findIndex((o, i) => i !== e.selectedIndex && !o.disabled));
      if (idx < 0) return 'no other option';
      await sel.selectOption({ index: idx });
      return true;
    }
    if (c.kind === 'check') {
      await host.locator('input[type="checkbox"], input[type="radio"]:not(:checked)').first().click({ timeout: 5000 });
      return true;
    }
    if (c.kind === 'number') {
      const input = host.locator('input[type="number"]').first();
      const v = await input.evaluate((e) => ({ value: Number(e.value), step: Number(e.step) || 1 }));
      await input.fill(String(v.value + v.step));
      await input.press('Enter');
      return true;
    }
    if (c.kind === 'buttons') {
      const buttons = host.locator('button');
      const n = await buttons.count();
      for (let i = 0; i < n; i += 1) {
        const b = buttons.nth(i);
        const on = await b.evaluate(
          (e) => e.disabled || e.classList.contains('on') || e.classList.contains('active') || ['aria-pressed', 'aria-checked', 'aria-selected'].some((a) => e.getAttribute(a) === 'true'),
        );
        if (!on) {
          await b.click({ timeout: 5000 });
          return true;
        }
      }
      return 'every option is already selected';
    }
    return `unknown control kind (${c.kind})`;
  }

  function finish() {
    const checks = {};
    for (const f of failures) checks[f.check] = (checks[f.check] ?? 0) + 1;
    mkdirSync(opt.out, { recursive: true });
    const captures = existsSync(shotsDir) ? readdirSync(shotsDir).filter((n) => n.endsWith('.png')).sort() : [];
    const report = {
      ok: failures.length === 0,
      base,
      expectBrand: opt.expectBrand,
      sizes: opt.sizes,
      themes: opt.themes,
      langs: opt.langs,
      wideFontSizes: opt.wideFont === false ? '' : opt.wideFontSizes,
      states,
      minima,
      waivers,
      checks,
      artifactMeasurements,
      captures: captures.length,
      failures,
    };
    writeFileSync(join(opt.out, 'gate-report.json'), JSON.stringify(report, null, 2));
    // G14: the captures are for a person to read (the gate measures, it does not judge content); one page shows them.
    writeFileSync(join(opt.out, 'index.html'), captureIndex(report, captures));
    return report;
  }
}

const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

/** G14: one page with every capture, grouped by route, the failure captures and the failure list first. */
export function captureIndex(report, captures) {
  const groups = new Map();
  for (const name of captures) {
    const key = name.startsWith('fail_') ? 'failures' : name.split('_')[0];
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(name);
  }
  const order = ['failures', ...[...groups.keys()].filter((k) => k !== 'failures')];
  const rows = report.failures
    .slice(0, 400)
    .map((f) => `<tr><td>${esc(f.check)}</td><td>${esc(f.route)}</td><td>${esc(f.mode)}</td><td>${esc(f.trail)}</td><td>${esc(f.message)}</td></tr>`)
    .join('');
  const figure = (n) => `<figure><a href="shots/${esc(n)}"><img loading="lazy" src="shots/${esc(n)}" alt="${esc(n)}"></a><figcaption>${esc(n.replace(/\.png$/, ''))}</figcaption></figure>`;
  const sections = order
    .filter((k) => groups.has(k))
    .map((k) => `<h2>${esc(k)} (${groups.get(k).length})</h2><div class="grid">${groups.get(k).map(figure).join('')}</div>`)
    .join('');
  const style =
    'body{font:14px system-ui,sans-serif;margin:16px;background:#f6f8fa;color:#1f2328}h1{font-size:18px}h2{font-size:15px;margin-top:24px}' +
    'table{border-collapse:collapse;font-size:12px}td{border-bottom:1px solid #d0d7de;padding:3px 6px;vertical-align:top}' +
    '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}figure{margin:0;background:#fff;border:1px solid #d0d7de;padding:6px}' +
    'img{width:100%;height:auto;display:block}figcaption{font-size:11px;color:#57606a;margin-top:4px}';
  const head = `caos-shell-gate: ${esc(report.expectBrand)} at ${esc(report.base)}: ${report.ok ? 'OK' : `${report.failures.length} failure(s)`} in ${report.states} states, ${captures.length} captures`;
  const wrows = (report.waivers ?? []).map((w) => `<tr><td>${esc(w.route)}</td><td>${esc(w.lang)}</td><td>${esc(w.floor)}</td><td>${esc(w.reason)}</td><td>${w.valid ? 'accepted' : 'refused'}</td></tr>`).join('');
  const waiverTable = wrows ? `<h2>Waivers (${report.waivers.length})</h2><table><tr><td>route</td><td>language</td><td>floor</td><td>reason</td><td>verdict</td></tr>${wrows}</table>` : '';
  const table = rows ? `<table><tr><td>check</td><td>route</td><td>mode</td><td>trail</td><td>message</td></tr>${rows}</table>` : '';
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${head}</title><style>${style}</style></head><body><h1>${head}</h1>${table}${waiverTable}${sections}</body></html>\n`;
}

function slug(route) {
  return route === '/' ? 'landing' : route.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '');
}
