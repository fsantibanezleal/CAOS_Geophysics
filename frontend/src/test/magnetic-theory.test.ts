import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import katex from "katex";
import { CitationsProvider, useLangStore } from "@fasl-work/caos-app-shell";
import { MagneticTheoryCourse } from "../components/MagneticTheoryCourse";
import { magneticLessons } from "../data/magnetic-survey-course";
import { magneticDerivations } from "../data/magnetic-course-derivations";
import { CITATIONS } from "../data/citations";

// SSR copy coverage only; browser gate uses the real shell store.
vi.mock("@fasl-work/caos-app-shell", async original => {
  const shell = await original<typeof import("@fasl-work/caos-app-shell")>();
  return { ...shell, useShellLang: () => shell.useLangStore.getState().lang };
});
describe("magnetic theory independent of fitted results", () => {
  it("retains all nine bilingual extended definitions, equations and questions", () => {
    expect(new Set(magneticLessons.map(lesson => lesson.id)).size).toBe(9);
    expect(Object.keys(magneticDerivations).sort()).toEqual(magneticLessons.map(lesson => lesson.id).sort());
    for (const lesson of magneticLessons) {
      const derivation = magneticDerivations[lesson.id];
      for (const text of [lesson.title, lesson.body, lesson.symbols, lesson.limit, derivation.symbols,
        derivation.exercise, derivation.answer, derivation.implementation, ...derivation.paragraphs]) {
        expect(text).toHaveLength(2); expect(text[0]).not.toBe(text[1]);
        expect(text.every(value => value.length > 15)).toBe(true);
      }
      for (const equation of [lesson.equation, derivation.equation])
        expect(katex.renderToString(equation, { throwOnError: true })).toContain("katex");
    }
  });
  it("resolves every primary reference once in the existing root registry", () => {
    const ids = CITATIONS.map(citation => citation.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const lesson of magneticLessons) for (const ref of lesson.references) {
      expect(CITATIONS.filter(citation => citation.id === ref.id)).toHaveLength(1);
      expect(CITATIONS.find(citation => citation.id === ref.id)!.url).toBe(ref.url);
      expect(ref.url).toMatch(/^https:\/\/raw\.githubusercontent\.com\//);
    }
  });
  it("uses scientific subject headings rather than slogans", () => {
    expect(magneticLessons.map(lesson => lesson.title[0])).toEqual([
      "Magnetic observations and physical metadata", "Induced magnetization and susceptibility parameterization",
      "Covariance-weighted data misfit", "Volume- and face-weighted L2 regularization",
      "Smoothed L1 penalty and IRLS updates", "Geometry-defined folds and training-only selection",
      "Bound-constrained optimization and stopping criteria", "Sensitivity and conditional model resolution",
      "Local execution, artifacts and provenance",
    ]);
  });
  it.each(["en", "es"] as const)("renders %s theory with no fitted object, file input or fabricated metric", lang => {
    useLangStore.setState({ lang });
    const html = renderToStaticMarkup(createElement(CitationsProvider, { items: CITATIONS,
      children: createElement(MagneticTheoryCourse, { implementation: true }) }));
    expect(html).toContain('data-lesson="original"'); expect(html).toContain("katex");
    expect(html).toContain(lang === "es" ? "Pregunta razonada" : "Worked question");
    expect(html).toContain("magnetic_survey.py: plan_geometry");
    expect(html).toContain("<details>"); expect(html).not.toContain('type="file"');
    expect(html).not.toContain("data-generation"); expect(html).not.toContain("<script");
  });
  it("mounts both research pages without a result dependency or second provider", () => {
    const component = readFileSync("src/components/MagneticTheoryCourse.tsx", "utf8");
    const research = readFileSync("src/pages/Research.tsx", "utf8");
    expect(component).not.toMatch(/import.*MagneticView|fetch\(|CitationsProvider|style=/);
    expect(research.match(/id: "magnetic-theory"/g)).toHaveLength(2);
    expect(research).toContain("<MagneticTheoryCourse implementation />");
  });
});
