import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { PRODUCT_ROUTES } from "../lib/routes";
import { artifactBase, deploymentMode, routerBasename } from "../lib/deployment";

const read = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");

describe("frontend route and shell foundation", () => {
  it("adversarial: refuses route additions or path drift from the approved six-route manifest", () => {
    expect(PRODUCT_ROUTES.map(({ id, path, en }) => [id, path, en])).toEqual([
      ["app", "/app", "App"],
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

  it("six_pages_are_deferred_without_changing_the_route_manifest", () => {
    const entry = read("../main.tsx");
    for (const page of ["Workbench", "Research"]) {
      expect(entry).toContain(`lazy(() => import("./pages/${page}")`);
    }
    for (const page of ["Introduction", "Methodology", "Implementation", "Experiments", "Benchmark"]) {
      expect(entry).toContain(`module.${page}`);
    }
    expect(entry).toContain("<Suspense fallback={<RouteLoading />}>");
    expect(entry).not.toContain('from "./pages"');
    expect(PRODUCT_ROUTES.map(({ id, path }) => [id, path])).toEqual([
      ["app", "/app"],
      ["introduction", "/introduction"],
      ["methodology", "/methodology"],
      ["implementation", "/implementation"],
      ["experiments", "/experiments"],
      ["benchmark", "/benchmark"],
    ]);
  });

  it("adversarial: refuses legacy basenames, nested asset roots, and generated route copies", () => {
    expect(deploymentMode).toBe("single-origin");
    for (const path of ["/", "/benchmark/", "/CAOS_Geophysics/benchmark/", "/CAOS_Geophysics-copy/benchmark"]) {
      expect(routerBasename(deploymentMode, path)).toBe("/");
      expect(artifactBase(deploymentMode, path)).toBe("/");
    }
    expect(read("../../vite.config.ts")).toContain("base: '/'");
    expect(read("../lib/deployment.ts")).not.toContain('"legacy"');
    const { scripts } = JSON.parse(read("../../package.json"));
    expect(scripts.build).toBe("node scripts/verify-joint-pins.mjs && tsc --noEmit && node copy-data.mjs && vite build");
    expect(scripts["build:single-origin"]).toBe("npm run build");
    expect(existsSync(new URL("../../create-route-entrypoints.mjs", import.meta.url))).toBe(false);
  });

  it("adversarial: rejects product-owned font, palette, and shell chrome overrides", () => {
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
    expect(manifest.dependencies["@fasl-work/caos-app-shell"]).toBe("0.19.9");
    expect(lock.packages[""].dependencies["@fasl-work/caos-app-shell"]).toBe("0.19.9");
    expect(lock.packages["node_modules/@fasl-work/caos-app-shell"].version).toBe("0.19.9");
    expect(installed.version).toBe("0.19.9");
    const entry = read("../main.tsx");
    const releaseVersion = read("../../../VERSION").trim();
    const metadata = entry.slice(entry.indexOf(`version: "${releaseVersion}"`), entry.indexOf("  architecture,"));
    expect(metadata).toContain('visibility: "public"');
    expect(metadata).toContain("contain: true");
    expect(metadata).toContain("license: {");
    expect(metadata).toContain('en: "Apache code license · CC BY content license"');
    expect(metadata).toContain('es: "Licencia Apache para código · licencia CC BY para contenido"');
    const waveformMount = read("./waveform-browser-entry.tsx");
    expect(waveformMount).toContain('visibility: "public"');
    expect(waveformMount).toContain("contain: true");
    expect(waveformMount).toContain('en: "Apache-2.0 code and CC-BY-4.0 content"');
    expect(waveformMount).toContain('es: "Código Apache-2.0 y contenido CC-BY-4.0"');
    expect(read("../../vite.config.ts")).toContain("dedupe: ['react', 'react-dom', 'react-router']");
    const gate = read("../../scripts/gate.mjs");
    expect(gate).toContain("@fasl-work/caos-app-shell/gate");
    expect(gate).toContain("product.workbench_route ?? '/app'");
    expect(gate).toContain("workbench: appRoute");
    expect(gate).toContain("requireFocus: true");
    expect(gate).toContain("expectedShellVersion = '0.19.9'");
    expect(gate).toContain("GEOPHYSICS_GATE_OUTPUT");
    expect(gate).toContain("outside every Git checkout");
    expect(existsSync(new URL("../../scripts/vendor/caos-app-shell-gate-0.19.1/gate/run.mjs", import.meta.url))).toBe(false);
    expect(read("../pages/Workbench.tsx")).toContain("<CaseWorkbench");
    expect(read("../pages/Workbench.tsx")).toContain('data-control="inverse-method"');
    expect(read("../main.tsx")).toContain('@fasl-work/caos-app-shell/chart.css');
    const manifestJson = JSON.parse(read("../../../product.json"));
    expect(manifestJson.name).toBe("Inverse Earth Studio");
    expect(manifestJson.workbench_route).toBe("/app");
    // This is an ABI/consumer guard, not a measured mobile instrument-area gate.
  });

  it("adversarial: refuses routes that imply unavailable API operations are runnable", () => {
    expect(PRODUCT_ROUTES.map(route => route.path)).not.toEqual(expect.arrayContaining([
      "/catalogue", "/projects", "/processing", "/modelling", "/evaluation",
    ]));
    for (const file of ["../main.tsx", "../pages/Workbench.tsx", "../pages/Research.tsx"])
      expect(read(file)).not.toContain("api/client");
  });
});
