import { lstatSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";

/** Explicit external QA storage, never a dependency directory or repo fallback. */
export function courseQaPaths(output: string | undefined, run: string, repository: string) {
  if (!output || !isAbsolute(output)) throw new Error("Supply absolute M01_COURSE_QA_OUTPUT outside the repository");
  if (!/^[a-z0-9-]{1,80}$/.test(run)) throw new Error("Invalid owned QA run name");
  const root = resolve(output), repo = resolve(repository), inside = relative(repo, root);
  if (dirname(root) === root || inside === "" || (inside !== ".." && !inside.startsWith(`..${sep}`) && !isAbsolute(inside)))
    throw new Error("Course QA output must be external, not a repository or filesystem root");
  for (let current = root; ; current = dirname(current)) {
    let entry;
    try { entry = lstatSync(current); }
    catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }
    if (entry) {
      if (entry.isSymbolicLink() || !entry.isDirectory()) throw new Error("Course QA output ancestry must be real directories");
    }
    if (dirname(current) === current) break;
  }
  const runRoot = join(root, run);
  return { runRoot, evidence: join(runRoot, "evidence"), results: join(runRoot, "results"), report: join(runRoot, "report.json") };
}
