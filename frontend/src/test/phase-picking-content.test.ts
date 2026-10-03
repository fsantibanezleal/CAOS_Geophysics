import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import katex from "katex";
import { chapters } from "../data/methods";
import { phasePickers } from "../data/phase-picking";
import { CITATIONS } from "../data/citations";

const source = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");
const allText = (id: "m08" | "m13", lang: 0 | 1) => {
  const method = phasePickers.find(item => item.id === id)!;
  return [method.title[lang], ...[method.theory, method.implementation].flatMap(section => [
    section.title[lang], ...section.paragraphs.map(p => p.text[lang]), ...section.equations.map(e => e.caption[lang]),
    ...section.symbols.map(pair => pair[lang]), ...section.steps?.map(pair => pair[lang]) ?? [], section.callout[lang],
  ])].join(" ");
};

describe("M08/M13 scientific content", () => {
  it("grouped_navigation_preserves_legacy_chapters", () => {
    expect(chapters.map(chapter => chapter.id)).toEqual(["potential", "mt", "seismic", "joint", "cnn", "ae"]);
    expect(phasePickers.map(method => method.id)).toEqual(["m08", "m13"]);
    const page = source("../pages/Research.tsx");
    expect(page).toContain('id: "fields"');
    expect(page).toContain('id: "waves"');
    expect(page).toContain('id: "learned"');
    expect(page).toContain('content: <PhasePickingContent method="m08" view="theory" />');
    expect(page).toContain('content: <PhasePickingContent method="m13" view="implementation" />');
    expect(source("../lib/routes.json")).not.toContain('"path": "/phase-picking"');
  });

  it("m08_content_and_units", () => {
    const method = phasePickers[0];
    expect(method.id).toBe("m08");
    expect(method.theory.paragraphs.length).toBeGreaterThanOrEqual(4);
    expect(method.implementation.paragraphs.length).toBeGreaterThanOrEqual(4);
    expect(method.implementation.steps?.length).toBeGreaterThanOrEqual(6);
    expect(method.theory.equations.length).toBeGreaterThanOrEqual(2);
    for (const lang of [0, 1] as const) {
      const text = allText("m08", lang);
      for (const term of ["MiniSEED", "StationXML", "m/s", "Hz", "UTC", "STA/LTA", "P/S", "AR-AIC"])
        expect(text).toContain(term);
      expect(text).toMatch(lang === 0 ? /onset detector, not a P\/S classifier/ : /detecta inicios; no clasifica P\/S/);
    }
    expect(method.theory.equations[1].tex).toContain("x_c[j]^2");
    expect(method.theory.equations[1].tex).toContain("N_L>N_S");
  });

  it("m13_architecture_loss_and_honesty", () => {
    const method = phasePickers[1];
    expect(method.id).toBe("m13");
    expect(method.theory.paragraphs.length).toBeGreaterThanOrEqual(4);
    expect(method.implementation.paragraphs.length).toBeGreaterThanOrEqual(4);
    expect(method.implementation.steps?.length).toBeGreaterThanOrEqual(6);
    expect(method.theory.equations.length).toBeGreaterThanOrEqual(3);
    for (const lang of [0, 1] as const) {
      const text = allText("m13", lang);
      for (const term of ["100 Hz", "3001", lang === 0 ? "0.1 s" : "0,1 s", "softmax", "P/S", "M08"])
        expect(text.toLowerCase()).toContain(term.toLowerCase());
      expect(text.toLowerCase()).toContain(lang === 0 ? "four downsampling stages" : "cuatro etapas descendentes");
      expect(text).toContain(lang === 0 ? "cross-entropy" : "entropía cruzada");
      expect(text).toContain(lang === 0 ? "A frozen M13 checkpoint" : "checkpoint M13");
    }
    expect(method.theory.equations[2].tex).toContain("\\log q_{k,n}");
  });

  it("disjoint_same_trace_evaluation_without_results", () => {
    const text = allText("m13", 0) + allText("m08", 0);
    for (const phrase of ["event-and-station-disjoint", "Bridge recordings", "same held-out", "one-to-one", "P/S confusion", "calibration", "abstention"])
      expect(text.toLowerCase()).toContain(phrase.toLowerCase());
    expect(text).toContain("The published PhaseNet split was stratified by station recordings");
    expect(text).toContain("The frozen M13 checkpoint and M08 comparator were scored");
    expect(source("../../../docs/design/features/phase-picking-content/research.md")).toContain("does **not** establish mutually exclusive event IDs");
  });

  it("equations_citations_and_diagrams", () => {
    const registry = new Map(CITATIONS.map(citation => [citation.id, citation]));
    for (const method of phasePickers) for (const section of [method.theory, method.implementation]) {
      for (const equation of section.equations) {
        expect(() => katex.renderToString(equation.tex, { throwOnError: true })).not.toThrow();
        expect(equation.caption[0].length).toBeGreaterThan(40);
        expect(equation.caption[1].length).toBeGreaterThan(40);
      }
      expect(section.paragraphs.length).toBeGreaterThanOrEqual(4);
      expect(section.symbols.length).toBeGreaterThanOrEqual(3);
      for (const paragraph of section.paragraphs) {
        expect(paragraph.text[0].length).toBeGreaterThan(180);
        expect(paragraph.text[1].length).toBeGreaterThan(140);
        expect(section.refs).toContain(paragraph.cite);
      }
      for (const id of section.refs) {
        const citation = registry.get(id);
        expect(citation, `missing citation ${id}`).toBeDefined();
        expect(citation!.doi || citation!.url).toBeTruthy();
      }
    }
    const diagram = source("../components/PhasePickingDiagram.tsx");
    expect(diagram).toContain('method === "m08"');
    expect(diagram).toContain("diagram-active");
    expect(diagram).toContain("diagram-edge");
    expect(diagram).not.toMatch(/#[0-9a-f]{3,8}\b|fontFamily|@font-face/i);
    const presentation = source("../components/PhasePickingContent.tsx");
    for (const primitive of ["<Equation", "<Cite", "<Refs", "<Callout", "<PhasePickingDiagram"])
      expect(presentation).toContain(primitive);
  });

  it("no_false_operation_claim", () => {
    const content = source("../components/PhasePickingContent.tsx") + source("../components/PhasePickingDiagram.tsx");
    expect(content).not.toMatch(/fetch\(|ApiClient|WebSocket|<button/i);
    expect(allText("m08", 0)).toContain("No local M08 short/long window lengths");
    expect(allText("m13", 0)).toContain("this frontend branch carries no model or field waveform bytes");
    expect(allText("m13", 0)).toContain("browser parity verdict");
  });

  it("wiki_source_links", () => {
    const wiki = source("../../../docs/problem-types/phase-picking.md");
    expect(source("../../../docs/README.md")).toContain("problem-types/phase-picking.md");
    expect(source("../../../docs/problem-types/problem-types.md")).toContain("phase-picking.md");
    for (const url of ["https://doi.org/10.1093/gji/ggy423", "https://doi.org/10.1785/bssa0680051521", "https://doi.org/10.1785/0120080019", "https://docs.obspy.org/"])
      expect(wiki).toContain(url);
    expect(wiki).toContain("5,926 are QC-valid and 74 QC rejections");
  });
});
