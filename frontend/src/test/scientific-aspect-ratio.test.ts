import { describe, expect, it } from "vitest";
import { heatmapAspectRatio } from "../components/ScientificPlots";

describe("physical heatmap aspect ratio", () => {
  it("uses equal physical axis ranges for a square map", () => {
    expect(heatmapAspectRatio(undefined, [-1050, 1050], [-1050, 1050])).toBe(1);
  });

  it("preserves the physical scale ratio for unequal survey extents", () => {
    expect(heatmapAspectRatio(undefined, [-1200, 1200], [-800, 800])).toBe(1.5);
  });

  it("honors an explicit diagram ratio", () => {
    expect(heatmapAspectRatio(1.45, [-1050, 1050], [-1050, 1050])).toBe(1.45);
  });

  it("does not invent geometry when coordinate ranges are unavailable or degenerate", () => {
    expect(heatmapAspectRatio(undefined)).toBeUndefined();
    expect(heatmapAspectRatio(undefined, [1, 1], [0, 2])).toBeUndefined();
  });
});
