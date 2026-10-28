import { test, expect, type APIRequestContext, type BrowserContext, type Page } from "@playwright/test";

const origin = "http://127.0.0.1:8877";
const email = "eligibility-owner@example.org";
const password = "a separate long R-005 QA password";
const bytes = Buffer.from("station,x,y,z,g,sigma\nS1,500000,6200000,100,1,0.1\nS2,500010,6200010,100,2,0.1\nS3,500020,6200000,100,3,0.1\nS4,500030,6200010,100,4,0.1\nS5,500040,6200000,100,100,0.1\n");
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
  await expect(page.getByRole("button", { name: "Submit flag QC job", exact: true })).toBeDisabled();
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
