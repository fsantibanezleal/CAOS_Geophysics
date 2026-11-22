export type LVMeasurement = { epoch: string; gravity_mgal: number; sigma_mgal: number; qc?: { status: "suspect"; reason: string; review: string } };
export type LVStation = { station_id: string; easting_m: number; northing_m: number; measurements: LVMeasurement[] };
export type LVDifferenceRow = {
  station_id: string;
  easting_m: number;
  northing_m: number;
  earlier_gravity_mgal: number;
  earlier_sigma_mgal: number;
  later_gravity_mgal: number;
  later_sigma_mgal: number;
  delta_gravity_mgal: number;
  delta_sigma_independent_mgal: number;
  standardized_delta_independent: number;
};
export type LongValleyCase = {
  schema: "geophysics.field.gravity-time-lapse/v2";
  source: { title: string; provider: string; data_url: string; format_metadata_url: string; fgdc_metadata_url: string; source_sha256: string; metadata_sha256: string; retrieved_date: string; attribution: string };
  observation_contract: { horizontal_coordinates: string; gravity_unit: string; uncertainty: string; processing_history: string; interpretation_limits: string[]; quality_control: string };
  epochs: string[];
  station_count: number;
  measurement_count: number;
  stations: LVStation[];
  difference: { earlier_epoch: string; later_epoch: string; difference_convention: "later-minus-earlier"; uncertainty_model: string; stations: LVDifferenceRow[] };
};

const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

export function parseLongValleyCase(value: unknown): LongValleyCase {
  if (!value || typeof value !== "object") throw new Error("Long Valley artifact is not an object");
  const data = value as Partial<LongValleyCase>;
  if (data.schema !== "geophysics.field.gravity-time-lapse/v2" || !Array.isArray(data.epochs) || !Array.isArray(data.stations) || !data.source || !data.observation_contract || !data.difference)
    throw new Error("Long Valley artifact has an unsupported schema");
  if (data.station_count !== data.stations.length || new Set(data.epochs).size !== data.epochs.length || data.epochs.length < 2)
    throw new Error("Long Valley artifact station or epoch count is inconsistent");
  const ids = new Set<string>();
  let n = 0;
  for (const station of data.stations) {
    if (!station.station_id || ids.has(station.station_id) || !finite(station.easting_m) || !finite(station.northing_m) || !Array.isArray(station.measurements))
      throw new Error("Long Valley station identity or geometry is invalid");
    ids.add(station.station_id);
    let previous = "";
    for (const measurement of station.measurements) {
      if (!data.epochs.includes(measurement.epoch) || measurement.epoch <= previous || !finite(measurement.gravity_mgal) || !finite(measurement.sigma_mgal) || measurement.sigma_mgal <= 0)
        throw new Error(`Long Valley measurement is invalid at ${station.station_id}`);
      if (measurement.qc && (measurement.qc.status !== "suspect" || typeof measurement.qc.reason !== "string" || !measurement.qc.reason || typeof measurement.qc.review !== "string" || !measurement.qc.review))
        throw new Error(`Long Valley quality flag is invalid at ${station.station_id}`);
      previous = measurement.epoch;
      n++;
    }
  }
  if (n !== data.measurement_count || data.difference.difference_convention !== "later-minus-earlier" ||
      !data.epochs.includes(data.difference.earlier_epoch) || !data.epochs.includes(data.difference.later_epoch) ||
      !Array.isArray(data.difference.stations) || typeof data.observation_contract.quality_control !== "string")
    throw new Error("Long Valley artifact measurement count or difference convention is inconsistent");
  const replay = differenceEpochs(data as LongValleyCase, data.difference.earlier_epoch, data.difference.later_epoch);
  if (replay.length !== data.difference.stations.length)
    throw new Error("Long Valley precomputed difference station count does not replay");
  const tolerance = (expected: number, actual: unknown) => finite(actual) && Math.abs(expected - actual) <= 1e-12 + Math.abs(expected) * 1e-14;
  const rowFields: Exclude<keyof LVDifferenceRow, "station_id">[] = ["easting_m", "northing_m", "earlier_gravity_mgal", "earlier_sigma_mgal", "later_gravity_mgal", "later_sigma_mgal", "delta_gravity_mgal", "delta_sigma_independent_mgal", "standardized_delta_independent"];
  const recorded = new Map(data.difference.stations.map((row) => [row.station_id, row]));
  if (recorded.size !== data.difference.stations.length || replay.some((row) => {
    const stored = recorded.get(row.station_id);
    return !stored || rowFields.some((field) => !tolerance(row[field], stored[field]));
  })) throw new Error("Long Valley precomputed differences do not replay from the occupation arrays");
  if (!/^[0-9a-f]{64}$/.test(data.source.source_sha256) || !/^[0-9a-f]{64}$/.test(data.source.metadata_sha256))
    throw new Error("Long Valley source identity is invalid");
  return data as LongValleyCase;
}

export function differenceEpochs(data: LongValleyCase, earlier: string, later: string, includeSuspect = false): LVDifferenceRow[] {
  if (!data.epochs.includes(earlier) || !data.epochs.includes(later) || earlier === later)
    throw new Error("Choose two distinct occupations in the source");
  const output: LVDifferenceRow[] = [];
  for (const station of data.stations) {
    const a = station.measurements.find((m) => m.epoch === earlier);
    const b = station.measurements.find((m) => m.epoch === later);
    if (!a || !b) continue;
    if (!includeSuspect && (a.qc?.status === "suspect" || b.qc?.status === "suspect")) continue;
    const delta = b.gravity_mgal - a.gravity_mgal;
    const sigma = Math.hypot(a.sigma_mgal, b.sigma_mgal);
    output.push({ station_id: station.station_id, easting_m: station.easting_m, northing_m: station.northing_m, earlier_gravity_mgal: a.gravity_mgal, earlier_sigma_mgal: a.sigma_mgal, later_gravity_mgal: b.gravity_mgal, later_sigma_mgal: b.sigma_mgal, delta_gravity_mgal: delta, delta_sigma_independent_mgal: sigma, standardized_delta_independent: delta / sigma });
  }
  return output;
}
