import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProjectProcessingWorkbench } from "../components/ProjectProcessingWorkbench";
import { ProfileProjectWorkbench } from "../components/ProfileProjectWorkbench";

// Rendering admission only. Effects are not executed by SSR; no mocked solver
// output, authenticated API workflow or native host qualification is claimed.
describe("shared owned-project instrument navigation", () => {
  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
  for (const instrument of ["gravity", "mt", "profiles", "waveform", "joint"]) {
    it.each([false, true])(`mounts ${instrument} without switching project, Spanish=%s`, es => {
      const projectId = "11111111-1111-4111-8111-111111111111";
      const consoleError=vi.spyOn(console,"error");
      const url = new URL(`https://geophysics.ml.fasl-work.com/?project=${projectId}&instrument=${instrument}`);
      vi.stubGlobal("window", { location: url, history: { replaceState: vi.fn() } });
      const html = renderToStaticMarkup(createElement(ProjectProcessingWorkbench, {
        projectId, es, onManage: () => {}, onCurated: () => {},
      }));
      expect(html).toContain(es ? "Método del proyecto" : "Project method");
      expect((html.match(/selected=""/g) ?? []).length).toBeGreaterThanOrEqual(1);
      expect(html).toMatch(new RegExp(`<option value="${instrument}" selected=""`));
      // A single root instrument prevents the shell from treating navigation
      // and the workbench as side-by-side independent page bodies.
      expect(html.startsWith(instrument==="profiles"?'<div class="page-body wide caos-wb':'<div class="page-body wide workbench')).toBe(true);
      expect(html.indexOf('<nav class="processing-actions"')).toBeGreaterThan(html.indexOf('<aside'));
      expect((html.match(/<aside\b/g)??[])).toHaveLength(1);
      expect(html).toContain(instrument==="profiles"?"caos-wb-rail":"instrument-sidebar processing-sidebar");
      if(instrument!=="waveform"){
        for(const shortcut of ["Gravity station QC","QC gravimétrico","MT transfer functions","Funciones de transferencia MT","ERT / first-arrival profiles","ERT / perfiles de primeras llegadas"]){
          expect(html).not.toContain(`>${shortcut}</button>`);
        }
      }
      expect(html).toContain("instrument-main processing-main");
      expect(window.location.href).toBe(url.href);
      expect(window.history.replaceState).not.toHaveBeenCalled();
      expect(html).not.toContain("font-family");
      expect(consoleError).not.toHaveBeenCalled();
    });
  }
  it.each([false,true])("preserves standalone profile method callbacks, Spanish=%s",es=>{
    vi.stubGlobal("window",{location:new URL("https://example.invalid/")});
    const html=renderToStaticMarkup(createElement(ProfileProjectWorkbench,{projectId:"11111111-1111-4111-8111-111111111111",es,onManage:()=>{},onCurated:()=>{},onGravity:()=>{},onMt:()=>{}}));
    expect(html).toContain(es?"QC gravimétrico":"Gravity station QC");
    expect(html).toContain(es?"Funciones de transferencia MT":"MT transfer functions");
    expect((html.match(/<aside\b/g)??[])).toHaveLength(1);
  });
});
