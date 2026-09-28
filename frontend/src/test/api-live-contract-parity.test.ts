import { describe, expect, it } from "vitest";
import fixture from "./fixtures/api-owner-raw-v1.json";
import { parseRawAsset, parseSourceRecord } from "../api/contracts";

const clone = <T>(value: T): T => structuredClone(value);

describe("INT-API-FE-01 versioned API owner-view parity", () => {
  it("accepts the API fixture without private storage keys or false scientific validity", () => {
    const asset = parseRawAsset(fixture);
    expect(asset.schema_version).toBe("geophysics.raw-asset-view/v1");
    expect(asset.source.citation).toBeNull();
    expect(asset.source.private_storage_permission).toBe("attested");
    expect(asset.validation_status).toBe("raw_metadata_checked");
    expect(asset.download_url).toBe(`${asset.receipt}/download`);
    expect(JSON.stringify(asset)).not.toMatch(/storage_key|private.*path/i);
  });

  it("fails closed on an internal key, changed version, invented QC, or mismatched owner path", () => {
    expect(() => parseRawAsset({ ...clone(fixture), storage_key: "private/path" })).toThrow("unexpected field storage_key");
    expect(() => parseRawAsset({ ...clone(fixture), schema_version: "geophysics.raw-asset-view/v2" })).toThrow("schema_version");
    expect(() => parseRawAsset({ ...clone(fixture), validation_status: "valid" })).toThrow("validation_status");
    expect(() => parseRawAsset({ ...clone(fixture), download_url: "/api/projects/other/assets/private/download" })).toThrow("download_url");
    expect(() => parseSourceRecord({ ...clone(fixture.source), location: { kind: "url", url: "https://example.org" } })).toThrow("location");
  });
});
