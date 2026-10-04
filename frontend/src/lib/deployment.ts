export type DeploymentMode = "single-origin";

/** Both development and production builds use the approved root-only VPS origin. */
export const deploymentMode: DeploymentMode = "single-origin";

export function routerBasename(_mode: DeploymentMode, _pathname: string): string {
  return "/";
}

export function artifactBase(_mode: DeploymentMode, _pathname: string): string {
  return "/";
}
