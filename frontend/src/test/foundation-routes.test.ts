import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { PRODUCT_ROUTES } from "../lib/routes";
import { artifactBase, routerBasename } from "../lib/deployment";

const read = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");

describe("frontend route and shell foundation", () => {
  it("six_routes_share_one_manifest", () => {
    expect(PRODUCT_ROUTES.map(({ id, path, en }) => [id, path, en])).toEqual([
      ["app", "/", "App"],
      ["introduction", "/introduction", "Introduction"],
      ["methodology", "/methodology", "Methodology"],
      ["implementation", "/implementation", "Implementation"],
      ["experiments", "/experiments", "Experiments"],
      ["benchmark", "/benchmark", "Benchmark"],
    ]);
    expect(new Set(PRODUCT_ROUTES.map(route => route.path)).size).toBe(6);
    expect(PRODUCT_ROUTES.every(route => route.es && route.en)).toBe(true);
    expect(read("../../create-route-entrypoints.mjs")).toContain("src/lib/routes.json");
    expect(read("../main.tsx")).toContain("PRODUCT_ROUTES.map");
  });

  it("deployment_modes_preserve_legacy_and_target_paths", () => {
    expect(routerBasename("legacy", "/CAOS_Geophysics/benchmark/")).toBe("/CAOS_Geophysics");
    expect(artifactBase("legacy", "/CAOS_Geophysics/benchmark/")).toBe("/CAOS_Geophysics/");
    expect(routerBasename("legacy", "/benchmark/")).toBe("/");
    expect(routerBasename("legacy", "/CAOS_Geophysics-copy/benchmark")).toBe("/");
    expect(routerBasename("single-origin", "/CAOS_Geophysics/benchmark/")).toBe("/");
    expect(artifactBase("single-origin", "/benchmark/")).toBe("/");
    expect(read("../../vite.config.ts")).toContain("mode === 'single-origin' ? '/' : './'");
    expect(read("../../package.json")).toContain("build:single-origin");
  });

  it("shell_tokens_and_chrome_are_centralized", () => {
    const entry = read("../main.tsx");
    const css = read("../styles.css");
    expect(entry).toContain('import "@fasl-work/caos-app-shell/styles.css"');
    expect(entry).toContain("<AppShell config={config}>");
    expect(entry).toContain("<CitationsProvider items={CITATIONS}>");
    expect(css).not.toMatch(/@font-face|font-family\s*:\s*["']|^\s*:root\s*\{|\[data-theme=/m);
    expect(css).not.toMatch(/^\s*--(?:font|color)-[a-z-]+\s*:/m);
    expect(read("../../index.html")).not.toContain('name="theme-color"');
  });

  it("no_unreleased_operation_route", () => {
    expect(PRODUCT_ROUTES.map(route => route.path)).not.toEqual(expect.arrayContaining([
      "/catalogue", "/projects", "/processing", "/modelling", "/evaluation",
    ]));
    for (const file of ["../main.tsx", "../pages/Workbench.tsx", "../pages/Research.tsx"])
      expect(read(file)).not.toContain("api/client");
  });
});
