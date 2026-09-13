# GitHub Pages

The Pages workflow is `.github/workflows/deploy-pages.yml`. It checks the committed artifact contract, installs the precompute requirements needed by the checks, rebuilds the frontend, and publishes `frontend/dist` with `actions/deploy-pages`.

Enable it once in the repository settings with Pages source set to GitHub Actions. The project-site build uses a relative Vite base, so both the Pages project URL and the ML host use the same artifact.
