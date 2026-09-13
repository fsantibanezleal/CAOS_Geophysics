# Deployment

The static SPA is built locally or in GitHub Actions. GitHub Pages is the canonical public release. The ML host serves the same build from a static nginx document root and has no request-time compute. Deep links are supported by the Pages fallback copy.

Deploy only a verified frontend/dist. Never train, run inference, modify the manifest, or fetch unreviewed raw data during deployment. Verify the title, release record, case count, manifest byte checks, HTTPS certificate, and pointer-driven rendering on both endpoints.
