/** Owned validation cache is explicit external working storage. */
import { defineConfig, mergeConfig } from "vitest/config";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { existsSync, realpathSync } from "node:fs";
import base from "./vite.config";

const value = process.env.GEOPHYSICS_QA_CACHE;
if (!value || !isAbsolute(value)) throw new Error("Select explicit external GEOPHYSICS_QA_CACHE");
const requested = resolve(value);
let existing = requested;
while (!existsSync(existing)) existing = dirname(existing);
const cache = resolve(realpathSync.native(existing), relative(existing, requested));
for (let parent = cache; ; parent = dirname(parent)) {
  if (existsSync(resolve(parent, ".git"))) throw new Error("QA cache must be outside checkouts");
  if (parent === dirname(parent)) break;
}
export default mergeConfig(base, defineConfig({ cacheDir: cache, publicDir: false }));
