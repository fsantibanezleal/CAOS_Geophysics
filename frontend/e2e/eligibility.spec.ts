import { test, expect, type APIRequestContext, type BrowserContext, type Page } from "@playwright/test";

const origin = "http://127.0.0.1:8877";
const email = "eligibility-owner@example.org";
const password = "a separate long R-005 QA password";
const bytes = Buffer.from("station,x,y,z,g,sigma\nS1,500000,6200000,100,1,0.1\nS2,500010,6200010,100,2,0.1\nS3,500020,6200000,100,3,0.1\nS4,500030,6200010,100,4,0.1\nS5,500040,6200000,100,100,0.1\n");
const magneticBytes = Buffer.from([
  "E,N,TMI_nT,line,role,height_m,sample",
  ...Array.from({ length: 5 }, (_, line) => Array.from({ length: 8 }, (_, sample) =>
    `${500000 + sample * 10},${100000 + line * 100},${20 + line + sample / 10},F${line},flight,100,${sample}`,
  )).flat(),
  "",
].join("\n"));
const ertBytes = Buffer.from([
  "# Wenner array with 2m",
  "8# Number of sensors",
  "#x z",
  ...Array.from({ length: 8 }, (_, index) => `${2 * index} 0`),
  "5# Number of data",
  "#a b m n R",
  ...Array.from({ length: 5 }, (_, index) => `${index + 1} ${index + 4} ${index + 2} ${index + 3} 1`),
  "",
].join("\n"));
let context: BrowserContext;
let page: Page;
let projectId = "";
let datasetId = "";

async function post(request: APIRequestContext, path: string, data?: unknown, form?: Record<string, string>) {
  const csrf = await (await request.get(`${origin}/api/auth/csrf`)).json();
  return request.post(`${origin}${path}`, {
    headers: { Origin: origin, "X-CSRF-Token": csrf.csrf_token },
    ...(form ? { form } : data === undefined ? {} : { data }),
  });
}

test.beforeAll(async ({ browser }) => {
  context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  page = await context.newPage();
  expect((await context.request.get(`${origin}/__qa/processing`)).ok()).toBe(true);
  expect((await post(context.request, "/api/auth/register", { email, password })).status()).toBe(201);
  const { token } = await (await context.request.get(`${origin}/__qa/mail/latest`)).json();
  expect((await post(context.request, "/api/auth/verify/verify", { token })).ok()).toBe(true);
  expect((await post(context.request, "/api/auth/cookie/login", undefined, { username: email, password })).ok()).toBe(true);

  const project = await post(context.request, "/api/projects", { name: "R-005 eligibility QA", description: "Contract QA input, not a scientific case" });
  expect(project.status(), await project.text()).toBe(201);
  projectId = (await project.json()).id;
  const metadata = {
    filename: "r005-owned-stations.csv", mime: "text/csv", format: "gravity_csv",
    source: { provider: "QA owner supplied input", rights_statement: "Private R-005 test input",
      rights_decision: "provider-link-only", private_storage_permission: "attested", attribution: "QA input",
      expected_bytes: bytes.length, expected_sha256: await cryptoHash(bytes) },
    physical: { coordinate_reference: "epsg", epsg: 32719, axis_order: "xy", horizontal_datum: "WGS84",
      vertical_datum: "survey benchmark", vertical_positive: "up", horizontal_unit: "m", vertical_unit: "m",
      measurement_unit: "mGal", epoch_utc: "2026-10-28T12:00:00Z", component_frame: "local vertical down",
      geometry: { station_id_column: "station", x_column: "x", y_column: "y", z_column: "z",
        value_column: "g", sigma_column: "sigma" } },
  };
  const uploadCsrf = await (await context.request.get(`${origin}/api/auth/csrf`)).json();
  const asset = await context.request.post(`${origin}/api/projects/${projectId}/assets`, {
    headers: { Origin: origin, "X-CSRF-Token": uploadCsrf.csrf_token,
      "Content-Type": "text/csv", "X-Asset-Metadata": JSON.stringify(metadata) }, data: bytes,
  });
  expect(asset.status(), await asset.text()).toBe(201);
  const dataset = await post(context.request, `/api/projects/${projectId}/datasets`, { asset_id: (await asset.json()).asset_id });
  expect(dataset.status(), await dataset.text()).toBe(201);
  datasetId = (await dataset.json()).dataset_id;
});

test.afterAll(async () => { await context?.close(); });

async function cryptoHash(value: Buffer) {
  const { createHash } = await import("node:crypto");
  return createHash("sha256").update(value).digest("hex");
}

test("eligible method only is submittable; offline and incompatible methods show field paths", async () => {
  const endpoint = `${origin}/api/projects/${projectId}/datasets/${datasetId}/methods`;
  const response = await context.request.get(endpoint);
  expect(response.ok()).toBe(true);
  const verdict = await response.json();
  expect(verdict.methods.map((item: { method_id: string }) => item.method_id)).toEqual(["gravity.station-outlier-flags/v1"]);
  const byId = new Map(verdict.unavailable.map((item: { method_id: string }) => [item.method_id, item]));
  expect((byId.get("M05") as { lane: string }).lane).toBe("incompatible_input");
  expect((byId.get("gravity.survey-l2-ordinary/v1") as { reason_fields: string[] }).reason_fields)
    .toContain("physical_metadata.geometry.ordinary_l2");

  await page.goto(`${origin}/?project=${projectId}`);
  await expect(page.getByTestId("processing-instrument")).toBeVisible();
  await page.getByRole("combobox", { name: "Control section", exact: true }).selectOption("run");
  const method = page.getByRole("combobox", { name: "API method verdict", exact: true });
  await method.selectOption("gravity.survey-l2-ordinary/v1");
  await expect(page.getByTestId("method-eligibility")).toContainText("physical_metadata.geometry.ordinary_l2");
  await expect(page.getByRole("button", { name: "Submit ordinary-L2 job", exact: true })).toBeDisabled();
  await method.selectOption("M05");
  await expect(page.getByTestId("method-eligibility")).toContainText("dataset.modality");
  await expect(page.getByRole("button", { name: "Submit flag QC job", exact: true })).toBeDisabled();

  await page.evaluate(() => localStorage.setItem("caos.lang", "es"));
  await page.reload();
  await expect(page.getByTestId("processing-instrument")).toBeVisible();
  await page.getByRole("combobox", { name: "Sección de controles", exact: true }).selectOption("run");
  await page.getByRole("combobox", { name: "Veredicto de método de la API", exact: true }).selectOption("gravity.survey-l2-ordinary/v1");
  await expect(page.getByTestId("method-eligibility")).toContainText("Campos que debe revisar");
  await expect(page.getByTestId("method-eligibility")).toContainText("physical_metadata.geometry.ordinary_l2");
});

test("owned magnetic survey shows source eligibility and refuses pending VPS admission", async () => {
  const magneticMetadata = {
    filename: "r005-magnetic-flight-lines.csv", mime: "text/csv", format: "magnetic_csv",
    source: { provider: "Authored R-005 QA input", citation: "Synthetic eligibility control; not field data.",
      rights_statement: "Private test fixture authored for this test.", rights_decision: "mirror",
      private_storage_permission: "attested", attribution: "R-005 browser test",
      expected_bytes: magneticBytes.length, expected_sha256: await cryptoHash(magneticBytes) },
    physical: { coordinate_reference: "epsg", epsg: 32719, axis_order: "xy", horizontal_datum: "WGS84",
      vertical_datum: "survey reference", vertical_positive: "up", horizontal_unit: "m", vertical_unit: "m",
      measurement_unit: "nT", epoch_utc: "2026-10-28T12:00:00Z", component_frame: "total field",
      geometry: { line_id_column: "line", x_column: "E", y_column: "N", z_column: "height_m",
        value_column: "TMI_nT" } },
  };
  const uploadCsrf = await (await context.request.get(`${origin}/api/auth/csrf`)).json();
  const asset = await context.request.post(`${origin}/api/projects/${projectId}/assets`, {
    headers: { Origin: origin, "X-CSRF-Token": uploadCsrf.csrf_token,
      "Content-Type": "text/csv", "X-Asset-Metadata": JSON.stringify(magneticMetadata) }, data: magneticBytes,
  });
  expect(asset.status(), await asset.text()).toBe(201);
  const assetReceipt = await asset.json();

  await page.evaluate(() => localStorage.setItem("caos.lang", "en"));
  await page.goto(`${origin}/?project=${projectId}&instrument=magnetic-flightline`);
  await expect(page.getByTestId("m03-eligibility")).toHaveCount(0);
  await page.getByRole("combobox", { name: "Stored magnetic CSV", exact: true }).selectOption(assetReceipt.asset_id);
  for (const [label, value] of [
    ["easting *", "E"], ["northing *", "N"], ["value *", "TMI_nT"], ["line id *", "line"],
    ["line role *", "role"], ["sensor height m *", "height_m"], ["sample order *", "sample"],
  ]) await page.getByLabel(label, { exact: true }).fill(value);
  await page.getByLabel("Provider processing already applied", { exact: true }).fill("Synthetic total-field anomaly; no corrections applied.");
  await page.getByLabel("Magnetic quantity", { exact: true }).fill("total-field anomaly [nT]");
  await page.getByRole("button", { name: "Validate mapped dataset", exact: true }).click();

  const eligibility = page.getByTestId("m03-eligibility");
  await expect(eligibility).toContainText("M03 unavailable");
  await expect(eligibility).toContainText("host.magnetic_online_admission");
  await expect(page.getByRole("heading", { name: "Online M03 execution is pending host admission" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Run M03 line QC and grid", exact: true })).toHaveCount(0);
  await expect(page.getByText("Dataset receipt", { exact: true })).toBeVisible();
});

test("owned ERT profile parses with rights and exposes the closed VPS method gate", async () => {
  const ertMetadata = {
    filename: "r005-owned-profile.ohm", mime: "text/plain", format: "ert_ohm",
    source: { provider: "Authored R-005 QA input", citation: "Synthetic ERT eligibility control; not field data.",
      rights_statement: "Private test fixture authored for this test.", rights_decision: "derivative-only",
      private_storage_permission: "attested", attribution: "R-005 browser test",
      expected_bytes: ertBytes.length, expected_sha256: await cryptoHash(ertBytes) },
    physical: { coordinate_reference: "local", local_crs: "Declared baseline", axis_order: "xy",
      horizontal_datum: "Declared datum", vertical_datum: "Declared datum", vertical_positive: "up",
      horizontal_unit: "m", vertical_unit: "m", measurement_unit: "ohm", epoch_utc: "2026-10-28T12:00:00Z",
      component_frame: "ABMN", geometry: { electrode_count: 8, measurement_count: 5 } },
  };
  const uploadCsrf = await (await context.request.get(`${origin}/api/auth/csrf`)).json();
  const upload = await context.request.post(`${origin}/api/projects/${projectId}/assets`, {
    headers: { Origin: origin, "X-CSRF-Token": uploadCsrf.csrf_token,
      "Content-Type": "text/plain", "X-Asset-Metadata": JSON.stringify(ertMetadata) }, data: ertBytes,
  });
  expect(upload.status(), await upload.text()).toBe(201);
  const assetReceipt = await upload.json();

  await page.goto(`${origin}/?project=${projectId}&instrument=profiles`);
  await page.getByRole("combobox", { name: "Project method", exact: true }).selectOption("profiles");
  await page.getByText("Processing controls", { exact: true }).click();
  await page.getByRole("combobox", { name: "Stored original", exact: true }).selectOption(assetReceipt.asset_id);
  await page.getByText("Dataset citation and processing permission", { exact: true }).click();
  await page.getByLabel("Source citation for this profile", { exact: true }).fill("Declared own survey; authored R-005 test.");
  await page.getByLabel("Declared rights holder", { exact: true }).fill("R-005 test owner");
  await page.getByLabel("I have permission to process this original", { exact: true }).check();
  await page.getByRole("button", { name: "Parse original profile", exact: true }).click();

  await expect(page.getByText("host.profile_online_admission", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Run native profile inversion on VPS", exact: true })).toBeDisabled();
  await expect(page.getByRole("combobox", { name: "Parsed dataset", exact: true })).toContainText("r005-owned-profile.ohm");
});
