import { describe, expect, it } from "vitest";
import { FORMAT_SPECS, UploadMetadataError, emptyUploadDraft, prepareUpload, type UploadDraft } from "../api/upload-metadata";

const original = new File(["station,x,y,z,g\nS1,0,0,100,9.81\nS2,10,0,100,9.80\n"], "stations.csv", { type: "text/csv" });
const gravity = (): UploadDraft => ({
  ...emptyUploadDraft(), format: "gravity_csv", mime: "text/csv", provider: "Survey owner",
  rightsStatement: "I may store this original privately.", rightsDecision: "provider-link-only",
  privateStorageAttested: true, attribution: "Survey owner", coordinateReference: "epsg", epsg: "32719",
  axisOrder: "xy", horizontalDatum: "WGS84", verticalDatum: "survey benchmark", verticalPositive: "up",
  horizontalUnit: "m", verticalUnit: "m", measurementUnit: "mGal", epochUtc: "2026-09-27T12:00:00Z",
  componentFrame: "local vertical down", geometry: { station_id_column: "station", x_column: "x", y_column: "y", z_column: "z", value_column: "g" },
});

describe("explicit scientific raw-upload declaration", () => {
  it("covers precisely the API envelope formats and produces no invented QC verdict", () => {
    expect(Object.keys(FORMAT_SPECS)).toEqual(["gravity_csv", "magnetic_csv", "traveltime_csv", "ert_csv", "geotiff", "edi", "miniseed", "stationxml", "segy", "mth5"]);
    const declaration = prepareUpload(original, gravity(), []);
    expect(declaration.source).toMatchObject({ rights_decision: "provider-link-only", private_storage_permission: "attested", citation: null });
    expect(declaration.physical).toMatchObject({ epsg: 32719, measurement_unit: "mGal", geometry: { station_id_column: "station" } });
    expect(JSON.stringify(declaration)).not.toMatch(/storage_key|validation_status|dataset_id/);
  });

  it("rejects missing rights, unit, CRS and geometry instead of guessing", () => {
    const draft = gravity();
    draft.privateStorageAttested = false;
    draft.horizontalDatum = "";
    draft.measurementUnit = "counts";
    draft.geometry.value_column = "";
    try { prepareUpload(original, draft, []); throw new Error("not rejected"); }
    catch (error) {
      expect(error).toBeInstanceOf(UploadMetadataError);
      expect((error as UploadMetadataError).fields).toEqual(expect.arrayContaining(["source.private_storage_permission", "physical.horizontal_datum", "physical.measurement_unit", "physical.geometry.value_column"]));
    }
  });

  it("requires waveform companion and per-channel azimuth/dip", () => {
    const draft = { ...gravity(), format: "miniseed" as const, mime: "application/vnd.fdsn.mseed", measurementUnit: "counts", componentFrame: "channel azimuth/dip", geometry: { network: "CL", station: "STA", channels: "BHZ,BHN", sample_rate_hz: "100", start_utc: "2026-09-27T12:00:00Z", end_utc: "2026-09-27T12:10:00Z", stationxml_asset_id: "11111111-1111-4111-8111-111111111111" }, orientation: { BHZ: { azimuth: "0", dip: "-90" }, BHN: { azimuth: "0", dip: "0" } } };
    const file = new File([new Uint8Array(256)], "trace.mseed", { type: draft.mime });
    expect(() => prepareUpload(file, draft, [])).toThrow("stationxml_asset_id");
    const declaration = prepareUpload(file, draft, [draft.geometry.stationxml_asset_id]);
    expect(declaration.physical.geometry.channel_orientation_deg).toEqual({ BHZ: [0, -90], BHN: [0, 0] });
  });
});
