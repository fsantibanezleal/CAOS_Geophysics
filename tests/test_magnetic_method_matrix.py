"""Tests for the fail-closed M04 requirement and gate inventory."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_magnetic_method_matrix", ROOT / "scripts/check_magnetic_method_matrix.py"
)
CHECK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECK
SPEC.loader.exec_module(CHECK)


class TestMagneticMethodMatrix(unittest.TestCase):
    def test_repository_inventory_never_converts_gate_presence_to_acceptance(self):
        records = CHECK.audit()
        self.assertEqual(tuple(record.requirement_id for record in records), CHECK.REQUIREMENT_IDS)
        output = io.StringIO()
        with redirect_stdout(output):
            status = CHECK.main(["--json", "--report-only"])
        self.assertEqual(status, 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["requirement_count"], 20)
        self.assertIs(report["scientific_acceptance"], False)
        self.assertIs(report["field_acceptance"], False)
        self.assertFalse(report["structural_inventory_complete"])

    def test_default_mode_fails_when_declared_gates_are_incomplete(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(CHECK.main([]), 1)

    def test_current_matrix_preserves_missing_inverse_as_a_missing_gate(self):
        record = next(item for item in CHECK.audit() if item.requirement_id == "R-407")
        self.assertFalse(record.gate_exists)
        self.assertIn("test_accepted_optimizer_binding", record.issue)

    def test_malformed_and_duplicate_gate_declarations_fail_closed(self):
        sample = """R-401 requirement
Implementation: data-pipeline/magnetic_survey.py
Gate: tests/data/test_magnetic_survey.py::test_original_inventory_and_masks
"""
        with self.assertRaisesRegex(ValueError, "R-401..R-420"):
            CHECK._parse_requirements(sample)
        with self.assertRaisesRegex(ValueError, "invalid M04 gate reference"):
            CHECK._gate_parts("tests/data/test_magnetic_survey.py::")
        with self.assertRaisesRegex(ValueError, "escapes audit root"):
            CHECK._repo_path(ROOT, "../outside.py")


if __name__ == "__main__":
    unittest.main()
