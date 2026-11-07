# Linux protected-profile execution integration

2026-10-08. Implements the existing approved bounded VPS job requirement. It
does not introduce an external service, backup, account or permission prerequisite.

- PL-01: only a previously admitted running owned ERT/traveltime job can launch
  the fixed hash-bound interpreter/producer, with its exact raw/dataset/request
  identities. No executable, environment, path, systemd property or native plugin
  comes from a browser request.
- PL-02: Linux child execution has actual nonroot IDs, empty capabilities, NNP,
  no network, read-only code/inputs, one CPU, 2 GiB kernel memory charge, zero swap,
  64 MiB private hard scratch and 600 s wall limits. Smaller administrative
  controls do not change numerical parameters. Existing Windows execution remains
  separately labelled and tested.
- PL-03: owner cancellation, caller EOF, launch failure, malformed input and
  resource exhaustion stop only the exact owned unit. No passed result is
  published before extinction, complete retained-member verification and ordinary
  transactional publication. Failed/uncertain files remain recoverable.
- PL-04: the worker integrates the measured child receipt without substituting
  memcg charge for RSS, soft file-size observations for hard quotas, or root
  observer CPU for complete native method CPU admission.
- PL-05: actual queued API/worker runs, cancellation/crash/resource interventions,
  owner isolation and result export are required on the private VPS candidate.
  The earlier direct private engine qualification alone cannot enable production.

Gates: constructor/packet adversarial tests, unchanged profile API regression,
actual original ERT and traveltime queued executions, cancellation/EOF and
memory/scratch/time controls, exact source/environment/member receipt audit,
and integrated authenticated browser roundtrip. Full maximum input geometry and
30-run/p95 admission remain separately recorded; nominal inputs do not establish
those populations.
