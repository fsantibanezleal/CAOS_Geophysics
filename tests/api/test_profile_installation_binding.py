"""Independent prelaunch authority controls, not scientific or host proof."""
from copy import deepcopy

import pytest

from app.profile_execution import validate_terminal, attach_execution, validate_execution
from app.processing_contract import canonical_bytes
from test_profile_execution_receipt import execution_fixture


def binding(receipt):
    return {key:deepcopy(receipt[key]) for key in (
        "configuration_sha256","python_sha256","environment_sha256","invocation_sha256","source_hashes")}


@pytest.mark.parametrize("key",["configuration_sha256","python_sha256","environment_sha256","invocation_sha256"])
def test_unrelated_installation_cannot_classify_terminal_cancellation(key):
    _,receipt,job,stage = execution_fixture()
    expected = binding(receipt)
    receipt[key] = "9"*64
    with pytest.raises(ValueError):
        validate_terminal(receipt,job,stage,expected)


def test_entire_source_closure_is_bound_not_only_numerical_modules():
    producer,receipt,job,stage = execution_fixture()
    expected = binding(receipt)
    receipt["source_hashes"]["scripts/profile_linux_child.py"] = "9"*64
    with pytest.raises(ValueError):
        attach_execution(canonical_bytes(producer),receipt,job,stage,expected)


def test_historical_authority_survives_without_adopting_a_current_installation():
    producer,receipt,job,stage = execution_fixture()
    expected = binding(receipt)
    result = attach_execution(canonical_bytes(producer),receipt,job,stage,expected)
    assert result["linux_installation"] == expected
    validate_execution(result,job)
    expected["configuration_sha256"] = "9"*64
    assert result["linux_installation"]["configuration_sha256"] != expected["configuration_sha256"]


@pytest.mark.parametrize("mutation",[
    lambda result:result.pop("linux_installation"),
    lambda result:result.pop("linux_execution"),
    lambda result:result["linux_installation"].update(extra="unknown"),
    lambda result:result["linux_installation"].update(invocation_sha256="9"*64),
    lambda result:result["linux_installation"]["source_hashes"].update({"scripts/profile_linux_child.py":"9"*64}),
])
def test_missing_partial_or_altered_historical_authority_refuses_reads(mutation):
    producer,receipt,job,stage = execution_fixture()
    result = attach_execution(canonical_bytes(producer),receipt,job,stage,binding(receipt))
    mutation(result)
    with pytest.raises(ValueError):
        validate_execution(result,job)
