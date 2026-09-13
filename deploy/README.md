# Deployment

Inverse Earth Studio is a static research workbench. GitHub Actions publishes `frontend/dist` to GitHub Pages. The same built directory can be promoted to the ML VPS without a runtime Python service or a Node installation on the host.

The VPS release uses an immutable directory under `/var/www/geophysics.ml.fasl-work.com/releases/` and an atomic `current` symlink. Nginx serves the SPA with a deep-link fallback and caches hashed assets while keeping `index.html` and replay data revalidatable.

The deployment script ships only an already baked and locally validated build. It never runs the scientific pipeline on the server.
