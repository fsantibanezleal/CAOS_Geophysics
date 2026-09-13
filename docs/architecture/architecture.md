# Architecture

## What this app is and is not

Inverse Earth Studio is a deterministic, static-first research instrument. Local processing creates compact replay artifacts; the browser animates and recomputes a bounded analytic mirror. It is not a cloud solver, an automatic field interpreter, or a claim that one inverse model is geologically unique.

## Lanes

The offline lane owns ingestion, preprocessing, grouped split, features, solver-backed forward or inverse work, learned calibration, evaluation, export, and validation. The browser lane owns low-latency parameter changes, linked maps and profiles, pointer readouts, and animation. The replay lane is the release fallback and source of truth for baked results. The VPS has no GPU and serves a static mirror only.

## Determinism

Every case is a pure function of its parameters and seed. The generator uses numpy.random.default_rng, stores the seed in the manifest, serializes compact JSON with sorted keys, and validates artifact byte size. Wall-clock runtime influences lane classification but is not inserted into canonical data. This prevents an unchanged scientific run from creating a noisy diff.

## Pipeline flow

raw -> ingest -> preprocess -> grouped split -> features -> train -> infer -> evaluate -> export -> validate -> replay.

The split is grouped by case, not by adjacent observations. This blocks a frequency or spatial sample from the same physical model appearing in both training and held-out evaluation. A contract test rejects missing fields, NaN, non-positive frequencies, unknown units, and malformed numeric values.

## Release

GitHub Pages is the canonical static deployment. The ML host is an independently checked HTTPS mirror for large public artifacts and operational continuity. Both hosts receive an already baked frontend/dist; deployment never trains, rewrites manifests, or runs a benchmark.
