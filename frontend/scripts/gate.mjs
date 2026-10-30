// CAOS shell gate entry point. Keep its source and measured behavior on the exact installed shell version.
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, isAbsolute, join, parse, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runGate } from '@fasl-work/caos-app-shell/gate';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', '..');
const frontend = join(root, 'frontend');
const product = JSON.parse(readFileSync(join(root, 'product.json'), 'utf8'));
const routes = JSON.parse(readFileSync(join(frontend, 'src', 'lib', 'routes.json'), 'utf8'));
const appRoute = product.workbench_route ?? '/app';
const expectedShellVersion = '0.19.9';
const require = createRequire(import.meta.url);
const shellPackagePath = require.resolve('@fasl-work/caos-app-shell/package.json');
const shellPackage = JSON.parse(readFileSync(shellPackagePath, 'utf8'));

if (shellPackage.version !== expectedShellVersion) {
  console.error(`gate: product-owned gate is based on shell ${expectedShellVersion}, but the installed shell is ${shellPackage.version}`);
  process.exit(1);
}
if (product.app !== 'workbench' || typeof product.name !== 'string' || !product.name.trim()) {
  console.error('gate: product.json must name this workbench App before the shell gate can run');
  process.exit(1);
}
if (!routes.some((route) => route.path === appRoute)) {
  console.error(`gate: configured workbench route ${appRoute} is not in frontend/src/lib/routes.json`);
  process.exit(1);
}

const values = new Map([
  ['out', 'out'],
  ['url', 'url'],
  ['base-path', 'basePath'],
  ['routes', 'routes'],
  ['sizes', 'sizes'],
  ['themes', 'themes'],
  ['langs', 'langs'],
  ['case-sample', 'caseSample'],
  ['idle-ms', 'idleMs'],
  ['settle-ms', 'settleMs'],
  ['text-floor', 'textFloor'],
  ['instrument-min', 'instrumentMin'],
  ['stage-fill-min', 'stageFillMin'],
  ['stage-floor', 'stageFloor'],
  ['wide-font-sizes', 'wideFontSizes'],
]);
const extra = {};
const argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i += 1) {
  const flag = argv[i];
  if (!flag.startsWith('--')) {
    console.error(`gate: unexpected argument ${flag}`);
    process.exit(2);
  }
  const key = flag.slice(2);
  if (key === 'no-wide-font') {
    extra.wideFont = false;
  } else if (key === 'single-case') {
    extra.singleCase = true;
  } else if (key === 'require-focus' || key === 'spa-fallback') {
    console.error(`gate: ${flag} is fixed by the product adapter`);
    process.exit(2);
  } else if (['workbench', 'app-route', 'expect-brand', 'serve', 'no-require-focus'].includes(key)) {
    console.error(`gate: ${flag} is fixed by the product adapter`);
    process.exit(2);
  } else if (values.has(key)) {
    const value = argv[i + 1];
    if (value === undefined || value.startsWith('--')) {
      console.error(`gate: ${flag} requires a value`);
      process.exit(2);
    }
    i += 1;
    const property = values.get(key);
    extra[property] = ['idleMs', 'settleMs', 'textFloor', 'instrumentMin', 'stageFillMin', 'stageFloor'].includes(property)
      ? Number(value)
      : value;
    if (typeof extra[property] === 'number' && !Number.isFinite(extra[property])) {
      console.error(`gate: ${flag} requires a finite number`);
      process.exit(2);
    }
  } else {
    console.error(`gate: unsupported option ${flag}`);
    process.exit(2);
  }
}

const routesArg = extra.routes;
if (routesArg !== undefined && !routesArg.split(',').map((route) => route.trim().replace(/(.)\/+$/, '$1')).includes(appRoute)) {
  console.error(`gate: --routes omits the App route ${appRoute}; G18 would measure nothing`);
  process.exit(1);
}

const outputValue = extra.out ?? process.env.GEOPHYSICS_GATE_OUTPUT;
if (!outputValue || !isAbsolute(outputValue)) {
  console.error('gate: set GEOPHYSICS_GATE_OUTPUT or pass --out as an absolute path outside every Git checkout');
  process.exit(1);
}
const outputPath = resolve(outputValue);
const relativeOutput = relative(resolve(root), outputPath);
if (!relativeOutput || (!relativeOutput.startsWith(`..${sep}`) && relativeOutput !== '..' && !isAbsolute(relativeOutput))) {
  console.error('gate: visual evidence must be stored outside the product worktree');
  process.exit(1);
}
for (let parent = outputPath; ; parent = dirname(parent)) {
  if (existsSync(join(parent, '.git'))) {
    console.error('gate: visual evidence must be stored outside every Git checkout');
    process.exit(1);
  }
  if (parent === parse(parent).root) break;
}

const options = {
  ...extra,
  ...(extra.url ? {} : { serve: join(frontend, 'dist'), spaFallback: true }),
  expectBrand: product.name,
  workbench: appRoute,
  requireFocus: true,
  out: outputPath,
};
if (!options.url && !existsSync(join(frontend, 'dist', 'index.html'))) {
  console.error('gate: frontend/dist/index.html is missing; run npm run build first');
  process.exit(1);
}

try {
  const report = await runGate(options);
  for (const failure of report.failures.slice(0, 80)) {
    console.error(`FAIL [${failure.check}] ${failure.route} ${failure.mode}${failure.trail ? ` (${failure.trail})` : ''}: ${failure.message}`);
  }
  if (report.failures.length > 80) console.error(`... ${report.failures.length - 80} additional findings are recorded in ${join(outputPath, 'gate-report.json')}`);
  for (const artifact of report.artifactMeasurements ?? []) {
    console.log(`served artifact verified: ${artifact.path}, HTTP ${artifact.status}, ${artifact.contentType}, ${artifact.bytes} bytes, sha256 ${artifact.sha256}`);
  }
  console.log(report.ok ? `caos-shell-product-gate: OK, ${report.states} measured states` : `caos-shell-product-gate: ${report.failures.length} failure(s) in ${report.states} measured states`);
  process.exitCode = report.ok ? 0 : 1;
} catch (error) {
  console.error(`gate: ${error.stack ?? error.message}`);
  process.exitCode = 1;
}
