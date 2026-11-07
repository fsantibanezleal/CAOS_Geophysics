# Fixed-window authentication gate

The actual middleware uses integer Unix seconds and bucket_start = now - now%600.
Each client/scope bucket admits ten POST attempts; count greater than ten returns
429 with Retry-After = bucket_start +600 -now. This is a fixed UTC window, not
ten attempts per rolling600 seconds. Login/logout and absent auth-route POSTs
all count after unchanged origin/CSRF admission.

FW-01 THE HTTP integration gate SHALL test ten rejected login attempts and an
eleventh429 in a dedicated fresh DB/server, not infer its bucket count from a
multi-step owner case. Gate: local-real-access.spec.ts dedicated auth-rate test.

FW-02 WHEN server HTTP Date reports thirty seconds or less before its fixed
boundary, THE dedicated test SHALL wait remaining+one seconds (maximum31s),
then re-read Date and require a safe start. It SHALL not replace the backend
clock, increment counters directly, raise limits or silently retry a failed
control. Gate: frozen synthetic Date cases and actual dedicated HTTP run.

FW-03 THE test SHALL require all eleven response Date buckets to equal the
start bucket, the first ten responses400, and response eleven429 with
code:rate_limited and integer Retry-After in1..600. Crossing a bucket during
this bounded test fails explicitly rather than relabelling400 as an admission
failure. Missing/malformed Date fails closed. Same named gates.

Keep the nine original anonymous/owner/language/theme/device controls unchanged
except moving their incidental trailing rate probes to the dedicated gate.
Owner cookie/logout/cross-account/deletion checks remain mandatory. The added
pure scheduler test is not an HTTP/server result. No API/runtime/clock/policy
changes or production admission claim follow from this test correction.
