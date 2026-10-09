import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import katex from "katex";
import { mtArrayRows, mtSections } from "../data/online-mt-course";
import { mtQuestions } from "../components/OnlineMTExercise";
import { CITATIONS } from "../data/citations";
import worked from "../data/online-mt-worked.json";
const source = (path: string) => readFileSync(new URL("../" + path, import.meta.url), "utf8");
const prose = JSON.stringify(mtSections);

describe("online MT course", () => {
  it("scientific content and equations", () => {
    expect(mtSections).toHaveLength(12);
    for (const method of ["m05", "m06"]) for (const view of ["theory", "implementation"])
      expect(mtSections.filter(s => s.method === method && s.view === view)).toHaveLength(3);
    for (const section of mtSections) {
      expect(section.paragraphs).toHaveLength(4);
      expect(section.equations.length).toBeGreaterThanOrEqual(2);
      for (const p of section.paragraphs) {
        expect(CITATIONS.some(c => c.id === p.cite && (c.doi || c.url))).toBe(true);
        for (const text of p.text) {
          expect(text.length).toBeGreaterThan(350);
          expect(text).not.toMatch(/D:\\|docs\/|data-pipeline\/|ADR-\d/);
        }
        expect(p.text[0]).not.toBe(p.text[1]);
      }
      for (const eq of section.equations) {
        expect(() => katex.renderToString(eq.tex, { throwOnError: true })).not.toThrow();
        for (const caption of eq.caption) expect(caption.length).toBeGreaterThan(100);
      }
      expect(section.symbols.length).toBeGreaterThanOrEqual(2);
      for (const text of section.limitation) expect(text.length).toBeGreaterThan(80);
    }
    const component = source("components/OnlineMTCourse.tsx");
    for (const primitive of ["SubTabs", "Equation", "InlineMath", "Callout", "Cite", "Refs", "useShellLang"])
      expect(component).toContain(primitive);
  });
  it("implementation contract", () => {
    for (const value of ["objective_residual", "read_edi", "screen_edi", "_compatibility", "invert_edi", "invert_mt", "_inverse", "bootstrap_mt", "_trf_only", "identifiability", "2-point", "400", "300", "1e-10", "768 MiB", "32 MiB", "300 seconds"])
      expect(prose).toContain(value);
    expect(prose).toContain("not an analytic derivative");
    expect(prose).toContain("training objective");
    expect(prose).toContain("not least squares of log apparent resistivity");
    expect(mtArrayRows).toHaveLength(9);
    expect(mtArrayRows.find(row => row.quantity.startsWith("uncertainty"))?.shape).toBe("[B,L]; [L]");
  });
  it("field exclusion", () => {
    for (const value of ["cl061", "16,411", "320.233", "109.508", "267.600", "QC-only", "truth=null", "90c5c96cd69d6d29c866a768097cb3b38bc20e8b9c143e24bf10b2d253261e83"])
      expect(prose).toContain(value);
    expect(prose).toContain("no inverse model");
    expect(mtQuestions.find(q => q.id === "cl061")?.answer[0]).toMatch(/^No\./);
  });
  it("conditional scope", () => {
    for (const value of ["conditional", "posterior", "correlated", "static shift", "nonuniqueness", "fixed thickness", "central differences", "pointwise", "no activation"])
      expect(prose.toLowerCase()).toContain(value);
    expect(worked.synthetic).toBe(true);
    expect(worked.truth_passed_to_solver).toBe(false);
    expect(worked.cases.map(c => c.id)).toEqual(["fixed", "thin", "thick", "halfspace", "beta"]);
    expect(worked.training_mask.filter(Boolean)).toHaveLength(20);
    expect(worked.cases[1].heldout_wrms).toBeLessThan(worked.cases[0].heldout_wrms);
    expect(mtQuestions).toHaveLength(5);
    for (const q of mtQuestions) for (const pair of [q.prompt, q.answer]) {
      expect(pair[0]).not.toBe(pair[1]);
      for (const text of pair) expect(text.length).toBeGreaterThan(65);
    }
  });
  it("scoped integration", () => {
    const current = source("pages/Research.tsx");
    let expected = execFileSync("git", ["show", "afac8ab:frontend/src/pages/Research.tsx"], { encoding: "utf8" });
    expected = expected.replace('import { PhasePickerPanel } from "../components/PhasePickerPanel";', 'import { PhasePickerPanel } from "../components/PhasePickerPanel";\nimport { OnlineMTCourse, OnlineMTIntroduction } from "../components/OnlineMTCourse";');
    expected = expected.replace('content: <TheoryChapter chapter={chapter} /> }));', 'content: chapter.id === "mt"\n      ? <OnlineMTCourse view="theory" replay={<TheoryChapter chapter={chapter} />} />\n      : <TheoryChapter chapter={chapter} /> }));');
    expected = expected.replace('content: <SubTabs ariaLabel={t("Numerical algorithms", "Algoritmos numéricos")} tabs={algorithmsFor(chapter)} />,', 'content: chapter.id === "mt"\n            ? <OnlineMTCourse view="implementation" replay={<SubTabs ariaLabel={t("Numerical algorithms", "Algoritmos numéricos")} tabs={algorithmsFor(chapter)} />} />\n            : <SubTabs ariaLabel={t("Numerical algorithms", "Algoritmos numéricos")} tabs={algorithmsFor(chapter)} />,');
    // Introduction's expressly authorized opener/block/heading, no other seams.
    expected = expected.replace('"Geophysical inversion estimates subsurface properties from measured physical responses. This application compares density, magnetic susceptibility, resistivity and acoustic velocity in controlled synthetic experiments. The relation "', '"Geophysical research separates immutable observations, derived processing and conditional subsurface inversion. This platform combines audited synthetic lessons with owned CSV flag processing and reviewed bounded EDI QC/inversion; method-specific admission is not public host activation. The relation "');
    expected = expected.replace('"La inversión geofísica estima propiedades del subsuelo a partir de respuestas físicas medidas. Esta aplicación compara densidad, susceptibilidad, resistividad y velocidad acústica en experimentos sintéticos controlados. La relación "', '"La investigación geofísica separa observaciones inmutables, procesamiento derivado e inversión condicional del subsuelo. La plataforma combina lecciones sintéticas auditadas, flags de CSV propio y QC/inversión EDI acotados revisados; admisión por método no implica host público activo. La relación "');
    expected = expected.replace("      <section>", "      <OnlineMTIntroduction />\n      <section>");
    expected = expected.replace('"4. Experimental calculation and interpretation"', '"4. Synthetic experimental calculation and interpretation"').replace('"4. Cálculo e interpretación experimental"', '"4. Cálculo e interpretación experimental sintética"');
    // Only MAIN's explicitly approved M01 seams extend this full-file guard.
    expected = expected.replace('import { OnlineMTCourse, OnlineMTIntroduction } from "../components/OnlineMTCourse";', 'import { OnlineMTCourse, OnlineMTIntroduction } from "../components/OnlineMTCourse";\nimport { M01ScientificCourse } from "../components/M01ScientificCourse";');
    expected = expected.replace('tabs={released(["potential", "mt", "joint"])}', 'tabs={[\n        { id: "m01", label: t("Gravity processing", "Procesamiento gravimétrico"), content: <M01ScientificCourse /> },\n        ...released(["potential", "mt", "joint"]),\n      ]}');
    expected = expected.replace('ariaLabel={t("Field algorithms by method", "Algoritmos de campos por método")} tabs={chapters', 'ariaLabel={t("Field algorithms by method", "Algoritmos de campos por método")} tabs={[\n        { id: "m01", label: t("Gravity processing", "Procesamiento gravimétrico"), content: <M01ScientificCourse /> },\n        ...chapters');
    expected = expected.replace('        }))} />,\n    },\n    {\n      id: "waves",', '        })),\n      ]} />,\n    },\n    {\n      id: "waves",');
    // The reviewed pure-theory mount changes only these three exact seams;
    // keep full-file equality for every existing MT equation and algorithm.
    expected = expected.replace('import { M01ScientificCourse } from "../components/M01ScientificCourse";',
      'import { M01ScientificCourse } from "../components/M01ScientificCourse";\nimport { MagneticTheoryCourse } from "../components/MagneticTheoryCourse";');
    expected = expected.replace('        ...released(["potential", "mt", "joint"]),',
      '        { id: "magnetic-theory", label: t("Magnetic surveys", "Levantamientos magnéticos"), content: <MagneticTheoryCourse /> },\n        ...released(["potential", "mt", "joint"]),');
    expected = expected.replace('        ...chapters\n',
      '        { id: "magnetic-theory", label: t("Magnetic surveys", "Levantamientos magnéticos"), content: <MagneticTheoryCourse implementation /> },\n        ...chapters\n');
    // Exactly two deployment prose exceptions; retain whole-file science checks.
    const deploymentCopy = [
      ["The build copies already computed results. SimPEG/SciPy solve potential-field systems; PyTorch/Deepwave run differentiable and learned computations on the local GPU when available. GitHub Pages and the VPS serve static files. Only the layered MT forward calculator recomputes a physical response in the browser.",
        "The build copies already computed results. SimPEG/SciPy solve potential-field systems; PyTorch/Deepwave run differentiable and learned computations on the local GPU when available. The current live 0.04.001 deployment uses only the ML VPS; Pages publication has been withdrawn. The replacement keeps courses, curated replay and validated browser computations public, including layered MT forward calculation and locally implemented M13 phase-picking inference. Server project persistence, uploads and VPS jobs require login; implementation and local validation do not mean new VPS jobs are deployed."],
      ["El build copia resultados calculados. SimPEG/SciPy resuelven campos potenciales; PyTorch/Deepwave ejecutan cálculos diferenciables y aprendidos en GPU local disponible. Pages y VPS sirven archivos estáticos. Sólo la calculadora directa MT recalcula respuesta física en navegador.",
        "El build copia resultados calculados. SimPEG/SciPy resuelven campos potenciales; PyTorch/Deepwave ejecutan cálculos diferenciables y aprendidos en GPU local disponible. El despliegue live 0.04.001 actual usa sólo ML VPS; la publicación en Pages fue retirada. El reemplazo mantiene públicos los cursos, la reproducción curada y los cálculos validados en navegador, incluido MT directo por capas y la inferencia M13 de fases implementada localmente. La persistencia de proyectos, las cargas y las tareas VPS requieren inicio de sesión; la implementación y validación local no significan que se hayan desplegado nuevas tareas VPS."],
    ];
    for (const [oldCopy, newCopy] of deploymentCopy) {
      expect(expected.split(oldCopy)).toHaveLength(2);
      expect(current.split(newCopy)).toHaveLength(2);
      expected = expected.replace(oldCopy, newCopy);
    }
    expect(current.replaceAll("\r\n", "\n")).toBe(expected.replaceAll("\r\n", "\n"));
    const diagram = source("components/OnlineMTDiagram.tsx"), css = source("components/OnlineMTCourse.module.css");
    expect(diagram).toContain("useShellLang");
    expect(diagram).toContain("var(--color-accent)");
    expect(diagram + css).not.toMatch(/#[0-9a-f]{3,8}\b|@font-face|font-family|Georgia/i);
    expect(css).not.toMatch(/:root|\.page-body|\.tabs|data-theme/);
  });
  it("Introduction current scope", () => {
    const introduction = source("components/OnlineMTCourse.tsx").split("export function OnlineMTIntroduction")[1];
    for (const text of ["immutable original", "flag", "correction", "truth=null", "QC-only", "offline local CPU/GPU", "closed pending", "verification/re-import", "not public host activation"])
      expect(introduction + source("pages/Research.tsx")).toContain(text);
    expect(introduction).toContain("neither public API activation nor all M01–M13 methods online");
    const base = execFileSync("git", ["show", "afac8ab:frontend/src/pages/Research.tsx"], { encoding: "utf8" });
    const equations = (text: string) => [...text.split("function TheoryChapter")[0].matchAll(/tex=\{String\.raw`([^`]+)`\}/g)].map(m => m[1]);
    expect(equations(source("pages/Research.tsx"))).toEqual(equations(base));
  });
  it("orthogonal fields in a right-handed x-depth section", () => {
    const diagram = source("components/OnlineMTDiagram.tsx");
    expect(diagram).toContain('data-mt-direction="x-right" d="M50 70H155"');
    expect(diagram).toContain('data-mt-direction="z-down" d="M38 101V330"');
    const outOfPlane = diagram.split('data-mt-direction="y-out-of-plane"')[1].split("</g>")[0];
    expect(outOfPlane.match(/<circle /g)).toHaveLength(2);
    expect(outOfPlane).toContain('cx="250" cy="70" r="12"');
    expect(outOfPlane).toContain('cx="250" cy="70" r="3"');
    expect(outOfPlane).not.toContain("<path");
    for (const term of ["+y out of the page toward the viewer", "+z downward", "campos horizontales ortogonales", "no representan amplitudes"])
      expect(diagram).toContain(term);
  });
});
