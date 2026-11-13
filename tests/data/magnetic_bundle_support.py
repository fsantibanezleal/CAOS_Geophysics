"""Small envelope fixtures for local magnetic bundle container controls."""

import magnetic_survey_bundle as bundle
from magnetic_survey_json import digest
from magnetic_survey_support import encode, request as protocol_request


def make_candidates():
    betas = (0.0001, 0.001, 0.01, 0.1, 1., 10., 100., 1000.)
    return [{"id": f"candidate-{i:02d}", "beta": beta,
             "penalty": penalty, "folds": [], "status": "failed", "score": None}
            for i, (beta, penalty) in enumerate(
                (value, penalty) for value in betas for penalty in ("l2", "sparse_smallness"))]


def make_manifest(intent="local_calibrate", status="failed"):
    candidates = make_candidates()
    history_members, history_payloads = bundle.encode_history_table([], candidates)
    request_metadata, request_members, request_payloads = bundle.encode_request_metadata(
        encode(protocol_request()))
    payloads = {**history_payloads, **request_payloads}
    members = history_members + request_members
    names = [member["name"] for member in history_members]
    result = {
        "schema": "magnetic-survey-result-1", "status": status,
        "identity": None, "inventory": None, "partition": None,
        "candidates": candidates, "selected": None, "model": None,
        "prediction": None, "metrics": None,
        "history": {"codec": "magnetic-history-table-1",
                    "index": {"member": names[0]},
                    "numeric": {"member": names[1]},
                    "model_hash_words": {"member": names[2]}},
        "diagnostics": None,
        "claims": {"full_method_accepted": False, "field_source_verified": False,
                   "geology_truth_known": False, "online_admitted": False},
    }
    request_metadata["intent"] = intent
    source = request_metadata["source"]
    manifest = {"schema": "magnetic-survey-bundle-1", "result": result,
                "request_metadata": request_metadata,
                "original": {"sha256": source["original_sha256"], "bytes": source["original_bytes"],
                             "scope": source["scope"], "rights": source["rights"],
                             "included": False},
                "members": members}
    manifest["generation_sha256"] = digest(manifest)
    return manifest, payloads
