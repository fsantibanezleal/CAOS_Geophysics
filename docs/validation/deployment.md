# Current deployment status — 2026-11-11

The only application origin is [https://geophysics.ml.fasl-work.com/](https://geophysics.ml.fasl-work.com/), served from the ML VPS. The current live release is `0.04.001`; the local candidate is `0.04.003`. No GitHub Pages application is configured or part of the deployment target.

The replacement has not been activated. Running `python scripts/verify_deployment.py https://geophysics.ml.fasl-work.com/` fails because the live catalogue does not match the local candidate. The existing release and two rollback releases remain protected. Product acceptance, scientific method gates, measured host admission, integrated browser acceptance and release verification must pass before cutover.

The [single-origin deployment requirement](../design/SDD.md) governs future releases. The archived [0.04.001 release receipt](deployment-0.04.001.md) documents an earlier release and deployment policy; it is historical evidence, not the current release plan.
