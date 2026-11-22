import { readFileSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
// @ts-expect-error: the template's build-time ES module is shared with this product contract test.
import { declaredFiles } from '../../scripts/declared.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const derived = resolve(here, '../../../data/derived');
const v2 = join(derived, 'v2');
const catalog = JSON.parse(readFileSync(join(v2, 'catalog.json'), 'utf8'));
const declared = declaredFiles(derived);

describe('the shared-template publication contract for the geophysics catalog', () => {
  it('declares every canonical catalog file and no unavailable artifact', () => {
    expect(catalog.schema).toBe('inverse-earth.catalog/v2');
    expect(catalog.complete).toBe(true);
    expect(catalog.cases).toHaveLength(20);
    expect(declared.index.cases).toHaveLength(20);
    expect(declared.declared).toHaveLength(148);
    expect(declared.missing).toEqual([]);
    expect(declared.tolerated).toEqual([]);
    expect(declared.problems).toEqual([]);
  });

  it('binds the 120 published case artifacts to the catalog paths and byte counts', () => {
    const entries = new Map(declared.index.cases.map((entry: { case_id: string; manifest_path: string }) => [entry.case_id, entry.manifest_path]));
    for (const c of catalog.cases) {
      expect(entries.has(c.id)).toBe(true);
      const manifestPath = entries.get(c.id) as string;
      const manifest = JSON.parse(readFileSync(join(derived, manifestPath), 'utf8'));
      expect(manifest.case_id).toBe(c.id);
      expect(manifest.artifacts).toHaveLength(6);
      expect(manifest.artifacts.map((artifact: { path: string }) => artifact.path)).toEqual(c.variants.map((variant: { path: string }) => `v2/${variant.path}`));
      for (let i = 0; i < c.variants.length; i++) {
        const variant = c.variants[i];
        const artifact = manifest.artifacts[i];
        expect(artifact.bytes).toBe(variant.bytes);
        expect(artifact.sha256).toBe(variant.sha256);
        expect(statSync(join(derived, artifact.path)).size).toBe(artifact.bytes);
      }
    }
  });

  it('does not advertise an absent artifact as ready', () => {
    const readiness = JSON.parse(readFileSync(join(derived, 'readiness.json'), 'utf8'));
    expect(readiness.schema).toBe('inverse-earth.readiness/v1');
    expect(readiness.catalog.sha256).toMatch(/^[0-9a-f]{64}$/);
    expect(readiness.artifacts.missing).toEqual([]);
    expect(readiness.artifacts.present).toBe(120);
    expect(readiness.state).toBe('available');
  });
});
