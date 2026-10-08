# Native broker input transport, 2026-10-08

The literal client-input unit implements the reviewed request layout and
immutable source transfer. It does not implement a broker listener, peer
authentication, production launch, result publication or a scientific method.
No service, public route or live release was changed by these controls.

## Exact-byte contract

The request is352 little-endian bytes with fixed LBR1/version1/SUBMIT1 framing,
sequence1 and zero reserved fields. Identifiers are nonnil raw16-byte values;
hashes are raw32-byte values; lengths are non-boolean integers. Source5MiB,
parameters64KiB and lineage16KiB ceilings are transport bounds, not new scientific
profiles. Larger physical correction/transform requests are not admitted by
this unit. Unknown fields, mutable buffers, zero identities, short/long framing,
corrupt headers/reserved fields and over-cap lengths are rejected.

Hashing preserves the original bytes: integer1 and floating1.0 remain different
inputs. There is no scientific JSON parsing or reserialization. A source hash
is not peer authentication or evidence of successful computation.

## Local execution

Fresh source-frozen execution passed177 tests, zero failures/errors/skips,0.353s.
The suites cover the new transport, unchanged qualification context and source
scope. Ruff and diff checks also pass. JUnit SHA-256:

```text
a98fff0c2db9b765679ccb0a3d0479e40c2573e540f50efe81ac812034cf3391
```

The driver recorded exit0 and stable pre/post source and runtime inventories.
No existing qualification controller or accounting policy was edited. The
Windows unsupported-platform control fails closed; it is not Linux operation
evidence.

## Actual Linux input operations

The source and control script were copied to a separate private directory and
independently hash-checked before a20-second-bounded run. Actual kernel
6.8.0-117-generic and CPython3.12.3 were read before execution. Interpreter SHA:

```text
e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f
```

Client source SHA:

```text
8ef4563f139abc73a6f577253af163cc9988a69e310c1d9e62b7a4c91b6e270c
```

Final Linux control source SHA:

```text
706aeef6f8c0ecd657ea5f7a32c1968e97531565b1135552938c21133ca8802a
```

Actual exit0 controls measured three exact input bodies, read-only/CLOEXEC
descriptors and WRITE/GROW/SHRINK/SEAL seals. Nine attempted writes/shrinks/grows
through reopened writable descriptors returned EPERM without altering bytes.
All published descriptors closed after context exit. An injected second-input
preparation failure closed the first input and exposed only a fixed safe code,
without private OS context. A caller exception also left the descriptor census
unchanged. Original first-run source/evidence remains retained.

## Unaccepted boundaries

These controls do not test socket ancillary transport, sender credentials,
retained peer PIDFD/unit identity, source-profile eligibility, clone3 birth,
aggregate CPU/memory/scratch containment, scientific engines, cancellation,
durable database publication or restart recovery. All full broker and production
gates remain required. The control explicitly reports native_launch_accepted,
peer_identity_accepted, method_accepted and production_accepted as false.
