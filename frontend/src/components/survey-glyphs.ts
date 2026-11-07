/** Median adjacent station interval on each acquisition axis, in metres. */
export function surveyStationPitch(locations: number[][]): [number, number] {
  if (locations.length < 2 || locations.some(p => p.length < 2 || !p.slice(0, 2).every(Number.isFinite)))
    throw new Error("Survey glyphs require finite easting/northing locations");

  const axisPitch = (axis: 0 | 1) => {
    const coordinates = [...new Set(locations.map(p => p[axis]))].sort((a, b) => a - b);
    const intervals = coordinates.slice(1).map((value, i) => value - coordinates[i]).filter(value => value > 0);
    if (!intervals.length) return undefined;
    intervals.sort((a, b) => a - b);
    const middle = Math.floor(intervals.length / 2);
    return intervals.length % 2 ? intervals[middle] : (intervals[middle - 1] + intervals[middle]) / 2;
  };

  const east = axisPitch(0);
  const north = axisPitch(1);
  const fallback = east ?? north;
  if (fallback === undefined) throw new Error("Survey locations do not define station spacing");
  return [east ?? fallback, north ?? fallback];
}

/** Point glyph diameter occupies half the tighter observed station interval. */
export function surveyGlyphDiameter(locations: number[][]): number {
  const [east, north] = surveyStationPitch(locations);
  return Math.min(east, north) * 0.5;
}
