// A product takes this file verbatim: it tests the base script scripts/gate.mjs. The route plan comes from the product's
// frontend route manifest and product.json showcase.story_routes, so no product's story steps are embedded in this test.
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const root = resolve(process.cwd(), '..');
const frontend = resolve(root, 'frontend');
const gateScript = fileURLToPath(new URL('../scripts/gate.mjs', import.meta.url));
const product = JSON.parse(readFileSync(resolve(root, 'product.json'), 'utf8')) as {
  showcase?: { story_routes?: string[] };
};
const pages = JSON.parse(readFileSync(resolve(frontend, 'src/lib/routes.json'), 'utf8')) as Array<{ path: string }>;

describe('the product-owned visual gate plan', () => {
  it('measures the app, documentation and the product declared story routes', () => {
    const expected = [...pages.map(({ path }) => path), ...(product.showcase?.story_routes ?? [])];
    const result = spawnSync(process.execPath, [gateScript, '--plan'], {
      cwd: frontend,
      encoding: 'utf8',
      timeout: 10_000,
    });

    expect(result.status, result.stderr).toBe(0);
    expect(result.stdout).toContain(`gate: routes ${expected.join(',')}`);
  });
});
