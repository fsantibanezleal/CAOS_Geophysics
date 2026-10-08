import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { useLangStore } from "@fasl-work/caos-app-shell";
import { JointNativeStateInstrument, JointResultWorkbench } from "../components/JointResultWorkbench";
import { importJointOutput, type JointFile } from "../api/joint-result";
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
describe("joint scientific output instrument", () => {
  it.skipIf(!process.env.GEOPHYSICS_JOINT_INSTRUMENT_FIXTURE)("state export links", async () => {
    const initial = await importJointOutput(files(process.env.GEOPHYSICS_JOINT_INSTRUMENT_FIXTURE!));
    for (const lang of ["en", "es"] as const) { useLangStore.setState({ lang });
      const parent = renderToStaticMarkup(createElement(JointResultWorkbench, { initial })); expect(parent).toContain("docs/guides/22_local_joint_survey.md"); expect(parent).toContain("docs/data-contract/04_joint-local-inspection.md");
      const html = renderToStaticMarkup(createElement(JointNativeStateInstrument, { inspection: initial }));
      expect(html).toContain('data-testid="joint-native-coupling-readout"'); expect(html).toContain(lang === "en" ? "Export this exact native frame JSON" : "Exportar este marco nativo exacto JSON");
      expect(html).toContain(lang === "en" ? 'aria-label="Native model frame"' : 'aria-label="Marco de modelo nativo"'); expect(html).toContain("nonconverged");
    }
  });
  it.each(["en", "es"] as const)("renders bilingual inspection boundary %s", lang => {
    useLangStore.setState({ lang }); const html = renderToStaticMarkup(createElement(JointResultWorkbench));
    expect(html).toContain(lang === "en" ? "Offline scientific processing; local browser inspection" : "Procesamiento científico fuera de línea; inspección local en navegador");
    expect(html).toContain(lang === "en" ? "Import local workflow output directory" : "Importar directorio local de resultados");
    expect(html).toContain("disabled"); expect(html).not.toContain("<script"); expect(html).not.toContain("<iframe");
  });
  it.skipIf(!process.env.GEOPHYSICS_JOINT_OUTPUT_FIXTURE)("renders actual physical result and exact selectors", async () => {
    const initial = await importJointOutput(files(process.env.GEOPHYSICS_JOINT_OUTPUT_FIXTURE!)); useLangStore.setState({ lang: "en" });
    const html = renderToStaticMarkup(createElement(JointResultWorkbench, { initial }));
    expect(html).toContain('aria-label="Joint scientific view"'); expect(html).toContain('aria-label="Survey response"');
    expect(html).toContain("predicted minus observed"); expect(html).toContain("candidate failures and scientific gates remain separate");
    expect(html).toContain('data-testid="joint-response-readout"'); expect(html).not.toContain("<script");
  });
});
