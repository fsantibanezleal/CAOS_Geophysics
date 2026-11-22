# Original-IRLS floor continuation: post-cap research only

**Status: diagnostic evidence; not production convergence, candidate selection, or method acceptance.**

## Frozen source and experiment

This experiment starts from the immutable family-0 / condition-0 original24 archive `family0-condition0-42c602cd2ccd226e.gza` (SHA-256 `c4b14395699a84a5ca459ae865f955a7f8baea1ec2869051cc8b215b3b6a64bf`). Its request SHA-256 is `21df6770b31fcc94b67025a202cc589e0df4412f156f41bf4b8db1f4bd9b2cc6`, result SHA-256 `72148cb969aca853f7c3b494ddcb03676c15af9e4a99ed717dde83bc2835dda3`, and source-inventory SHA-256 `f543f9f1919481f1e2c7b110789fde4872548f0ba00d607691c4fbb6853de0ef`.

The research harness restarts each recorded terminal model at the archived epsilon floor, runs the source-bound original partition solver, independently replays each added native solve, then calculates the untouched held-out fold metrics. It now starts from `fit['models_q'][-1]`, byte-for-byte equal to the archived final native state, rather than reconstructing it from rounded physical units. The first receipt set divided `model_kg_m3` by 1000 and could shift the initial state by an ULP; all receipts without the `-exactq` suffix are superseded and must not be used as continuation evidence. The corrected harness is `scripts/research/continue_irls_floor.py` (SHA-256: `592743c0cde6fe8d2ef4aa21dbe8b3b6784aa5a4797c943f64863bd8d7ae36b2`). Outputs are new JSON receipts outside the repository at `E:\_Datos\CAOS_Geophysics\validation\floor-extension-research-20261031\`.

**The experiment adds solves beyond the original policy limit of 20 IRLS weight updates.** A research `floor_fixed_point` therefore does not satisfy the unchanged production terminal contract, which requires exactly the approved stage book and update cap. No limit was changed in production, and no output below is a production-eligible fit. The continuation also occurs after the original calibration's 1,800 s aggregate budget; it cannot repair the original24 aggregate-wall failure.

## Results

| Candidate | Fold 0 WRMS | Fold 1 WRMS | Fold 2 WRMS | Research continuation | Mean normalized held-out `phi_d` |
|---:|---:|---:|---:|---|---:|
| 0 | 19.390 (original) | zero-free-direction failure | 4.303 | Fold 1 cannot continue from its exact archived state; fold 2 reaches the research floor criterion but has poor held-out fit quality. | not scored |
| 1 | update cap after 12 added stages | 8.522 | update cap after 6 added stages | Fold 1 reaches research criterion after 8 added updates but has poor held-out fit quality. | not scored |
| 2 | unresolved | unresolved | merit line-search failure | Not continued: no supported continuation from the failed fold-2 state. | not scored |
| 3 | 5.388 | 1.716 | 1.748 | All three folds reach the research floor criterion after one added stage each. | 11.6760 |
| 4 | 1.842 | 1.039 | 1.287 | All three folds reach the research floor criterion after one added stage each. | 2.0439 |
| 5 | 1.232 (original) | 1.037 | 1.225 | All three folds have a research terminal state. | 1.3646 |
| 6 | 1.473 (original) | 1.070 (original) | 1.040 | All three folds have a research terminal state. | 1.4655 |
| 7 | unresolved | unstarted | unstarted | The archived calibration hit its wall cap; no continuation accepted. | not scored |

The mean score shown for candidates 3–6 is the equal-size-fold mean of `WRMS²`; it is an arithmetic summary of the archived and exact-state continuation fold scores, **not** the production selection result. Candidate 5 scores lower than candidate 6 among these research-only continuations. Candidates 0–2 and 7 are incomplete, and the original calibration's overall time gate failed, so candidate 5 cannot be declared selected and no development refit or outer evaluation is justified from this experiment.

The small held-out residuals for candidate 5/6 do not prove geological recovery, field usefulness, or generalization beyond the frozen synthetic folds. Candidate 1 fold 1 demonstrates why a solver terminal alone is insufficient: the continued solution's held-out WRMS is 8.522.

## Existing terminal-stage certificate audit

The archived final stage of every candidate 3–6 fold recorded the original inner solver reason `absolute_stationary`. The new `scripts/research/audit_irls_terminal_certificate.py` reconstructs each final stage from the exact native archived `q`; it confirms the recomputed weight arrays are bitwise identical in all 12 folds, projected-KKT infinity residuals span `1.76e-13` to `8.04e-13`, and the minimum positive smallness-diagonal coefficient is `0.15`. Source SHA-256: `f7042767de6e771e24bb2af624b84aaaee5102bce4ba42f1990ab800de3cb408`. External receipt `terminal-certificate-exactq-v2.json` has SHA-256 `aec2367f239cf51e659502fe62f52dc881c1f9909b9a2cdc0f35b10ef20ed19a` and embedded receipt digest `a7b779dbbc8e12f8c23141b998b10184e8a45b99547fb691ea07c5fbd3c6bf17`.

The downstream fit still reported `irls_iteration_cap` for candidate 3/4 and candidate 5/6 folds whose last three transitions did not meet the declared three-change test. The added research stage did zero optimizer iterations and mainly supplied another measured transition. This is evidence that the three-transition test is the remaining terminal distinction for these specific folds; it is **not** authority to bypass that declared test. The M02 specification and existing positive-cause review explicitly require a separate scientific/design review and fresh adversarial controls before adopting a different terminal certificate. No terminal-policy change is implemented here.

## Key receipt hashes

Every receipt's embedded digest is independently checked by its producer. The following are the byte-level SHA-256 values of the external receipt files:

| Receipt | Status | File SHA-256 |
|---|---|---|
| `candidate0-fold1-exactq.json` | zero-free-direction failure | `0b9e9f0e033f184051e883624c8a212b1f3c0fde8903c729ec045ea2286fc2c0` |
| `candidate0-fold2-exactq.json` | research floor criterion; WRMS 4.303 | `ff333ba137f36cd110f30c3800a890a5dc83b848ae930a89c240f88cd05d5329` |
| `candidate1-fold0-exactq.json` | update cap after 12 added stages | `d21ffd38284032743eb4f23cb82e699ab853052a5d3d3861ea1d1b93551d02ef` |
| `candidate1-fold1-exactq.json` | research floor criterion; WRMS 8.522 | `859f40fc2597128af316857d4524702bc695e4636ccfcb7d1aa46121bfd75124` |
| `candidate1-fold2-exactq.json` | update cap after 6 added stages | `da21dd59bd1c3653693d69526c09e79f6f6b5b3659c32170ff665bd7a5d6428a` |
| candidate 3, folds 0–2 | all three research floor criteria | `65ab70d1389497a0e87dca959bb72174a1e7fd4c287a63bb5e3f0e37d8172fc9`, `f2d51ce40862717ed7aae613e1d01b2f68b52d2c9ba558a4a0345a05c7d5d0c2`, `73f9d21ddc25ab833feea09b498f776684396b82ee2aea6b0111d9cfd2c95323` |
| candidate 4, folds 0–2 | all three research floor criteria | `bb63c1091eee0de3584e4e873f3bac1f7fa42375fbc79f0bf3b8a2987cca42b1`, `7f52bcc733b814a61ee6b218588e5c765ce8b6795628c3088f8272a3b314637a`, `f72ef549831d04d3aa63d8c9cfbf41c1f0a751d29b4daa7e98b12c022fd93cad` |
| candidate 5, folds 1–2 | both research floor criteria | `239dd7beb62ac161a2f8ca5122a509951597bbeab5b18e256c4b0b7faf54ee53`, `a52fe134c5c4f311e1d14e98441b96fbf81e870adaa80fe4f3b6ac26b46b7edb` |
| `candidate6-fold2-exactq.json` | research floor criterion; WRMS 1.040 | `83166d551280e0a37589259144210427e78ba126f9053d1483ce23c3f8006b68` |

## Decision and remaining work

Do not change the production cap, accept the post-cap solutions, or release a selected candidate from this evidence. A policy change would require an explicit scientific design decision plus a fresh complete calibration under its approved aggregate budget and independent acceptance. The next valid calibration must resolve candidates 0–2 and 7 (including candidate 2's merit failure), score the entire frozen candidate set, pass the unchanged aggregate/per-fit limits, refit the selected beta on development data, and produce the outer evaluation. The 23 other family/condition pairs remain unrun. The bound-active tied-maximum case also still requires a mathematically justified generalized KKT treatment; arbitrary tie selection is inadmissible.

The original full archive remains the controlling failure: 1,800.313000000002 s versus the 1,800 s cap, zero of eight candidates eligible, 22 started fits independently replayed, maximum started-fit time 117.453 s, and two fits explicitly unstarted. See [the source-bound precision replay](precision-replay-2026-10-31.md).

A separate [terminal-certificate amendment proposal](../terminal-certificate-amendment-proposal.md) is pending owner decision. Its proposed rule has not been implemented or applied to the original calibration.
