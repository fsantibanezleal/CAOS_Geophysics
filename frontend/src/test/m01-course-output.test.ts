import { describe, expect, it } from "vitest";
import { fileURLToPath } from "node:url";
import { dirname, join, parse } from "node:path";
import { courseQaPaths } from "../../e2e/m01-course-output";

const repo = fileURLToPath(new URL("../../../", import.meta.url));
describe("course QA external evidence custody", () => {
  it("requires explicit absolute output before any test creates evidence", () => {
    for (const output of [undefined, "", "relative-output"]) expect(() => courseQaPaths(output, "run-01", repo)).toThrow();
  });
  it("identifies the caller's required output variable without relaxing custody", () => {
    expect(() => courseQaPaths(undefined, "run-01", repo, "GEOPHYSICS_VELOCITY_QA_OUTPUT"))
      .toThrow("Supply absolute GEOPHYSICS_VELOCITY_QA_OUTPUT outside the repository");
    expect(() => courseQaPaths(repo, "run-01", repo, "GEOPHYSICS_VELOCITY_QA_OUTPUT")).toThrow();
  });
  it("rejects repository, dependency and filesystem-root output", () => {
    for (const output of [repo, join(repo, "..evidence"), join(repo, "frontend", "node_modules", "qa"), parse(repo).root])
      expect(() => courseQaPaths(output, "run-01", repo)).toThrow();
  });
  it("rejects traversing or unbounded run names", () => {
    const output = join(dirname(repo), "external-course-evidence");
    for (const run of ["", "../escape", "a/b", "a".repeat(81)]) expect(() => courseQaPaths(output, run, repo)).toThrow();
  });
  it("keeps screenshot, trace and report paths together outside the repository", () => {
    const output = join(dirname(repo), "external-course-evidence"), paths = courseQaPaths(output, "run-01", repo);
    expect(paths).toEqual({ runRoot: join(output, "run-01"), evidence: join(output, "run-01", "evidence"),
      results: join(output, "run-01", "results"), report: join(output, "run-01", "report.json") });
  });
});
