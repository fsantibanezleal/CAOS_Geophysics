import type { RawUploadDeclaration } from "./lifecycle";

type FieldKind = "text" | "integer" | "number" | "list" | "stationxml";
export interface GeometryField { key: string; en: string; es: string; kind: FieldKind; positive?: boolean; optional?: boolean }
interface FormatSpec { en: string; es: string; extensions: string[]; mimes: string[]; maxMiB: number; units: string[]; frames: string[]; geometry: GeometryField[] }
const field = (key: string, en: string, es: string, kind: FieldKind = "text", positive = false, optional = false): GeometryField => ({ key, en, es, kind, positive, optional });
const channels = field("channels", "Channel codes (comma-separated)", "Códigos de canal (separados por coma)", "list");

export const FORMAT_SPECS = {
  gravity_csv: { en: "Gravity station CSV", es: "CSV de estaciones gravimétricas", extensions: [".csv"], mimes: ["text/csv"], maxMiB: 50, units: ["mGal", "m/s2"], frames: ["local vertical down", "local vertical up"], geometry: [field("station_id_column", "Station ID column", "Columna de estación"), field("x_column", "X column", "Columna X"), field("y_column", "Y column", "Columna Y"), field("z_column", "Z column", "Columna Z"), field("value_column", "Value column", "Columna de valor"), field("sigma_column", "Sigma column (required for flag QC)", "Columna sigma (necesaria para QC de marcas)", "text", false, true)] },
  magnetic_csv: { en: "Magnetic flight-line CSV", es: "CSV de líneas magnéticas", extensions: [".csv"], mimes: ["text/csv"], maxMiB: 50, units: ["nT"], frames: ["total field", "ENU", "NED"], geometry: [field("line_id_column", "Line ID column", "Columna de línea"), field("x_column", "X column", "Columna X"), field("y_column", "Y column", "Columna Y"), field("z_column", "Z column", "Columna Z"), field("value_column", "Value column", "Columna de valor")] },
  traveltime_csv: { en: "Traveltime CSV", es: "CSV de tiempos de viaje", extensions: [".csv"], mimes: ["text/csv"], maxMiB: 50, units: ["s", "ms"], frames: ["source-receiver"], geometry: [field("source_x_column", "Source X column", "Columna X fuente"), field("source_y_column", "Source Y column", "Columna Y fuente"), field("receiver_x_column", "Receiver X column", "Columna X receptor"), field("receiver_y_column", "Receiver Y column", "Columna Y receptor"), field("time_column", "Time column", "Columna de tiempo")] },
  ert_csv: { en: "ERT electrode CSV", es: "CSV de electrodos ERT", extensions: [".csv"], mimes: ["text/csv"], maxMiB: 50, units: ["ohm", "V", "ohm.m"], frames: ["ABMN"], geometry: [field("a_column", "A electrode column", "Columna electrodo A"), field("b_column", "B electrode column", "Columna electrodo B"), field("m_column", "M electrode column", "Columna electrodo M"), field("n_column", "N electrode column", "Columna electrodo N"), field("electrode_count", "Electrode count", "Cantidad de electrodos", "integer", true)] },
  geotiff: { en: "GeoTIFF grid", es: "Grilla GeoTIFF", extensions: [".tif", ".tiff"], mimes: ["image/tiff", "application/geotiff"], maxMiB: 200, units: ["nT", "mGal"], frames: ["total field", "local vertical down", "local vertical up"], geometry: [field("rows", "Rows", "Filas", "integer", true), field("columns", "Columns", "Columnas", "integer", true), field("pixel_width", "Pixel width", "Ancho de píxel", "number", true), field("pixel_height", "Pixel height", "Alto de píxel", "number", true)] },
  edi: { en: "EDI transfer functions", es: "Funciones de transferencia EDI", extensions: [".edi"], mimes: ["text/plain", "application/octet-stream"], maxMiB: 5, units: ["ohm", "mV/km/nT"], frames: ["geographic ENU", "instrument axes"], geometry: [field("station_id", "Station ID", "ID de estación"), field("frequency_count", "Frequency count", "Cantidad de frecuencias", "integer", true), field("tensor_components", "Tensor components (comma-separated)", "Componentes del tensor (separados por coma)", "list"), field("rotation_degrees", "Rotation (degrees)", "Rotación (grados)", "number"), field("rotation_reference", "Rotation reference (MT processing: unspecified or geographic-north)", "Referencia de rotación (procesamiento MT: unspecified o geographic-north)", "text", false, true), field("sign_convention", "Time sign (MT processing: + or −)", "Signo temporal (procesamiento MT: + o −)", "text", false, true), field("variance_convention", "Variance convention (MT processing: complex or per-real-component)", "Convención de varianza (procesamiento MT: complex o per-real-component)", "text", false, true)] },
  miniseed: { en: "MiniSEED waveform", es: "Forma de onda MiniSEED", extensions: [".mseed", ".msd"], mimes: ["application/vnd.fdsn.mseed", "application/octet-stream"], maxMiB: 200, units: ["counts", "m/s", "m/s2"], frames: ["channel azimuth/dip"], geometry: [field("network", "Network", "Red"), field("station", "Station", "Estación"), channels, field("sample_rate_hz", "Sample rate (Hz)", "Frecuencia de muestreo (Hz)", "number", true), field("start_utc", "Start UTC (ISO 8601)", "Inicio UTC (ISO 8601)"), field("end_utc", "End UTC (ISO 8601)", "Fin UTC (ISO 8601)"), field("stationxml_asset_id", "Companion StationXML asset", "Activo StationXML asociado", "stationxml")] },
  stationxml: { en: "StationXML response", es: "Respuesta StationXML", extensions: [".xml"], mimes: ["application/xml", "text/xml"], maxMiB: 20, units: ["counts", "m/s", "m/s2"], frames: ["channel azimuth/dip"], geometry: [field("network", "Network", "Red"), field("station", "Station", "Estación"), channels, field("response_epoch_utc", "Response epoch UTC (ISO 8601)", "Época de respuesta UTC (ISO 8601)")] },
  segy: { en: "SEG-Y traces", es: "Trazas SEG-Y", extensions: [".sgy", ".segy"], mimes: ["application/x-segy", "application/octet-stream"], maxMiB: 200, units: ["counts", "Pa", "m/s"], frames: ["source-receiver"], geometry: [field("source_count", "Source count", "Cantidad de fuentes", "integer", true), field("receiver_count", "Receiver count", "Cantidad de receptores", "integer", true), field("sample_interval_us", "Sample interval (µs)", "Intervalo de muestra (µs)", "integer", true), field("samples_per_trace", "Samples per trace", "Muestras por traza", "integer", true), field("coordinate_scalar", "Coordinate scalar (nonzero integer)", "Factor de coordenadas (entero no nulo)", "integer")] },
  mth5: { en: "MTH5 run", es: "Registro MTH5", extensions: [".h5"], mimes: ["application/x-hdf5", "application/octet-stream"], maxMiB: 200, units: ["counts", "mV/km", "nT"], frames: ["channel azimuth/dip"], geometry: [field("survey_id", "Survey ID", "ID de levantamiento"), field("station_id", "Station ID", "ID de estación"), field("run_id", "Run ID", "ID de registro"), channels, field("start_utc", "Start UTC (ISO 8601)", "Inicio UTC (ISO 8601)"), field("end_utc", "End UTC (ISO 8601)", "Fin UTC (ISO 8601)")] },
} satisfies Record<string, FormatSpec>;

export type RawFormat = keyof typeof FORMAT_SPECS;
export type UploadDraft = {
  format: RawFormat | ""; mime: string; provider: string; doi: string; citation: string;
  rightsStatement: string; rightsDecision: "mirror" | "provider-link-only" | "derivative-only" | "";
  privateStorageAttested: boolean; attribution: string;
  coordinateReference: "epsg" | "local" | ""; epsg: string; localCrs: string;
  axisOrder: "xy" | "yx" | "lon_lat" | "lat_lon" | "";
  horizontalDatum: string; verticalDatum: string; verticalPositive: "up" | "down" | "";
  horizontalUnit: "m" | "km" | "degree" | ""; verticalUnit: "m" | "ft" | "";
  measurementUnit: string; epochUtc: string; componentFrame: string;
  geometry: Record<string, string>;
  orientation: Record<string, { azimuth: string; dip: string }>;
};

export const emptyUploadDraft = (): UploadDraft => ({
  format: "", mime: "", provider: "", doi: "", citation: "", rightsStatement: "", rightsDecision: "",
  privateStorageAttested: false, attribution: "", coordinateReference: "", epsg: "", localCrs: "",
  axisOrder: "", horizontalDatum: "", verticalDatum: "", verticalPositive: "", horizontalUnit: "",
  verticalUnit: "", measurementUnit: "", epochUtc: "", componentFrame: "", geometry: {}, orientation: {},
});

export class UploadMetadataError extends Error {
  constructor(public readonly fields: string[]) { super(`Complete or correct: ${fields.join(", ")}`); }
}

const isoUtc = (value: string) => /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value) && !Number.isNaN(Date.parse(value));
const nonempty = (value: string) => value.trim().length > 0;

/** Client-side declaration checks are guidance; the API is the scientific envelope authority. */
export function prepareUpload(file: File | null, draft: UploadDraft, stationxmlAssets: readonly string[]): Omit<RawUploadDeclaration, "filename" | "source"> & { source: Omit<RawUploadDeclaration["source"], "expected_bytes" | "expected_sha256"> } {
  const errors: string[] = [];
  const required = (condition: boolean, path: string) => { if (!condition) errors.push(path); };
  required(!!file && file.size > 0, "file");
  required(!!draft.format, "format");
  const spec = draft.format ? FORMAT_SPECS[draft.format] : null;
  if (spec && file) {
    required(spec.extensions.some(extension => file.name.toLowerCase().endsWith(extension)), "filename/format");
    required(file.size <= spec.maxMiB * 1024 * 1024, `file limit ${spec.maxMiB} MiB`);
    required(spec.mimes.includes(draft.mime), "MIME");
  }
  required(nonempty(draft.provider), "source.provider");
  required(draft.rightsStatement.trim().length >= 10, "source.rights_statement");
  required(!!draft.rightsDecision, "source.rights_decision");
  required(draft.privateStorageAttested, "source.private_storage_permission");
  required(nonempty(draft.attribution), "source.attribution");
  required(!!draft.coordinateReference, "physical.coordinate_reference");
  required(!!draft.axisOrder, "physical.axis_order");
  required(draft.horizontalDatum.trim().length >= 2, "physical.horizontal_datum");
  required(draft.verticalDatum.trim().length >= 2, "physical.vertical_datum");
  required(!!draft.verticalPositive, "physical.vertical_positive");
  required(!!draft.horizontalUnit, "physical.horizontal_unit");
  required(!!draft.verticalUnit, "physical.vertical_unit");
  required(isoUtc(draft.epochUtc), "physical.epoch_utc");
  required(!!spec && spec.units.includes(draft.measurementUnit), "physical.measurement_unit");
  required(!!spec && spec.frames.includes(draft.componentFrame), "physical.component_frame");
  if (draft.coordinateReference === "epsg") {
    required(/^\d+$/.test(draft.epsg) && +draft.epsg >= 1000 && +draft.epsg <= 999999, "physical.epsg");
  } else if (draft.coordinateReference === "local") {
    required(draft.localCrs.trim().length >= 5, "physical.local_crs");
    required(draft.horizontalUnit !== "degree", "physical.horizontal_unit");
  }
  const geometry: RawUploadDeclaration["physical"]["geometry"] = {};
  for (const geometryField of spec?.geometry ?? []) {
    const value = (draft.geometry[geometryField.key] ?? "").trim();
    const path = `physical.geometry.${geometryField.key}`;
    if (!value) { if (!geometryField.optional) errors.push(path); continue; }
    if (geometryField.kind === "stationxml") {
      required(stationxmlAssets.includes(value), path);
      geometry[geometryField.key] = value;
    } else if (geometryField.kind === "list") {
      const items = value.split(",").map(item => item.trim()).filter(Boolean);
      required(items.length > 0 && new Set(items).size === items.length, path);
      geometry[geometryField.key] = items;
    } else if (geometryField.kind === "integer" || geometryField.kind === "number") {
      const number = Number(value);
      required(Number.isFinite(number) && (geometryField.kind !== "integer" || Number.isInteger(number)) && (!geometryField.positive || number > 0) && (geometryField.key !== "coordinate_scalar" || number !== 0), path);
      geometry[geometryField.key] = number;
    } else {
      geometry[geometryField.key] = value;
    }
  }
  if (draft.format === "edi") {
    const components = geometry.tensor_components;
    required(Array.isArray(components) && ["Zxx", "Zxy", "Zyx", "Zyy"].every(component => components.includes(component)) && components.every(component => ["Zxx", "Zxy", "Zyx", "Zyy", "Tx", "Ty"].includes(component)), "physical.geometry.tensor_components");
    required(typeof geometry.rotation_degrees === "number" && geometry.rotation_degrees >= -360 && geometry.rotation_degrees <= 360, "physical.geometry.rotation_degrees");
    if (geometry.sign_convention !== undefined) required(["+", "-"].includes(String(geometry.sign_convention)), "physical.geometry.sign_convention");
    if (geometry.variance_convention !== undefined) required(["complex", "per-real-component"].includes(String(geometry.variance_convention)), "physical.geometry.variance_convention");
    if (geometry.rotation_reference !== undefined) required(["unspecified", "geographic-north"].includes(String(geometry.rotation_reference)), "physical.geometry.rotation_reference");
  }
  if (draft.format === "miniseed" || draft.format === "stationxml" || draft.format === "mth5") {
    const orientations: Record<string, [number, number]> = {};
    const values = geometry.channels;
    if (Array.isArray(values)) for (const channel of values) {
      const pair = draft.orientation[channel];
      const azimuth = pair?.azimuth === "" || pair?.azimuth === undefined ? NaN : Number(pair.azimuth);
      const dip = pair?.dip === "" || pair?.dip === undefined ? NaN : Number(pair.dip);
      required(Number.isFinite(azimuth) && azimuth >= 0 && azimuth < 360 && Number.isFinite(dip) && dip >= -90 && dip <= 90, `physical.geometry.channel_orientation_deg.${channel}`);
      orientations[channel] = [azimuth, dip];
    }
    geometry.channel_orientation_deg = orientations;
  }
  if (draft.format === "miniseed" || draft.format === "mth5") {
    const start = geometry.start_utc;
    const end = geometry.end_utc;
    required(typeof start === "string" && isoUtc(start), "physical.geometry.start_utc");
    required(typeof end === "string" && isoUtc(end) && typeof start === "string" && isoUtc(start) && Date.parse(start) < Date.parse(end), "physical.geometry.end_utc");
  }
  if (draft.format === "stationxml") required(typeof geometry.response_epoch_utc === "string" && isoUtc(geometry.response_epoch_utc), "physical.geometry.response_epoch_utc");
  if (errors.length) throw new UploadMetadataError([...new Set(errors)]);
  return {
    mime: draft.mime,
    format: draft.format as RawFormat,
    source: {
      provider: draft.provider.trim(), doi: draft.doi.trim() || null, citation: draft.citation.trim() || null,
      rights_statement: draft.rightsStatement.trim(), rights_decision: draft.rightsDecision as "mirror" | "provider-link-only" | "derivative-only",
      private_storage_permission: "attested", attribution: draft.attribution.trim(),
    },
    physical: {
      coordinate_reference: draft.coordinateReference as "epsg" | "local",
      epsg: draft.coordinateReference === "epsg" ? +draft.epsg : null,
      local_crs: draft.coordinateReference === "local" ? draft.localCrs.trim() : null,
      axis_order: draft.axisOrder as "xy" | "yx" | "lon_lat" | "lat_lon",
      horizontal_datum: draft.horizontalDatum.trim(), vertical_datum: draft.verticalDatum.trim(),
      vertical_positive: draft.verticalPositive as "up" | "down",
      horizontal_unit: draft.horizontalUnit as "m" | "km" | "degree", vertical_unit: draft.verticalUnit as "m" | "ft",
      measurement_unit: draft.measurementUnit, epoch_utc: draft.epochUtc, component_frame: draft.componentFrame,
      geometry,
    },
  };
}
