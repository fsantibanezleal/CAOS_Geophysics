// Give static hosts an index entrypoint for every documented route. The app still
// uses BrowserRouter, while this makes bookmarked route loads resolve without
// relying only on a 404.html fallback.
import { cpSync, copyFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontend = dirname(fileURLToPath(import.meta.url));
const dist = join(frontend, 'dist');
const index = join(dist, 'index.html');
const assets = join(dist, 'assets');
const manifest = JSON.parse(readFileSync(join(frontend, 'src/lib/routes.json'), 'utf8'));
const routes = manifest.filter(({ path }) => path !== '/').map(({ path }) => {
  if (!/^\/[a-z-]+$/.test(path)) throw new Error(`Invalid static route: ${path}`);
  return path.slice(1);
});

for (const route of routes) {
  const routeDir = join(dist, route);
  mkdirSync(routeDir, { recursive: true });
  copyFileSync(index, join(routeDir, 'index.html'));
  if (existsSync(assets)) cpSync(assets, join(routeDir, 'assets'), { recursive: true });
}

console.log(`[route-entrypoints] created ${routes.length} static route entrypoints`);
