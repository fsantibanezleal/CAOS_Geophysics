export type DeploymentMode = "legacy" | "single-origin";

/** The target mode is opt-in until the single-origin cutover is approved. */
export const deploymentMode: DeploymentMode =
  import.meta.env.MODE === "single-origin" ? "single-origin" : "legacy";

export function routerBasename(mode: DeploymentMode, pathname: string): string {
  if (mode === "single-origin") return "/";
  // Preserve the two existing static origins while the replacement is built.
  return pathname === "/CAOS_Geophysics" || pathname.startsWith("/CAOS_Geophysics/")
    ? "/CAOS_Geophysics"
    : "/";
}

export function artifactBase(mode: DeploymentMode, pathname: string): string {
  const basename = routerBasename(mode, pathname);
  return basename === "/" ? "/" : `${basename}/`;
}
