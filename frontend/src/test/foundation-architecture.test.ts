import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { architecture } from "../architecture";

describe("target architecture communication", () => {
  it("target_is_distinct_from_live_release", () => {
    expect(architecture.tabs).toHaveLength(5);
    for (const [index, tab] of architecture.tabs.entries()) {
      const file = ["01-the-app", "02-lanes", "03-web-flow", "04-the-science", "05-data-contracts"][index];
      const svg = readFileSync(new URL(`../../public/svg/tech/${file}.svg`, import.meta.url), "utf8");
      expect(svg).toContain("APPROVED TARGET");
      expect(svg).toContain("LIVE 0.04.001");
      expect(svg).toContain('class="arch-svg"');
      expect(svg).toContain("[data-arch-lang");
      expect(tab.body_en).toMatch(/target|planned/i);
      expect(tab.body_en).toMatch(/0\.04\.001/);
      expect(tab.body_es).toMatch(/objetivo|previst/i);
      expect(tab.body_es).toMatch(/0\.04\.001/);
    }
    expect(architecture.tabs[1].body_en).toMatch(/worker|CPU/);
    expect(architecture.tabs[4].body_en).toMatch(/Clear Lake|cl061/);
  });
  it("single VPS legacy and replacement public client remain distinct", () => {
    const system = architecture.tabs[0], lanes = architecture.tabs[1];
    expect(system.body_en).toContain("ML VPS only; Pages publication has been withdrawn");
    expect(system.body_es).toContain("sólo en ML VPS; la publicación en Pages fue retirada");
    expect(system.body_en).toContain("server project persistence, uploads and VPS jobs require login");
    expect(system.body_es).toContain("persistencia de proyectos, las cargas y las tareas VPS requieren inicio de sesión");
    expect(system.body_en).toContain("not a claim that new VPS jobs are deployed");
    expect(system.body_es).toContain("no afirma que se hayan desplegado nuevas tareas VPS");
    expect(lanes.body_en).toContain("public M13 phase-picking inference locally in the browser");
    expect(lanes.body_es).toContain("inferencia pública M13 de fases localmente en el navegador");
    expect(lanes.body_en).toContain("do not establish replacement API or new VPS-job deployment");
    expect(lanes.body_es).toContain("no acreditan el despliegue de la API de reemplazo ni de nuevas tareas VPS");
    expect(system.body_en + lanes.body_en).not.toMatch(/on Pages and|two static origins|computes only bounded MT/);
    expect(system.body_es + lanes.body_es).not.toMatch(/en Pages y|dos orígenes estáticos|sólo calcula MT/);
  });
});
