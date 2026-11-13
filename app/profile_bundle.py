"""Portable protected profile bundle; no original bytes or fabricated field truth."""
import io
from types import SimpleNamespace
import zipfile

from app.errors import ApiError
from app.processing_contract import canonical_bytes, sha256
from app.profile_contract import validate_profile_dataset, validate_profile_result


def profile_manifest(dataset, result, dataset_sha, result_sha):
    return {"schema": "geophysics.processing-bundle/v1",
            "dataset_id": dataset["dataset_id"], "job_id": result["job_id"],
            "method_id": result["method_id"], "parameters": result["parameters"],
            "rights": dataset["profile_metadata"]["source"]["rights"],
            "axes": dataset["axis_order"], "dimensions": dataset["dimensions"],
            "units": {"position": "m", "observation": dataset["observation_unit"]},
            "provenance": {"raw_sha256": dataset["parent_raw_sha256"],
                           "dataset_sha256": dataset_sha, "request_sha256": result["request_sha256"],
                           "child_code_sha256": result["child_code_sha256"],
                           "profile_code_hashes": result["profile"]["code_hashes"]},
            "members": {"dataset.json": {"sha256": dataset_sha, "bytes": len(canonical_bytes(dataset))},
                        "result.json": {"sha256": result_sha, "bytes": len(canonical_bytes(result))}},
            "raw_bytes_included": False}


def verify_profile_contents(manifest, dataset, result, dataset_sha, result_sha):
    try:
        validate_profile_dataset(dataset, SimpleNamespace(
            id=dataset["dataset_id"], owner_id=dataset["owner_id"], project_id=dataset["project_id"],
            raw_asset_id=dataset["raw_asset_id"], raw_sha256=dataset["parent_raw_sha256"],
            parser_version=dataset["parser_version"], modality=dataset["modality"],
            row_count=dataset["dimensions"]["measurement"]))
        validate_profile_result(result, SimpleNamespace(id=result["job_id"], dataset_id=dataset["dataset_id"],
            dataset_sha256=dataset_sha, method_id=dataset["method_id"], request_sha256=result["request_sha256"],
            request_json={"parameters": result["parameters"], "raw_asset_id": dataset["raw_asset_id"],
                          "raw_sha256": dataset["parent_raw_sha256"],
                          "profile_child_sha256": manifest["provenance"]["child_code_sha256"],
                          "profile_code_hashes": manifest["provenance"]["profile_code_hashes"]}))
        if (manifest != profile_manifest(dataset, result, dataset_sha, result_sha)
                or result["profile"]["geometry"] != dataset["geometry"]
                or result["profile"]["metadata"] != dataset["profile_metadata"]):
            raise ValueError("profile geometry, declaration or manifest differs")
        report = result["profile"]["engine_report"]
        if "inverse" in report:
            observations = (report["inverse"]["observed_r_ohm"] if dataset["modality"] == "ert_profile"
                            else report["observations"]["picked_t_s"])
            if observations != dataset["observed"]:
                raise ValueError("profile result observations differ from owned original dataset")
    except (ApiError, KeyError, TypeError) as exc:
        raise ValueError("profile bundle contract mismatch") from exc


def build_profile_bundle(dataset, result, dataset_sha, result_sha):
    if sha256(canonical_bytes(dataset)) != dataset_sha or sha256(canonical_bytes(result)) != result_sha:
        raise ValueError("profile bundle inputs differ from receipts")
    manifest = profile_manifest(dataset, result, dataset_sha, result_sha)
    verify_profile_contents(manifest, dataset, result, dataset_sha, result_sha)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, item in (("manifest.json", manifest), ("dataset.json", dataset), ("result.json", result)):
            archive.writestr(name, canonical_bytes(item))
    encoded = output.getvalue()
    from app.bundle import verify_bundle
    verify_bundle(encoded)
    return encoded
