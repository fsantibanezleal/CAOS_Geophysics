import { describe, expect, it } from "vitest";
import { mapEncoding, mapScales, mapLabel } from "../components/M01CourseDiagram";

describe("M01 recorded map encoding", () => {
  it("signed and sequential encodings", () => {
    for (const field of ["field", "residual"] as const) {
      const [low, high] = mapScales[field];
      expect(mapEncoding(field, low)).toEqual({ colour: "var(--color-magenta)", opacity: 1 });
      expect(mapEncoding(field, high)).toEqual({ colour: "var(--color-accent)", opacity: 1 });
      expect(mapEncoding(field, 0).opacity).toBe(0);
      expect(mapEncoding(field, low / 2).opacity).toBe(.5);
      expect(mapEncoding(field, high / 2).opacity).toBe(.5);
      expect(mapEncoding(field, high * 2).opacity).toBe(1);
    }
    expect(mapEncoding("sigma", 0).opacity).toBe(0);
    expect(mapEncoding("sigma", .015)).toEqual({ colour: "var(--color-accent)", opacity: .5 });
    expect(mapEncoding("sigma", .03).opacity).toBe(1);
  });

  it("formats fixed endpoints without roundoff tails", () => {
    expect(mapLabel(.30000000000000004)).toBe("0.3");
    expect(mapLabel(-.1)).toBe("-0.1");
    expect(mapLabel(.015)).toBe("0.015");
    expect(mapLabel(0)).toBe("0");
  });
});
