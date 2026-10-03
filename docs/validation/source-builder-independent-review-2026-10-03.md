# Independent paired-source builder review

MAIN reviewed the complete builder and all 442 lines of its tests at `41f705245116e1f9d0a2ec4555bbeb050e4dea62`, the approved feature design, exact selection policy and operational guide. This review is separate from the producer's 250-test ops execution. Only seven new feature paths were promoted through PR118 to develop `b086cb3308ba02869daba4726ee42f9354edd198`.

## Actual independent execution

A fresh detached review worktree ran `tests/ops/test_source_bundle.py` with the existing read-only online-MT interpreter, bytecode disabled and entirely new external temporary fixtures. Result: **70 passed, one Windows symlink-privilege skip, 85.96 seconds**. The explicit runtime was detached `59f46c5a945531e573ae6db611a1f860237e3ba5`; the selected ops commit was frozen `5bc20eb3253c88c0cd903ccf06fc42aeb2a26b77`. The opt-in actual committed-pair API test executed, not skipped. It prepared eleven immutable fixture files and deleted only the marked disposable project's four files, leaving seven survivors. This is not an actual Linux or production drill.

The private JUnit receipt is retained outside all repositories at `D:\_worktrees\sb-main-c7c38458\source-review.xml`, SHA-256 `898111a718144113c2630ab269c2253bceefaf13a86e1b0541f1eed5fd589ebc`. Raw/source copies, selection JSON, bundle, private databases and deliberate failed-output fixtures stay private. No existing temporary directory was reused or swept.

## Independent immutable-object and archive verification

MAIN separately wrote and executed a private verifier without importing the builder. It read the exact Git commit/tree/blob objects through offline, no-replace, no-optional-lock Git commands with inherited Git redirects/config removed. It recomputed Git object identities, followed every selected tree chain, compared all 38 blob lengths and SHA-256 digests with the manifest, and independently parsed the raw tar headers/checksums, regular-file type, USTAR version, explicit epoch, sorted names, zero padding and exact member bytes. No extraction or source-repository write occurred in this review.

The actual committed-pair archive SHA-256 is `6de2abd4e31c267499eeb83a388ffb00920503c98bb936734ee8c6257ec1b0df`; manifest SHA-256 is `0b7a45069e587a6deea44d3ca5e36098f2816f6a13b1e9c0d4f0b15425c85d9f`. All 34 runtime blobs are also identical at develop `cf086dc817d095d66e46fdab53cc235a8e70004b`; this source-invariance check is not relabelled as a runtime execution at that commit. The private independent verifier SHA-256 is `b8674410d9146fe1f391e9b7552daeebe93632382c21c0ac2e8cd890eedbb9ff`.

The trusted installed interpreter/Git distribution, reviewed selection and launch source are prerequisites; their self-produced fingerprints do not authenticate their producer or establish production key/deletion authority. Content checks are defensive, not exhaustive secret detection. Unknown future correction/transform children remain unsupported until their separate recovery adapters are reviewed.

## Admission remains closed

PR117's tiny ADR correction independently passed the content guard, 94 frontend tests and a single-origin build, then develop CI `37112677175` passed at `cf086dc`. The historical CI failure at `46bd5e7` remains recorded. Neither that CI success nor this source-only bundle closes the unchanged 30% host disk gate, actual Linux restore, externally durable deletion acknowledgements, SMTP, identity, single-origin cutover or complete scientific/user acceptance. No host installation, service change, production/private-state mutation or release occurred here.
