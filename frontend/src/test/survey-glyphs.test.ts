import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { surveyGlyphDiameter, surveyStationPitch } from "../components/survey-glyphs";

const artifact = JSON.parse(readFileSync(new URL("../../../data/derived/v2/GRAVITY_INTRUSION/reference.json", import.meta.url), "utf8")) as {
  survey: { locations: number[][] };
};
const locations = artifact.survey.locations;

describe("survey station glyph geometry", () => {
  it("derives physical pitch and a non-overlapping marker from committed receiver coordinates", () => {
    const pitch = surveyStationPitch(locations);
    expect(pitch[0]).toBeCloseTo(67.7419, 3);
    expect(pitch[1]).toBeCloseTo(58.0645, 3);
    expect(surveyGlyphDiameter(locations)).toBeCloseTo(29.03225, 3);
    expect(surveyGlyphDiameter(locations)).toBeLessThan(Math.min(...pitch));
  });

  it("uses the available axis spacing for a single-line acquisition", () => {
    const row = locations.filter(p => p[1] === locations[0][1]);
    const pitch = surveyStationPitch(row);
    expect(pitch[0]).toBeCloseTo(67.7419, 3);
    expect(pitch[1]).toBe(pitch[0]);
    expect(surveyGlyphDiameter(row)).toBeCloseTo(33.87095, 3);
  });

  it("rejects locations without finite physical coordinates", () => {
    expect(() => surveyGlyphDiameter([])).toThrow("finite easting/northing");
    expect(() => surveyGlyphDiameter([[0, Number.NaN, 0]])).toThrow("finite easting/northing");
  });
});
