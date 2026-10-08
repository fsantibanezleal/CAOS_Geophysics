import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { PRODUCT_ROUTES } from "../lib/routes";
import { artifactBase, deploymentMode, routerBasename } from "../lib/deployment";

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
    expect(read("../main.tsx")).toContain("PRODUCT_ROUTES.map");
  });

  it("all_builds_use_one_root_origin_without_route_asset_copies", () => {
    expect(deploymentMode).toBe("single-origin");
    for (const path of ["/", "/benchmark/", "/CAOS_Geophysics/benchmark/", "/CAOS_Geophysics-copy/benchmark"]) {
      expect(routerBasename(deploymentMode, path)).toBe("/");
      expect(artifactBase(deploymentMode, path)).toBe("/");
    }
    expect(read("../../vite.config.ts")).toContain("base: '/'");
    expect(read("../lib/deployment.ts")).not.toContain('"legacy"');
    const { scripts } = JSON.parse(read("../../package.json"));
    expect(scripts.build).toBe("tsc --noEmit && node copy-data.mjs && vite build");
    expect(scripts["build:single-origin"]).toBe("npm run build");
    expect(existsSync(new URL("../../create-route-entrypoints.mjs", import.meta.url))).toBe(false);
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

  it("the_exact_shared_shell_consumer_declares_product_metadata_and_containment", () => {
    const manifest = JSON.parse(read("../../package.json"));
    const lock = JSON.parse(read("../../package-lock.json"));
    const installed = JSON.parse(read("../../node_modules/@fasl-work/caos-app-shell/package.json"));
    expect(manifest.dependencies["@fasl-work/caos-app-shell"]).toBe("0.8.1");
    expect(lock.packages[""].dependencies["@fasl-work/caos-app-shell"]).toBe("0.8.1");
    expect(lock.packages["node_modules/@fasl-work/caos-app-shell"].version).toBe("0.8.1");
    expect(installed.version).toBe("0.8.1");
    const entry = read("../main.tsx");
    const metadata = entry.slice(entry.indexOf('version: "0.04.001"'), entry.indexOf("  architecture,"));
    expect(metadata).toContain('visibility: "public"');
    expect(metadata).toContain("contain: true");
    expect(metadata).toContain("license: {");
    expect(metadata).toContain('en: "Apache-2.0 code and CC-BY-4.0 content"');
    expect(metadata).toContain('es: "Código Apache-2.0 y contenido CC-BY-4.0"');
    expect(read("../../vite.config.ts")).toContain("dedupe: ['react', 'react-dom', 'react-router']");
    // This is an ABI/consumer guard, not a measured mobile instrument-area gate.
  });

  it("no_unreleased_operation_route", () => {
    expect(PRODUCT_ROUTES.map(route => route.path)).not.toEqual(expect.arrayContaining([
      "/catalogue", "/projects", "/processing", "/modelling", "/evaluation",
    ]));
    for (const file of ["../main.tsx", "../pages/Workbench.tsx", "../pages/Research.tsx"])
      expect(read(file)).not.toContain("api/client");
  });
});
