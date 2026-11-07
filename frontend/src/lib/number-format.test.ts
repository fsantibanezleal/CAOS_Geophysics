import { afterEach, describe, expect, it, vi } from "vitest";
import { formatCount, formatForCurrentLocale, formatNumber } from "./number-format";

describe("display number formatting", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("uses Chilean Spanish decimal and grouping separators", () => {
    expect(formatNumber(-0.7588, "es-CL")).toBe("-0,7588");
    expect(formatCount(6000, "es-CL")).toBe("6.000");
  });

  it("retains English formatting and supports scientific magnitudes", () => {
    expect(formatNumber(0.7588, "en-US")).toBe("0.7588");
    expect(formatNumber(6.17e-8, "es-CL")).not.toContain(".");
  });

  it("does not change source values and preserves non-finite labels", () => {
    const source = 0.7588;
    expect(formatNumber(source, "es-CL")).toBe("0,7588");
    expect(source).toBe(0.7588);
    expect(formatNumber(Number.NaN, "es-CL")).toBe("NaN");
  });

  it("follows the active shell document language for reusable instruments", () => {
    vi.stubGlobal("document", { documentElement: { lang: "es" } });
    expect(formatForCurrentLocale(0.7588)).toBe("0,7588");
  });
});
