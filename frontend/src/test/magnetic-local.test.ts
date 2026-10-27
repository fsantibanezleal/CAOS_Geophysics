import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { AddressInfo } from "node:net";
import { fileURLToPath } from "node:url";
import { chromium, type Browser, type Page } from "@playwright/test";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createServer, type ViteDevServer } from "vite";
import { M03_LOCAL_LIMITS } from "../api/magnetic-local";

const repo = resolve(fileURLToPath(new URL("../../../", import.meta.url)));
const frontend = join(repo, "frontend");
const pythonCandidates = [
  process.env.M03_PYTHON,
  join(repo, ".venv-pipeline", "Scripts", "python.exe"),
  join(repo, ".venv-pipeline", "bin", "python"),
  "python",
].filter((value): value is string => Boolean(value));

const source = {
  source_id: "controlled-plane",
  citation: "Authored analytic controls",
  rights_decision: "local-test-only",
  processing_state: "synthetic total-field anomaly",
  value_unit: "nT",
  value_quantity: "total-field anomaly",
  sensor_height_reference: "above-ground",
};
const frame = { crs: "local projected metric control", coordinates_are_projected: true as const, linear_unit: "m" as const };
const mapping = {
  easting: "E", northing: "N", value: "field", line_id: "line", line_role: "role",
  sensor_height_m: "height", sample_order: "index",
};
const settings = { grid_spacing_m: 12.5, holdout_fraction: 0.2, seed: "M03-control-v1" };
const options = { source, frame, mapping, settings };

function fixtureCsv(): string {
  const rows = ["E,N,field,line,role,height,index"];
  for (let line = 0; line < 5; line++) {
    const x = line * 100;
    for (let sample = 0; sample < 9; sample++) {
      const y = line * 5 + sample * 12.5;
      const height = 120 + 0.02 * y + (line === 2 && sample === 3 ? 15 : 0);
      rows.push([x, y, 50_000 + 0.3 * x - 0.15 * y, `F${line}`, "flight", height, sample].join(","));
    }
  }
  for (let sample = 0; sample < 9; sample++) {
    const x = sample * 50;
    rows.push([x, 50, 50_000 + 0.3 * x - 0.15 * 50 + 7, "T0", "tie", 120, sample].join(","));
  }
  return `${rows.join("\n")}\n`;
}

function pythonOracle(csv: string): Record<string, any> {
  const temporary = mkdtempSync(join(tmpdir(), "m03-pyodide-parity-"));
  const csvPath = join(temporary, "flightline.csv");
  const configPath = join(temporary, "config.json");
  const resultPath = join(temporary, "result.json");
  writeFileSync(csvPath, csv, "utf8");
  writeFileSync(configPath, JSON.stringify({ source, frame, mapping, settings }), "utf8");
  let lastError: unknown;
  try {
    for (const python of pythonCandidates) {
      if (python !== "python" && !existsSync(python)) continue;
      try {
        execFileSync(python, [join(repo, "data-pipeline", "magnetic_processing.py"), "--csv", csvPath,
          "--config", configPath, "--output", resultPath], { cwd: repo, stdio: "pipe", timeout: 60_000 });
        return JSON.parse(readFileSync(resultPath, "utf8"));
      } catch (error) {
        lastError = error;
      }
    }
    throw new Error(`Could not run the native Python M03 oracle. Set M03_PYTHON to an interpreter with the pinned NumPy/SciPy dependencies. ${String(lastError)}`);
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
}

let server: ViteDevServer;
let browser: Browser;
let page: Page;
let origin: string;
let expected: Record<string, any>;
const csv = fixtureCsv();

describe("M03 browser-local Python/SciPy parity", () => {
  beforeAll(async () => {
    expected = pythonOracle(csv);
    server = await createServer({
      configFile: join(frontend, "vite.config.ts"),
      root: frontend,
      logLevel: "error",
      server: { host: "127.0.0.1", port: 0, strictPort: false, hmr: false },
    });
    await server.listen();
    const address = server.httpServer?.address();
    if (!address || typeof address === "string") throw new Error("Vite test server did not bind a TCP port.");
    origin = `http://127.0.0.1:${(address as AddressInfo).port}`;
    browser = await chromium.launch({ headless: true });
    page = await browser.newPage();
    await page.goto(origin);
  }, 180_000);

  afterAll(async () => {
    await browser?.close();
    await server?.close();
  }, 60_000);

  it("uses the canonical Python source in a worker and matches the SciPy fixture result", async () => {
    await page.addScriptTag({
      type: "module",
      content: `import { runMagneticLocal } from "/src/api/magnetic-local.ts";
        window.__m03RunFn = runMagneticLocal;
        window.__m03Progress = [];
        window.__m03RunPromise = runMagneticLocal(
          new File([${JSON.stringify(csv)}], "controlled-flightline.csv", {type:"text/csv"}),
          ${JSON.stringify(options)},
          {onProgress:item=>window.__m03Progress.push(item.stage)}
        );`,
    });
    await page.waitForFunction(() => "__m03RunPromise" in window, undefined, { timeout: 10_000 });
    const actual = await page.evaluate(async () => ({
      run: await (window as any).__m03RunPromise,
      progress: (window as any).__m03Progress as string[],
    }));

    const { result, execution } = actual.run;
    expect(execution.lane).toBe("browser-local-pyodide");
    expect(execution.pyodide_version).toBe("0.29.5");
    expect(execution.python_version).toBe("3.13.2");
    expect(execution.numpy_version).toBe("2.2.5");
    expect(execution.scipy_version).toBe("1.14.1");
    expect(execution.python_pipeline_sha256).toBe(createHash("sha256").update(readFileSync(join(repo, "data-pipeline", "magnetic_processing.py"))).digest("hex"));
    expect(execution.original_csv_sha256).toBe(expected.source.sha256);
    expect(execution.original_csv_bytes).toBe(new TextEncoder().encode(csv).byteLength);
    expect(actual.progress).toEqual(["loading-runtime", "loading-scientific-packages", "processing"]);

    // Result contract and every numerical/display array are compared against
    // magnetic_processing.py executed natively on the same exact CSV bytes.
    expect(Object.keys(result).sort()).toEqual(Object.keys(expected).sort());
    expect(Object.keys(result.grid).sort()).toEqual(Object.keys(expected.grid).sort());
    expect(result.schema).toBe(expected.schema);
    expect(result.source).toEqual(expected.source);
    expect(result.configuration).toEqual(expected.configuration);
    expect(result.claims).toEqual(expected.claims);
    expect(result.limitations).toEqual(expected.limitations);
    expect(result.split).toEqual(expected.split);
    expect(result.grid.shape_yx).toEqual(expected.grid.shape_yx);
    expect(result.grid.x_easting_m).toEqual(expected.grid.x_easting_m);
    expect(result.grid.y_northing_m).toEqual(expected.grid.y_northing_m);
    expect(result.grid.support_mask).toEqual(expected.grid.support_mask);
    expect(result.grid.unsupported_value_encoding).toBe(expected.grid.unsupported_value_encoding);
    expect(result.geometry_qc).toEqual(expected.geometry_qc);
    expect(result.heldout_interpolation).toEqual(expected.heldout_interpolation);
    // This controlled plane fixture attains bit-for-bit equality on every
    // grid value, so no numeric tolerance is silently introduced here.
    expect(result.grid.values).toEqual(expected.grid.values);
    expect(result.configuration.value_unit).toBe("nT");
    expect(result.geometry_qc.lines.find((line: any) => line.line_id === "F2").sensor_height_m.qc_outlier_rows).toEqual([3]);
    expect(result.geometry_qc.crossover_interpolation_qc.mean_signed_difference).toBe(-7);
    expect(result.split.holdout_line_ids).toEqual(["F1"]);
    expect(result.grid.support_mask.flat().some((supported: boolean) => !supported)).toBe(true);
    expect(result.grid.support_mask[0][0]).toBe(true);
    expect(result.grid.support_mask[0][expected.grid.shape_yx[1] - 1]).toBe(false);
    expect(result.grid.support_mask[expected.grid.shape_yx[0] - 1][0]).toBe(false);
    expect(result.grid.support_mask[expected.grid.shape_yx[0] - 1][expected.grid.shape_yx[1] - 1]).toBe(true);
    result.grid.values.flat().forEach((value: number, index: number) => {
      if (!result.grid.support_mask.flat()[index]) expect(value).toBe(0);
    });

    const overLimitCsv = `E,N,field,line,role,height,index\n${"0,0,50000,F0,flight,100,0\n".repeat(M03_LOCAL_LIMITS.rows + 1)}`;
    const capCheck = await page.evaluate(async ({ csvText, options }) => {
      const progress: string[] = [];
      try {
        await ((window as any).__m03RunFn as (file: File, input: unknown, hooks: unknown) => Promise<unknown>)(
          new File([csvText], "over-limit.csv", {type:"text/csv"}), options,
          {onProgress:(item:{stage:string})=>progress.push(item.stage)},
        );
        return {message:"unexpected success",progress};
      } catch (error) {
        return {message:error instanceof Error?error.message:String(error),progress};
      }
    }, { csvText: overLimitCsv, options });
    expect(capCheck.message).toContain("25,000 CSV observations");
    expect(capCheck.progress).toEqual([]); // Refused before loading Pyodide/SciPy.

    const capCsvRows = ["E,N,field,line,role,height,index"];
    for (let line = 0; line < 5; line++) {
      const count = line === 2 ? M03_LOCAL_LIMITS.rows - 12 : 3;
      for (let sample = 0; sample < count; sample++) {
        const y = line === 2 ? sample * 100 / (count - 1) : 40 + sample * 10;
        const x = line * 100;
        capCsvRows.push([x,y,50_000+0.3*x-0.15*y,`F${line}`,"flight",120,sample].join(","));
      }
    }
    const maxRowsRun = await page.evaluate(async ({ csvText, options }) => {
      const run = await ((window as any).__m03RunFn as (file: File, input: unknown, hooks?: unknown) => Promise<any>)(
        new File([csvText], "browser-cap-control.csv", {type:"text/csv"}), options,
      );
      return {execution:run.execution,shape:run.result.grid.shape_yx,schema:run.result.schema};
    }, { csvText: `${capCsvRows.join("\n")}\n`, options });
    expect(maxRowsRun.schema).toBe("magnetic-flightline-process-result-1");
    expect(maxRowsRun.execution.original_csv_bytes).toBe(new TextEncoder().encode(`${capCsvRows.join("\n")}\n`).byteLength);
    expect(maxRowsRun.execution.resource_limits.rows).toBe(M03_LOCAL_LIMITS.rows);
    expect(maxRowsRun.shape[0] * maxRowsRun.shape[1]).toBeLessThanOrEqual(M03_LOCAL_LIMITS.gridCells);
  }, 180_000);

  it("keeps a stricter browser resource envelope than the Python parser maximum", () => {
    expect(M03_LOCAL_LIMITS.sourceBytes).toBe(16 * 1024 * 1024);
    expect(M03_LOCAL_LIMITS.rows).toBeLessThan(250_000);
    expect(M03_LOCAL_LIMITS.sourceLines).toBe(25_001);
    expect(M03_LOCAL_LIMITS.gridCells).toBeLessThan(250_000);
    expect(M03_LOCAL_LIMITS.crossoverSegmentTests).toBe(2_000_000);
    expect(M03_LOCAL_LIMITS.wallMilliseconds).toBe(180_000);
  });
});
