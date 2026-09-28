"""M12 matched-input classical comparator and locked cohort controls."""
import numpy as np

from velocity_validation import (
    COHORTS, CLASSICAL_LAMBDAS, classical_predict, make_cohort, operators, score,
    select_classical, sha256_bytes,
)


def test_disjoint_groups_and_matched_inputs():
    ops = operators()
    validation = make_cohort("validation", ops, fixture=True)
    family = make_cohort("family_only", ops, fixture=True)
    joint = make_cohort("joint_ood", ops, fixture=True)
    assert {record["id"] for record in validation["records"]}.isdisjoint(
        record["id"] for record in joint["records"])
    assert set(family["acquisition"]) == {"A", "B"}
    assert set(joint["acquisition"]) == {"C"}
    lam, candidates = select_classical(validation, ops)
    assert lam in CLASSICAL_LAMBDAS
    assert set(candidates) == {str(x) for x in CLASSICAL_LAMBDAS}
    classic = classical_predict(joint, ops, lam)
    assert classic.shape == joint["velocity"].shape
    assert np.isfinite(classic).all()
    assert 1400 <= classic.min() <= classic.max() <= 4000
    same_input = score(joint, classic.copy(), classic, ops, threshold_ms=0.0)
    assert same_input["noisy_input_sha256"] == sha256_bytes(joint["observed"].astype("<f8").tobytes())
    assert same_input["learned_velocity_rmse_m_s"] == same_input["classical_velocity_rmse_m_s"]
    assert same_input["learned_oracle_rmse_ms"] == same_input["classical_oracle_rmse_ms"]
    assert COHORTS["train"][0] == 800 and COHORTS["validation"][0] == 160
