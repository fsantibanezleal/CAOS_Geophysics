// Run the published CAOS shell gate against this product's built single-origin app.
// Keep the six-route manifest authoritative and require Focus on the real App route.
// Shell 0.19.0 reports `checks` as failure counts only; a missing G18/G20 key means
// no failure was recorded, not that a measurement was skipped. The gate runs G18
// for every configured workbench route and G20 during every measured route state.
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', '..');
const product = JSON.parse(readFileSync(join(root, 'product.json'), 'utf8'));
const routes = JSON.parse(readFileSync(join(root, 'frontend', 'src', 'lib', 'routes.json'), 'utf8'));
const appRoute = product.workbench_route ?? '/app';
const extras = process.argv.slice(2);
const value = (flag) => {
  const index = extras.indexOf(flag);
  return index < 0 ? null : (extras[index + 1] ?? '');
};

if (product.app !== 'workbench' || typeof product.name !== 'string' || !product.name.trim()) {
  console.error('gate: product.json must name this workbench App before the shell gate can run');
  process.exit(1);
}
if (!routes.some((route) => route.path === appRoute)) {
  console.error(`gate: configured workbench route ${appRoute} is not in frontend/src/lib/routes.json`);
  process.exit(1);
}
const reserved = ['--workbench', '--expect-brand', '--serve', '--spa-fallback', '--out', '--no-require-focus'];
const overridden = reserved.find((flag) => extras.includes(flag));
if (overridden) {
  console.error(`gate: ${overridden} is fixed by the product adapter and cannot be overridden`);
  process.exit(1);
}
const routesArg = value('--routes');
if (routesArg !== null && !routesArg.split(',').map((route) => route.trim().replace(/(.)\/+$/, '$1')).includes(appRoute)) {
  console.error(`gate: --routes omits the App route ${appRoute}; G18 would measure nothing`);
  process.exit(1);
}

const require = createRequire(import.meta.url);
const shellPackage = require.resolve('@fasl-work/caos-app-shell/package.json');
const bin = join(dirname(shellPackage), 'bin', 'caos-shell-gate.mjs');
if (!existsSync(bin)) {
  console.error(`gate: published shell gate is missing at ${bin}`);
  process.exit(1);
}
const serving = !extras.includes('--url');
const args = [
  ...(serving ? ['--serve', join(root, 'frontend', 'dist'), '--spa-fallback'] : []),
  '--expect-brand', product.name,
  '--workbench', appRoute,
  '--require-focus',
  '--out', join(root, 'frontend', 'gate-output'),
  ...extras,
];
const result = spawnSync(process.execPath, [bin, ...args], { cwd: root, stdio: 'inherit' });
let exitCode = result.status ?? 1;
const reportPath = join(root, 'frontend', 'gate-output', 'gate-report.json');
if (existsSync(reportPath)) {
  try {
    const report = JSON.parse(readFileSync(reportPath, 'utf8'));
    if (!Number.isInteger(report.states) || report.states < 1) {
      console.error('gate: the published shell gate reported no measured route states');
      exitCode = 1;
    }
  } catch (error) {
    console.error(`gate: could not read the published shell report at ${reportPath}: ${error.message}`);
    exitCode = 1;
  }
} else {
  console.error(`gate: the published shell gate did not write ${reportPath}`);
  exitCode = 1;
}
process.exit(exitCode);
