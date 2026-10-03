# Independent local accounting-protocol review

Date: 2026-10-03. Candidate [PR129](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/129)
at `3bedfe0bad821b3638cd9e7de718f7232a0198e7`. This is MAIN's independent
source review and local supplied-record execution, not a native worker receipt,
release acceptance, provider acknowledgement or permission to run a method.

## Exact reviewed scope

MAIN read all 1034 lines of scripts/physical_accounting_protocol.py and all
1022 lines of tests/worker_accounting/test_protocol.py. MAIN also read the full
eleven-path delta from the previously fully reviewed pure design
`2c94da44b6205652cd2d89d73ebbf78cc4626903`: two new code/test paths and nine
own feature documents. The final candidate changes no source/test bytes from
`965b0a248bc4fd74d9047757da2a06922bcabfae`.

Measured SHA-256 values of candidate files:

| File | SHA-256 |
| --- | --- |
| scripts/physical_accounting_protocol.py | 550a49d5b6ab3ec289f0c8722339c4a84af1d3b59e2786febce3c6d5566be622 |
| tests/worker_accounting/test_protocol.py | 662c9b1e0cf642b9ec0cea79bde897885752d4255188fc71de70e19ff3ce9215 |

The implementation imports only privately named dataclasses, enum, hashlib and
json. It accepts fixed byte/scalar arguments, not caller hooks, filenames,
handles, process IDs, configuration overrides or native counter readers.
The exact native-type checks precede coercion/equality hooks. Bounded byte
preflight precedes JSON allocation/integer conversion; nested returned records
are frozen. Unknown variants, duplicate keys and noncanonical bytes reject.

## Independent existing-suite replay

MAIN executed the actual candidate tests with the existing read-only
CPython 3.12.10 interpreter, without installing or editing dependencies:

```text
<EXISTING_READ_ONLY_PYTHON> -B -m pytest --noconftest -p no:cacheprovider -o addopts= -q tests/worker_accounting/test_protocol.py --junitxml=<NEW_PRIVATE_XML>
```

Actual outcome: **419 passed in 0.90 seconds**, exit 0; zero skips or xfails.
The private JUnit file SHA-256 is
`18cf6dcf5508ac4720751f831a6bcafd0d84787c82383dc6f7a2dbe213197d79`.
The XML is retained outside the repository. The duration is pytest output,
not a measurement of an executing scientific job's CPU or wall time.
Shared conftest and pytest caches were disabled; bytecode writes were disabled.
The external test harness's XML write is not an implemented protocol I/O feature.

## Newly authored independent controls

MAIN authored a separate private helper, independent of the producer's fixtures,
using only public protocol operations and literal records. Its SHA-256 is
`4042c05cfc736e5492cbd195a23d2daedf4f606de7fe759353c79fec843af77d`.
Execution passed **43 checks**, covering both platforms and both lanes.

The new records use different UUIDs, a nonzero asserted start offset, mixed
Windows user/kernel counters and Linux usage lower than user+system. Complete
finals have unequal but valid spacings. Sample count, byte count, digest and
receipt SHA are calculated independently from original canonical record bytes.
Release counters differ from the preliminary combined overhead while preserving
the exact checked sum and required budget relationship.

Controls include complete trace/receipt/release consistency; replayed release
becoming FAILED_HELD; CPU-stop thresholds; forbidden clean stop; malformed
native/derived CPU identity; sticky held state; exact maximum convertibles;
addition/multiplication overflow; delta underflow; bool rejection; preflight
integer/depth bounds; duplicate keys; negative zero; false runtime authority;
and rejection of implicit boolean eligibility. Emitted errors retain only fixed
application fields under direct calls, with no cause/parser context.

These are supplied-record consistency checks. Perfect synthetic records may be
protocol_eligible, but runtime_authorized is always false. They neither observe
an OS counter nor establish that supplied timestamps, hashes or assertions are
true. The helper reports os_measurements=false and runtime_authority=false.

## Review conclusion and remaining work

No blocking discrepancy was found in this narrowly approved pure unit during
MAIN's full read, suite replay and new controls. A separate exact-pin peer review
is still required before promotion; this document does not replace it.

All fifteen actual-platform gates remain CLOSED/NOT_RUN. There is no implemented
Job Object/cgroup controller, contained launch, real observation timer, aggregate
lifetime measurement, source/profile activation, persistence or release I/O.
The fixed 60/240-second ceilings and 57/237-second stop declarations are not
proven native enforcement and do not guarantee zero overshoot.

No API/worker/database/frontend caller was wired, no existing source-bundle or
admission policy was enlarged, and no production process, service, data, key,
deployment, DNS or hosting setting changed. Scientific acceptance, host resource
admission, independent durable recovery authority and full product convergence
remain separate pending requirements. Existing failures and historical receipts
are preserved, not replaced by this local pass.
