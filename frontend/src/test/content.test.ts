import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import katex from "katex";
import { chapters } from "../data/methods";
import { CITATIONS } from "../data/citations";
import { historyInfo, methodName, metricInfo } from "../data/metrics";
import { isosurface } from "../isosurface";
const source = (name: string) =>
  readFileSync(new URL("../" + name, import.meta.url), "utf8");
describe("scientific explanations and canonical presentation", () => {
  it("defines six chapters and every executable method in both languages", () => {
    expect(chapters.map((c) => c.id)).toEqual([
      "potential",
      "mt",
      "seismic",
      "joint",
      "cnn",
      "ae",
    ]);
    const methods = chapters.flatMap((c) => c.algorithms);
    expect(methods).toHaveLength(11);
    expect(new Set(methods.map((m) => m.id)).size).toBe(11);
    for (const c of chapters) {
      expect(c.paragraphs.length).toBeGreaterThanOrEqual(3);
      for (const pair of [c.title, ...c.paragraphs, c.assumptions])
        for (const text of pair) expect(text.length).toBeGreaterThan(10);
      for (const id of c.refs)
        expect(CITATIONS.some((c) => c.id === id)).toBe(true);
      for (const eq of [...c.equations, ...c.algorithms.map((a) => a.equation)])
        expect(() =>
          katex.renderToString(eq.tex, { throwOnError: true }),
        ).not.toThrow();
      for (const a of c.algorithms)
        for (const pair of [
          a.explanation,
          a.settings,
          a.history,
          a.limitation,
          ...a.steps,
        ])
          for (const text of pair) expect(text.length).toBeGreaterThan(20);
    }
  });
  it("keeps fonts, colour tokens and shell primitives owned by the shared shell", () => {
    const css = source("styles.css");
    expect(css).not.toMatch(/--(?:color-[\w-]+|font-[\w-]+|maxw[\w-]*)\s*:/);
    expect(css).not.toMatch(/Georgia|@font-face|:root|\[data-theme/);
    expect(css).not.toMatch(
      /(?:^|\n)\s*\.(?:prose|page-body|page-head|tabs|btn|select|range)\s*[{,]/,
    );
    expect(source("main.tsx")).toContain(
      "@fasl-work/caos-app-shell/styles.css",
    );
  });
  it("has bilingual token-themed architecture diagrams without custom fonts", () => {
    const folder = new URL("../../public/svg/tech/", import.meta.url);
    for (const f of readdirSync(folder).filter((f) => f.endsWith(".svg"))) {
      const svg = readFileSync(new URL(f, folder), "utf8");
      expect(svg).toContain('class="l-en');
      expect(svg).toContain('class="l-es');
      expect(svg).toContain("var(--color-");
      expect(svg).toContain("var(--font-sans)");
      expect(svg).not.toMatch(/#[0-9a-f]{3,8}\b|Georgia|serif/i);
    }
  });
  it("removes the rejected promotional headings from public pages", () => {
    const files = [
      "pages/Research.tsx",
      "pages/Workbench.tsx",
      "components/LiveMT.tsx",
      "architecture.ts",
      "main.tsx",
    ];
    const rejected = [
      "Compare errors, not appearances.",
      "Change one cause. Examine the consequence.",
      "One calculation. Traceable all the way to the screen.",
      "Follow the physics. Inspect the assumptions.",
      "Beneath the surface.",
      "Build a sounding, not an illustration.",
    ];
    for (const file of files)
      for (const phrase of rejected) expect(source(file)).not.toContain(phrase);
  });
  it("identifies actual algorithms and metric populations", () => {
    expect(methodName("mt-lm", false)).toMatch(/trust.region|TRF/i);
    expect(historyInfo("mt-lm", false).axis).toBe("Residual evaluation");
    expect(historyInfo("cnn", false).stride).toBe(5);
    expect(historyInfo("joint", false).stride).toBe(6);
    expect(metricInfo("wrms", "mt").description).toContain("√2");
    expect(metricInfo("wrms", "gravity").description).toContain(
      "active stations only",
    );
    expect(metricInfo("wrms", "joint", "joint").description).toContain(
      "all gravity stations",
    );
  });
});
describe("isosurface interpolation", () => {
  it("rejects incompatible input shapes", () =>
    expect(() =>
      isosurface([1], [2, 2, 2], [0, 0, 0], [1, 1, 1], 0.5),
    ).toThrow());
  it("returns no triangles for an empty field", () =>
    expect(
      isosurface(Array(8).fill(0), [2, 2, 2], [0, 0, 0], [1, 1, 1], 0.5).length,
    ).toBe(0));
  it("maps axes and stays within the physical grid bounds", () => {
    const p = isosurface(
      Array(8).fill(1),
      [2, 2, 2],
      [100, 200, -600],
      [50, 60, 70],
      0.5,
    );
    expect(p.length).toBeGreaterThan(0);
    expect(p.length % 9).toBe(0);
    for (let i = 0; i < p.length; i += 3) {
      expect(p[i]).toBeGreaterThanOrEqual(0.1);
      expect(p[i]).toBeLessThanOrEqual(0.200001);
      expect(p[i + 1]).toBeGreaterThanOrEqual(-0.600001);
      expect(p[i + 1]).toBeLessThanOrEqual(-0.459999);
      expect(p[i + 2]).toBeGreaterThanOrEqual(0.199999);
      expect(p[i + 2]).toBeLessThanOrEqual(0.320001);
    }
  });
  it("orients all triangles outward for a constant positive block", () => {
    const p = isosurface(
      Array(8).fill(1),
      [2, 2, 2],
      [-1, -1, -1],
      [1, 1, 1],
      0.5,
    );
    for (let i = 0; i < p.length; i += 9) {
      const a = Array.from(p.slice(i, i + 3)),
        b = Array.from(p.slice(i + 3, i + 6)),
        c = Array.from(p.slice(i + 6, i + 9));
      const u = b.map((v, k) => v - a[k]),
        v = c.map((v, k) => v - a[k]);
      const n = [
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
      ];
      expect(
        n.reduce((sum, v, k) => sum + (v * (a[k] + b[k] + c[k])) / 3, 0),
      ).toBeGreaterThanOrEqual(0);
    }
  });
});
