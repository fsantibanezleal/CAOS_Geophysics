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
});
