// A static server that answers the way GitHub Pages does, so a local gate run sees what the deployed site will:
// an existing file is 200; a directory without a trailing slash is a 301 to the slash; a directory with one serves its
// index.html; `/name` falls back to `name.html`; anything else is 404 with the site's 404.html. There is no SPA
// fallback, which is the point: a route that was not materialised, or an artifact missing from the build, fails here
// exactly as it would on Pages (failure classes 2 and 22: deep links that 404, artifacts answered with HTML).
// With `spaFallback` (`--spa-fallback`, shell 0.16.0) it answers as nginx does for a single-page app on a VPS
// (`try_files $uri $uri/ /index.html`): an extensionless path that matches no file gets index.html with 200; a path with an
// extension that matches no file stays 404, so a missing artifact still fails. Edge paths, by design of a gate server and tested:
// a directory with no index.html answers the app shell (nginx: 301 then 403); a dot in a directory name reads as an extension, so
// `/route/with.dot/` and `/app/run.v2` stay 404 (nginx would serve the app); a MISSING dotfile such as `/.env` has no extension and
// answers the app shell (an existing file, a dotfile included, is served as it is); the query string is no part of the path (`/route?x=1.5` answers the app shell, `/missing.js?v=2` is 404).

import { createServer } from 'node:http';
import { existsSync, statSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize, resolve, sep } from 'node:path';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.geojson': 'application/geo+json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.txt': 'text/plain; charset=utf-8',
  '.csv': 'text/csv; charset=utf-8',
  '.map': 'application/json',
  '.wasm': 'application/wasm',
  '.webmanifest': 'application/manifest+json',
  '.xml': 'application/xml',
};

export async function readFileWithBusyRetry(file, { read = readFile, pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms)) } = {}) {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await read(file);
    } catch (error) {
      if (error?.code !== 'EBUSY' || attempt >= 3) throw error;
      await pause(25 * (attempt + 1));
    }
  }
}

/**
 * @param {string} dir the built site
 * @param {string} basePath the site's base path ('/' for a custom domain, '/Repo/' for a project page)
 * @param {number} port 0 for any free port (the gate), or a fixed one (a product's preview)
 * @param {{ spaFallback?: boolean }} options `spaFallback`: answer an extensionless path that matches no file with index.html and 200
 * @returns {Promise<{ url: string, close: () => Promise<void> }>}
 */
export function servePages(dir, basePath = '/', port = 0, options = {}) {
  const root = resolve(dir);
  const base = basePath.endsWith('/') ? basePath : `${basePath}/`;
  const notFound = join(root, '404.html');
  const rootIndex = join(root, 'index.html');
  const server = createServer((req, res) => {
    const send = async (status, file, headers = {}) => {
      let body;
      if (req.method !== 'HEAD') {
        try {
          body = await readFileWithBusyRetry(file);
        } catch {
          if (res.destroyed) return;
          res.writeHead(503, { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store', 'Retry-After': '1' });
          res.end('Temporary static artifact read failure');
          return;
        }
      }
      res.writeHead(status, { 'Content-Type': MIME[extname(file).toLowerCase()] ?? 'application/octet-stream', 'Cache-Control': 'no-store', ...headers });
      res.end(body);
    };
    const missing = () => {
      if (existsSync(notFound)) send(404, notFound);
      else {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('404');
      }
    };
    let path;
    let search = '';
    // nginx `try_files $uri $uri/ /index.html`: a path with no extension that is no file answers the app shell
    const miss = () => (options.spaFallback && !extname(path ?? '') && existsSync(rootIndex) ? send(200, rootIndex) : missing());
    try {
      const u = new URL(req.url ?? '/', 'http://x');
      path = decodeURIComponent(u.pathname);
      search = u.search;
    } catch {
      return missing();
    }
    if (`${path}/` === base) {
      res.writeHead(301, { Location: base });
      return res.end();
    }
    if (!path.startsWith(base)) return missing();
    const rel = path.slice(base.length);
    const file = normalize(join(root, rel));
    if (file !== root && !file.startsWith(root + sep)) return missing();
    if (existsSync(file)) {
      const st = statSync(file);
      if (st.isFile()) return send(200, file);
      if (st.isDirectory()) {
        const index = join(file, 'index.html');
        if (!existsSync(index)) return miss();
        if (!path.endsWith('/')) {
          // the query string survives the redirect, as a Pages host keeps it (an old link /app?case=B2 must reach its case)
          res.writeHead(301, { Location: `${path}/${search}` });
          return res.end();
        }
        return send(200, index);
      }
    }
    if (!path.endsWith('/') && existsSync(`${file}.html`)) return send(200, `${file}.html`);
    return miss();
  });
  return new Promise((ok) => {
    server.listen(port, '127.0.0.1', () => {
      const { port } = server.address();
      ok({
        url: `http://127.0.0.1:${port}${base}`,
        close: () => new Promise((done) => server.close(() => done())),
      });
    });
  });
}
