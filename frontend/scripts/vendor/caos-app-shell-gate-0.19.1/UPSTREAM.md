# Vendored CAOS shell gate

This directory vendors the measured gate shipped by `@fasl-work/caos-app-shell@0.19.1`, the exact shell version pinned in `frontend/package.json`. The UI and shell components continue to come from that npm package. The product runs this owned copy so its route and artifact requirements are explicit, reviewable, and independent of edits to `node_modules`.

Upstream npm package integrity: `sha512-Sh3AiWPgFsm96cMNOOv8cZ8LTDsXe5X8ZbNQXt8rE71Gf51YDY6wMhb1J7Wzsm/w+CQzd0GfzMry8iEr4eqAqw==`.

The five gate modules below are otherwise copied from the package. Their upstream SHA-256 values are recorded here so the vendored baseline can be reconciled on a shell upgrade:

| File | Upstream SHA-256 |
| --- | --- |
| `gate/areas.mjs` | `a8f0d76b846d2860524d3e2b5505d10e69057762a6b089b32f40761428e9d962` |
| `gate/inpage.mjs` | `62257adc0f51ac765cb9772a6e824222d2d75d6b59119b19ac2efb0cb64e69e7` |
| `gate/png.mjs` | `b8363a8124b03ebdb2ac30a009b584a11ac88ed8e3bc8731c9c70467c5c58903` |
| `gate/run.mjs` | `8a130bf8bf3c05c934f2ff52dd1f193979889930d8d8c1aa7d286cd4e84c4df4` |
| `gate/serve.mjs` | `489f68d0d621a95cb83ecd54e7bb036a16c9113912eb42d0136bb82e80e7bb5f` |

## Product-specific changes in `gate/run.mjs`

1. A product configured with `workbench_route: "/"` is checked as a workbench at the root. Other products retain the upstream Introduction landing check.
2. The trailing-slash probe for `/` uses `/` itself. Other routes retain the upstream trailing-slash check.
3. The key constants are loaded through the pinned package's public `./keys` export because this copy does not live inside the package's `dist` tree.
4. JSON response bodies are measured with real HTTP GETs to the gate's configured origin. For every fetched JSON path, the gate checks HTTP 200, `application/json`, reads the complete response body, checks `Content-Length` when supplied, parses JSON, and records byte length and SHA-256. It additionally requires the browser workbench to fetch all four FWI reference files and checks each response's `inverse-earth/v2` schema and case id.

## Product-specific change in `gate/serve.mjs`

The Windows file server retries `EBUSY` reads three times with 25/50/75 ms
backoff, then returns HTTP 503 instead of terminating the gate process. This
covers transient NTFS sharing violations observed while the browser gate read
a 24 MiB built FWI artifact. Other filesystem errors are not retried.

The artifact verification does not read files from `dist` directly. In the default local run, the HTTP origin is the shell gate's static server over `frontend/dist`, so the measured bytes are the bytes the server actually returns. With `--url`, the same checks run against the supplied origin.

The five upstream gate modules have the same SHA-256 values in shell 0.19.1 as in 0.19.0; `gate/run.mjs` retains the documented product-specific adaptations above. Shell 0.19.1 also fixes narrow-screen flowing PlotCard content and localizes UPlot date labels; see the upstream changelog for the release details.

When upgrading the shell pin, replace this baseline from the matching published npm package, reconcile the product changes above, update the hashes and rerun the full product gate. Do not patch the installed package at runtime.

The upstream MIT license is included as `LICENSE`.
