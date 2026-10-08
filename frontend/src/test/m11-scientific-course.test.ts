import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { CitationsProvider, useLangStore } from "@fasl-work/caos-app-shell";
import katex from "katex";
import { M11ScientificCourse } from "../components/M11ScientificCourse";
import { jointChapters, M11_COURSE_CITATIONS } from "../data/m11-scientific-course";

// SSR normally uses Zustand's initial hydration snapshot, not later client
// language changes. Exercise both copy branches; real client store in browser QA.
vi.mock("@fasl-work/caos-app-shell", async importOriginal => {
  const shell = await importOriginal<typeof import("@fasl-work/caos-app-shell")>();
  return { ...shell, useShellLang: () => shell.useLangStore.getState().lang };
});

describe("M11 deep scientific methodology, not a synthetic solve", () => {
  it("has six distinct bilingual reasoning chapters and literal definitions", () => {
    expect(new Set(jointChapters.map(chapter => chapter.id)).size).toBe(6);
    const ids = new Set(M11_COURSE_CITATIONS.map(citation => citation.id));
    for (const chapter of jointChapters) {
      for (const text of [chapter.title, chapter.caption, chapter.question, chapter.answer, chapter.limitation, ...chapter.paragraphs]) {
        expect(text).toHaveLength(2); expect(text[0]).not.toBe(text[1]);
        expect(text.every(value => value.length > 25)).toBe(true);
      }
      expect(chapter.refs.every(id => ids.has(id))).toBe(true);
      expect(katex.renderToString(chapter.tex, { throwOnError: true })).toContain("katex");
    }
  });
  it("preserves actual scalar, selection, failure and external custody boundaries", () => {
    const all = JSON.stringify(jointChapters);
    for (const word of ["Gram", "Cholesky", "1.05", "no_validated_coupling_benefit", "ULP", "250", "512", "1800", "24 refined-source", "SHA-256", "inactive hole", "quartic", "SciPy fallback"]) expect(all).toContain(word);
    expect(jointChapters.find(chapter => chapter.id === "coupling")!.tex).toContain("p_i t_i-h_i^2");
  });
  it.each(["en", "es"] as const)("renders escaped accessible %s content through shell", lang => {
    useLangStore.setState({ lang });
    const html = renderToStaticMarkup(createElement(CitationsProvider, { items: M11_COURSE_CITATIONS, children: createElement(M11ScientificCourse) }));
    expect(html).toContain("data-m11-course"); expect(html).toContain("data-m11-chapter=\"quantity\"");
    expect(html).toContain("aria-expanded=\"false\""); expect(html).toContain("katex");
    expect(html).toContain(lang === "es" ? "Pregunta científica" : "Scientific question");
    expect(html).not.toContain("<script"); expect(html).not.toContain("fetch(");
  });
});
