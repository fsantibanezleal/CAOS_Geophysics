import { createElement, type ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { Cite, CitationsProvider, useLangStore } from "@fasl-work/caos-app-shell";
import { CITATIONS } from "../data/citations";
import { JointNativeStateInstrument, JointResultWorkbench } from "../components/JointResultWorkbench";
import { importJointOutput, jointFrameSidecar, jointInstrumentFrame, type JointFile } from "../api/joint-result";
import { format } from "../science";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

vi.mock("@fasl-work/caos-app-shell", async original => {
  const shell = await original<typeof import("@fasl-work/caos-app-shell")>();
  return { ...shell, useShellLang: () => shell.useLangStore.getState().lang };
});
function files(root: string): JointFile[] {
  const result: JointFile[] = []; function visit(dir: string) { for (const name of readdirSync(dir)) { const p = join(dir, name), info = statSync(p); if (info.isDirectory()) visit(p);
    else result.push({ path: relative(root, p).replaceAll("\\", "/"), size: info.size, read: async () => new Uint8Array(readFileSync(p)) }); } } visit(root); return result;
}
function renderRegistered(element: ReactElement): string {
  // Call through: diagnostics remain visible and are never mocked away.
  const warnings = vi.spyOn(console, "warn"), errors = vi.spyOn(console, "error");
  try {
    const html = renderToStaticMarkup(createElement(CitationsProvider, { items: CITATIONS, children: element }));
    expect(warnings).not.toHaveBeenCalled(); expect(errors).not.toHaveBeenCalled();
    expect(html).not.toMatch(/\[m11(?:source|cross)\]/);
    return html;
  } finally { warnings.mockRestore(); errors.mockRestore(); }
}
describe("joint scientific output instrument", () => {
  it("resolves both scientific citations through the actual application registry and provider", () => {
    for (const [id, href] of [
      ["m11source", "https://docs.simpeg.xyz/v0.25.2/content/api/generated/simpeg.regularization.CrossGradient.html"],
      ["m11cross", "https://doi.org/10.1029/2003JB002716"],
    ]) {
      expect(CITATIONS.filter(citation => citation.id === id)).toHaveLength(1);
      expect(renderRegistered(createElement(Cite, { id }))).toContain(`href="${href}"`);
    }
  });
  it.skipIf(!process.env.GEOPHYSICS_JOINT_INSTRUMENT_FIXTURE)("state export links", async () => {
    const initial = await importJointOutput(files(process.env.GEOPHYSICS_JOINT_INSTRUMENT_FIXTURE!));
    for (const lang of ["en", "es"] as const) { useLangStore.setState({ lang });
      const parent = renderRegistered(createElement(JointResultWorkbench, { initial })); expect(parent).toContain("docs/guides/22_local_joint_survey.md"); expect(parent).toContain("docs/data-contract/04_joint-local-inspection.md");
      const html = renderRegistered(createElement(JointNativeStateInstrument, { inspection: initial }));
      expect(html).toContain('href="https://doi.org/10.1029/2003JB002716"');
      expect(html).toContain('href="https://docs.simpeg.xyz/v0.25.2/content/api/generated/simpeg.regularization.CrossGradient.html"');
      expect(html).toContain('data-testid="joint-native-coupling-readout"'); expect(html).toContain(lang === "en" ? "Export this exact native frame JSON" : "Exportar este marco nativo exacto JSON");
      expect(html).toContain(lang === "en" ? 'aria-label="Native model frame"' : 'aria-label="Marco de modelo nativo"'); expect(html).toContain("nonconverged");
    }
  });
  it.skipIf(!process.env.GEOPHYSICS_JOINT_INSTRUMENT_FIXTURE)("formats native readouts without rounding arrays, cell attributes or exact exports", async () => {
    const initial = await importJointOutput(files(process.env.GEOPHYSICS_JOINT_INSTRUMENT_FIXTURE!));
    const frame = jointInstrumentFrame(initial, "selected", 0), original = jointFrameSidecar(initial, "selected", 0);
    const value = frame.model.arrays.density_kg_m3.values[0];
    const observed = frame.responses.gravity!.sealed.observed[0];
    for (const lang of ["en", "es"] as const) {
      useLangStore.setState({ lang });
      const html = renderRegistered(createElement(JointNativeStateInstrument, { inspection: initial }));
      expect(html).toContain(`data-value="${value}"`);
      expect(html).toContain(`${format(value)} kg/m³</output>`);
      const readout = html.match(/data-testid="joint-native-response-readout">([^<]*)<\/output>/)![1];
      expect(readout).toContain(`${format(observed)} /`);
      expect(readout).not.toMatch(/\d\.\d{10}/);
      expect(html).toContain(`data-cell="${frame.model.arrays.active_full_indices.values[0]}"`);
    }
    expect(frame.model.arrays.density_kg_m3.values[0]).toBe(value);
    expect(jointFrameSidecar(initial, "selected", 0)).toEqual(original);
    expect(JSON.parse(JSON.stringify(original))).toEqual(original);
  });
  it.each(["en", "es"] as const)("renders bilingual inspection boundary %s", lang => {
    useLangStore.setState({ lang }); const html = renderRegistered(createElement(JointResultWorkbench));
    expect(html).toContain(lang === "en" ? "Offline scientific processing; local browser inspection" : "Procesamiento científico fuera de línea; inspección local en navegador");
    expect(html).toContain(lang === "en" ? "Import local workflow output directory" : "Importar directorio local de resultados");
    expect(html).toContain("disabled"); expect(html).not.toContain("<script"); expect(html).not.toContain("<iframe");
  });
  it.skipIf(!process.env.GEOPHYSICS_JOINT_OUTPUT_FIXTURE)("renders actual physical result and exact selectors", async () => {
    const initial = await importJointOutput(files(process.env.GEOPHYSICS_JOINT_OUTPUT_FIXTURE!)); useLangStore.setState({ lang: "en" });
    const html = renderRegistered(createElement(JointResultWorkbench, { initial }));
    expect(html).toContain('aria-label="Joint scientific view"'); expect(html).toContain('aria-label="Survey response"');
    expect(html).toContain("predicted minus observed"); expect(html).toContain("candidate failures and scientific gates remain separate");
    expect(html).toContain('data-testid="joint-response-readout"'); expect(html).not.toContain("<script");
  });
});
