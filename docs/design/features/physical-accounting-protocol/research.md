# Pure accounting protocol design basis

Date: 2026-10-03. Status: documentation only, no implementation authorized.

MAIN reports a FULL read of all seven parent documents and all 34 primary
receipts at 3959ffc29eb4f93e0cca04fdc3154eca7ea7ddca. MAIN explicitly accepts
monitored aggregate accounting direction, NOT instantaneous zero overshoot;
correction/transform ceilings remain 60/240 seconds and final CPU>B is always
FAIL. MAIN expressly withholds OS launch/controller/security/provisioning,
profile activation and native probe authority because actual contexts are absent.
The next authorization is only to author this exact pure-unit sub-SDD before code.

The parent [research](../../../research/physical-worker-accounting-2026-10-03.md)
and [private contracts](../physical-worker-accounting/contracts.md) at that
immutable revision establish native units: Windows cumulative counters use
100-ns ticks; Linux counters use microseconds, converted by 1000 to ns and
conservatively charged with max(usage,user+system). This unit consumes supplied
integers and statements, never obtains those counters from an OS.

## Additional official language-interface research

Python's [JSON documentation](https://docs.python.org/3.12/library/json.html)
warns about hostile resource consumption and describes duplicate-key hooks,
integer conversion, nonfinite-number behavior and compact sorted serialization.
The proposed decoder therefore preflights byte/token/depth/node bounds BEFORE
decoding or constructing the JSON tree, rejects floats/nonfinite values and
duplicates, and does not rely on interpreter default numeric limits.

Python's [built-in type documentation](https://docs.python.org/3.12/library/stdtypes.html)
documents bool as an int subtype and integers with arbitrary precision. The
pure protocol must use exact builtin type checks (not isinstance(int)) and
explicit native/int64 range and arithmetic guards, not assume Python overflow
will reject incompatible native records.

Python's [exception documentation](https://docs.python.org/3.12/library/exceptions.html)
explains that raise-from-None suppresses display, not the retained context.
Inference for this design: fixed error payloads must not serialize exception
context/tracebacks or retain a JSON parser exception. Map expected parser errors
to a fixed code, then raise outside its handler; no debug/log export. This does
not promise that Python traceback frames are a secret-free memory boundary.

Our design inference: a bounded pure parser/converter/state machine can be
implemented and tested without an OS context. Passing it proves only consistency
of the supplied record stream. It cannot establish counter authenticity,
containment, finality, durability, source provenance or permission to publish.

## Actual read-only HTTPS receipts

Invoke-WebRequest -UseBasicParsing, RawContentStream response-body bytes, SHA256
in memory; no full page persisted. These are decoded HTTP body hashes, not TLS
wire/signed/installed-runtime evidence. No secrets, source measurements or host
contacts. Retrieval is design research, not future protocol runtime I/O.

| Source | UTC completion | HTTP | Body bytes | SHA-256 |
| --- | --- | ---: | ---: | --- |
| [Python 3.12 JSON](https://docs.python.org/3.12/library/json.html) | 2026-10-03T11:18:09.2278964Z | 200 | 107891 | `1a5e4ba18342b32f5f174d129f9c226a21a9445a89384f13a3f33ec327c2b68f` |
| [Python 3.12 built-in types](https://docs.python.org/3.12/library/stdtypes.html) | 2026-10-03T11:18:09.6814542Z | 200 | 648964 | `71f0518841d019a0ba058f321082930d4e0d7f7aca704d76a3e54987383b3e97` |
| [Python 3.12 exceptions](https://docs.python.org/3.12/library/exceptions.html) | 2026-10-03T11:41:39.3605740Z | 200 | 139853 | `d4f18fa368d9b84e07a2d888686cacc9d6164f7587793dca6056d5f2c17e7905` |

No new OS research changes the parent evidence or selects an alternate mechanism.
Read [requirements](requirements.md), [design](design.md), [contracts](contracts.md),
[validation](validation-plan.md), [tasks](tasks.md) and [review packet](review-packet.md)
before approving any later source scope. All future unit gates are NOT_RUN.
