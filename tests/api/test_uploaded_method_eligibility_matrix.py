"""Cross-modality checks for the selected-dataset method API."""


def test_uploaded_modality_eligibility_matrix(harness, make_harness):
    """Every admitted upload type returns its actual adapter and a scoped reason."""
    from test_magnetic_upload import magnetic_original, metadata as magnetic_metadata, options as magnetic_options
    from test_online_mt import NATIVE, upload_dataset as upload_edi_dataset
    from test_profile_jobs import owned_dataset as create_profile_dataset
    from test_waveform_service import index as index_waveform, pair as upload_waveform_pair
    from app.magnetic_contract import METHOD_ID as MAGNETIC_ID
    from app.mt_contract import M05_ID, M06_ID
    from app.profile_contract import M07_ID, M09_ID
    from app.waveform_contract import METHOD_ID as WAVEFORM_ID

    harness.account()

    def verdict(project_id: str, dataset_id: str) -> dict:
        response = harness.client.get(f"/api/projects/{project_id}/datasets/{dataset_id}/methods")
        assert response.status_code == 200, response.text
        result = response.json()
        rows = (*result["methods"], *result["unavailable"])
        ids = [row["method_id"] for row in rows]
        assert ids and len(ids) == len(set(ids))
        assert all(row["eligible"] is (row in result["methods"]) for row in rows)
        assert all(row.get("scope") for row in result["methods"])
        assert all(row.get("reason") and row.get("reason_fields")
                   for row in result["unavailable"])
        return result

    # Magnetic flight-line upload: valid source, closed host admission. It must
    # not fall back to gravity flag-QC.
    project = harness.project("Eligibility magnetic control")
    raw = magnetic_original()
    uploaded = harness.upload(project["id"], raw, magnetic_metadata(raw))
    assert uploaded.status_code == 201, uploaded.text
    created = harness.request("POST", f"/api/projects/{project['id']}/datasets", json={
        "asset_id": uploaded.json()["asset_id"], "magnetic_request": magnetic_options(),
    })
    assert created.status_code == 201, created.text
    result = verdict(project["id"], created.json()["dataset_id"])
    assert result["methods"] == []
    assert result["unavailable"] == [{
        "method_id": MAGNETIC_ID, "eligible": False, "lane": "pending_host_admission",
        "source_eligible": True,
        "reason": "The source-bound M03 dataset is ready; online execution remains closed until its worker and actual ML VPS resource admission are validated",
        "reason_fields": ["host.magnetic_online_admission"],
    }]

    # EDI bytes produce both compatible adapter records, explicitly closed
    # while MT host admission is disabled.
    project, _asset, dataset, _body = upload_edi_dataset(
        harness, NATIVE, station="ELIGIBILITY_NATIVE_CONTROL", count=24)
    result = verdict(project["id"], dataset["dataset_id"])
    assert result["methods"] == []
    assert {item["method_id"] for item in result["unavailable"]} == {M05_ID, M06_ID}
    assert all(item["lane"] == "pending_host_admission"
               and item["reason_fields"] == ["settings.mt_online_enabled", "host.actual_ml_vps_admission"]
               for item in result["unavailable"])

    # Supported profile grammars retain their specific inverse IDs and host
    # gate without enabling either job.
    for fmt, method_id in (("ert_ohm", M07_ID), ("traveltime_sgt", M09_ID)):
        project, _asset, dataset, _profile_metadata = create_profile_dataset(harness, method=fmt)
        result = verdict(project["id"], dataset["dataset_id"])
        assert result["methods"] == []
        assert result["unavailable"] == [{
            "method_id": method_id, "eligible": False, "lane": "pending_host_admission",
            "reason": "Use the complete local profile pipeline and result importer; actual host admission is not yet recorded",
            "reason_fields": ["host.profile_online_admission"],
        }]

    # Waveform resolves only to its native adapter and is controlled by its
    # verified native context.
    waveform_harness = make_harness()
    project, fixture, _xml, raw = upload_waveform_pair(waveform_harness)
    created = index_waveform(waveform_harness, project, fixture, raw)
    assert created.status_code == 201, created.text
    response = waveform_harness.client.get(
        f"/api/projects/{project['id']}/datasets/{created.json()['dataset_id']}/methods")
    assert response.status_code == 200, response.text
    result = response.json()
    rows = (*result["methods"], *result["unavailable"])
    assert [row["method_id"] for row in rows] == [WAVEFORM_ID]
    if result["methods"]:
        assert result["methods"][0]["eligible"] is True
        assert result["methods"][0]["scope"]
    else:
        assert result["unavailable"][0]["eligible"] is False
        assert result["unavailable"][0]["reason_fields"] == ["waveform_context.native_runtime"]
