import type { ShellRoute } from "@fasl-work/caos-app-shell";
import manifest from "./routes.json";

export interface ProductRoute extends ShellRoute {
  id: string;
}

/** The ordered public navigation and router table. Build entrypoints read the same JSON. */
export const PRODUCT_ROUTES: readonly ProductRoute[] = manifest;
