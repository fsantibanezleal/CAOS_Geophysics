# Single-VPS release verification requirements

This implements the read-only verification part of the approved product R-017 and operating amendment, not a deployer or scientific acceptance waiver.

SV-01 The verifier shall accept exactly one HTTPS origin, without user information, query, fragment or project base. Gate: `tests/ops/test_single_vps_verification.py::test_origin_contract`.

SV-02 The verifier shall hash every regular file in the explicit completed frontend build and compare the same bytes remotely, including all six direct SPA routes. It shall reject links, unsafe paths, missing/changed files and bounded-byte violations. Gate: `tests/ops/test_single_vps_verification.py::test_exact_build_and_routes`.

SV-03 The verifier shall check the actual local auth profile and anonymous private-project refusal using GET only, without an account secret or cookie. Wrong HTTP status, content encoding, redirect or API body shall fail. Gate: `tests/ops/test_single_vps_verification.py::test_api_boundary`.

SV-04 Network operations shall retain normal certificate/hostname verification, reject all redirects and bound each body by the locally known size plus one byte. No decompression, proxy autodiscovery, login, upload, job, bake, service or filesystem deletion shall occur. Gate: `tests/ops/test_single_vps_verification.py::test_transport_bounds`.

SV-05 The optional operator-reviewed host inventory shall require exactly current plus two distinct rollback releases and enough measured free disk/memory for the stated additional release and active-job reserves. Integers shall not accept booleans, negative values or overflow. Gate: `tests/ops/test_single_vps_verification.py::test_retention_and_capacity`.

SV-06 A verification receipt shall never imply scientific, browser, worker or full-release acceptance. CLI output shall be written only to an explicit new file, with exclusive creation and no overwrite. Private host/deploy evidence belongs outside the public product repository. Gate: `tests/ops/test_single_vps_verification.py::test_receipt_and_no_overwrite`.
