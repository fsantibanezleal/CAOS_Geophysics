export type AmargosaLine = {
  line_id: string;
  role: "flight" | "tie";
  coordinate_extent_m: { easting: [number, number]; northing: [number, number] };
};

export type AmargosaResult = {
  schema: "magnetic-flightline-process-result-1";
  source: { source_id: string; sha256: string; citation: string; value_unit: "nT" };
  claims: { source_hash_recomputed_from_original_bytes: boolean; inverse_model: boolean; scientific_release_accepted: boolean };
  source_selection: {
    selected_channel: string;
    track_count: { flight: number; tie: number };
    tracks: { track_id: string; role: "flight" | "tie"; representative_source_line_id: string; representative_sample_count: number }[];
  };
  geometry_qc: { lines: AmargosaLine[] };
  heldout_interpolation: { heldout_line_ids: string[]; heldout_row_count: number; coverage_fraction: number; mae: number; rmse: number; interpretation: string };
  grid: { x_easting_m: number[]; y_northing_m: number[]; shape_yx: [number, number]; values: number[][]; support_mask: boolean[][]; unsupported_value_encoding?: string };
  source_acquisition_receipt: { sha256: string; bytes: number; citation: string; validation_status: string };
};

const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const digest = (value: unknown): value is string => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);

export function parseAmargosaResult(value: unknown): AmargosaResult {
  if (!value || typeof value !== "object") throw new Error("Amargosa artifact is not an object");
  const data = value as Partial<AmargosaResult>;
  if (data.schema !== "magnetic-flightline-process-result-1" || !data.source || !data.claims || !data.source_selection ||
      !data.geometry_qc || !data.heldout_interpolation || !data.grid || !data.source_acquisition_receipt)
    throw new Error("Amargosa artifact has an unsupported schema");
  if (!digest(data.source.sha256) || data.source_acquisition_receipt.sha256 !== data.source.sha256 ||
      data.claims.source_hash_recomputed_from_original_bytes !== true || data.claims.inverse_model !== false ||
      data.claims.scientific_release_accepted !== false || data.source.value_unit !== "nT")
    throw new Error("Amargosa source identity or scientific boundary is inconsistent");
  const geometry = data.geometry_qc as AmargosaResult["geometry_qc"];
  const { x_easting_m: x, y_northing_m: y, shape_yx: shape, values, support_mask: mask } = data.grid;
  if (!Array.isArray(x) || !Array.isArray(y) || !Array.isArray(shape) || shape[0] !== y.length || shape[1] !== x.length ||
      !Array.isArray(values) || !Array.isArray(mask) || values.length !== y.length || mask.length !== y.length ||
      x.length < 2 || y.length < 2 || [...x, ...y].some((n) => !finite(n)) ||
      x.some((n, i) => i > 0 && n <= x[i - 1]) || y.some((n, i) => i > 0 && n <= y[i - 1]))
    throw new Error("Amargosa grid axes or dimensions are invalid");
  for (let row = 0; row < y.length; row++) {
    if (!Array.isArray(values[row]) || !Array.isArray(mask[row]) || values[row].length !== x.length || mask[row].length !== x.length)
      throw new Error("Amargosa grid row dimensions are invalid");
    for (let column = 0; column < x.length; column++) {
      const cell = values[row][column];
      if (typeof mask[row][column] !== "boolean" || !finite(cell) || (!mask[row][column] && cell !== 0))
        throw new Error("Amargosa grid values and support mask disagree");
    }
  }
  const tracks = data.source_selection.tracks;
  if (!Array.isArray(tracks) || !Array.isArray(geometry.lines) || tracks.length !== geometry.lines.length ||
      data.source_selection.track_count.flight !== tracks.filter((track) => track.role === "flight").length ||
      data.source_selection.track_count.tie !== tracks.filter((track) => track.role === "tie").length ||
      tracks.some((track) => !geometry.lines.some((line) => line.line_id === track.track_id && line.role === track.role)))
    throw new Error("Amargosa selected tracks do not match the geometry summary");
  const score = data.heldout_interpolation;
  if (!finite(score.coverage_fraction) || score.coverage_fraction < 0 || score.coverage_fraction > 1 ||
      !finite(score.mae) || !finite(score.rmse) || score.mae < 0 || score.rmse < score.mae ||
      score.heldout_row_count < 1 || score.interpretation !== "spatial interpolation on withheld whole flight lines; not a subsurface inverse")
    throw new Error("Amargosa held-out score or interpretation is invalid");
  return data as AmargosaResult;
}

export async function parseAmargosaBytes(bytes: ArrayBuffer, expectedSha256: string): Promise<AmargosaResult> {
  if (!digest(expectedSha256)) throw new Error("Amargosa artifact digest pin is invalid");
  const actual = Array.from(new Uint8Array(await globalThis.crypto.subtle.digest("SHA-256", bytes)))
    .map((value) => value.toString(16).padStart(2, "0")).join("");
  if (actual !== expectedSha256) throw new Error("Amargosa artifact bytes differ from the reviewed field-study index");
  let value: unknown;
  try { value = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)); }
  catch { throw new Error("Amargosa artifact is not valid UTF-8 JSON"); }
  return parseAmargosaResult(value);
}
