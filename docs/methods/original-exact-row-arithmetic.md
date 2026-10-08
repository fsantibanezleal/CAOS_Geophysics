# Original source exact-row certificate arithmetic

Prospective public original source epoch candidate7. This arithmetic is not a
native-host grant, a full M02/M04 acceptance or a compiled/quartic bridge.
Original source6 receipts and failed complete firstfits remain historical.

The source-owned terminal and magnetic field-domain proof use exact integer
row reductions. The non-native lanes of the original chord proof use the same
reductions at the unchanged34/50/80 digits; its first native-row lane stays
unchanged. Sparse/narrow original stencils and all source factor nesting,
SD divisions, stored-L/root actions, native H/g, objective, starts/bounds,
scientific weights and stopping predicates remain unchanged.

For literal binary64 coefficient c=n*2^b (signed <=53-bit significand) and
finite Decimal endpoint x=a*10^e, choose E=min endpoint exponent and
B=min nonzero coefficient binary exponent, also <=0. Then each row sum is

    S = sum(n*a*10^(e-E)*2^(b-B))
    exact value = (S*5^(-B))*10^(E+B).

All reductions are exact Python integer operations, scheduled via NumPy object
arrays, not floating BLAS. Sign of c selects the correct lower/upper endpoint.
Exact zero is represented with exponent0; nonzero subnormals retain b=-1074.
Only the final exact Decimal is rounded by isolated FLOOR/CEILING contexts.
The new interval therefore encloses the same original real factor action,
with no accumulated floating or sequential Decimal error estimate. Fraction
is TEST ONLY. No physical H is materialized and no source-sized integer cache
or previous-stage certificate is retained.

## Closed range, actual storage and lifetime

Dense actions have <=4096 rows/columns. Endpoint significands have <=1200
digits, exponents[-1200,1200], finite ordered pairs; coefficient finite64.
Significand/exponent and aligned endpoint-pair storage is checked BEFORE
alignment allocation against existing2048-byte endpoint slots. No new grant.

Accumulator bit count is less than
ceil(1200 log2(10))+ceil(2400 log2(10))+53+2045+12 <14100.
Final exact Decimal has <5100 digits, including5^1074. Integer storage uses
the loaded sys.int_info digit width/size; loaded real object sizes are tested.
Conversion/tuple scratch is covered by262144 bytes. The common source endpoint
ledger and terminal12f free-endpoint slots cover original vectors and the two
prepared representations; e.g. Joseph action peak <=11f+a+5m endpoint pairs,
covered by12f+6a+6source_components (m<=source_components).

At most eight source rows' native bit arrays coexist. They are charged at
128*rows*columns before object block selection. One coefficient-object array,
selected endpoint references, one product array, exact sums and conversions
fit the existing simultaneous8MiB native-workspace phase. The largest block
up to8 is chosen by this literal storage calculation; if even one row cannot
fit, the certificate FAILS without an arithmetic/solver fallback. Source
validation and original simultaneous allocation dictionaries remain gates,
distinct from actual RSS/process containment. Check deadline each row block
and during endpoint preparation. Dispose all temporaries on return/failure.

The literal terminal file binds physical_original_rows.py SHA; construction
and expanded domain/chord execution check loaded and on-disk source equality.
Consumer inventories should also list that named transitive module. Terminal
receipts name exact-dyadic-original-terminal-1, its SHA and8MiB scratch limit.
Independent tests include cancellation, signed extrema, transpose, zero and
subnormal retention, sparse unchanged action, ambient contexts, malformed
dimensions/ranges, real object sizes, preallocation denials, expiry, source
drift and the unchanged native stored-noise/strong-accuracy negative controls.

Fit acceptance still requires all actual source chords, native true CG
residual<=1e-6, summedCG<=200, accepted<=200/states<=201/LS<=20,
uninterrupted120 s clock, strict physical field ratio>1e-8, original source
strong-convexity/Neumann/free-box/active-sign/KKT/model/objective/prediction
certificates and original768MiB M04 or2GiB M02 source-bound quota. A faster
microbenchmark or independent L2 pass never unlocks incomplete sparse stages.
