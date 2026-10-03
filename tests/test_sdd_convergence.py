"""Adversarial, dependency-free checks of the product acceptance ledger."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sdd_convergence", ROOT / "scripts/check_sdd_convergence.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class TestConvergence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "scripts/gate.py").write_text("def main():\n    return 0\n", encoding="utf-8")
        self.sdd = self.root / "docs/SDD.md"
        self.sdd.write_text(
            "## 9. EARS requirements and named failing gates\n\n"
            "R-001 THE product SHALL preserve data. Gate: scripts/gate.py::main.\n\n"
            "R-002 WHEN data changes, THE product SHALL evaluate it. Gate: scripts/gate.py::main.\n\n"
            "## 10. Other material\nR-900 not a product declaration\n", encoding="utf-8",
        )
        self.ledger = {
            "schema": "geophysics.sdd-convergence/v1", "sdd_path": "docs/SDD.md",
            "sdd_sha256": CHECK.digest(self.sdd), "assessed_revision": "a" * 40,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
            "release": {"replacement_accepted": False, "class": "legacy-static",
                        "application_origins": ["https://one.example", "https://two.example"],
                        "pages_publishes_application": True},
            "requirements": [
                {"id": key, "verdict": "unresolved", "declared_gate": value,
                 "note": "Local tests do not imply product release.", "evidence": [], "receipts": []}
                for key, value in CHECK.declarations(self.sdd).items()
            ],
        }

    def measured(self):
        """Construct isolated test receipts, never production acceptance evidence."""
        for record in self.ledger["requirements"]:
            output = self.root / f"docs/{record['id']}-output.txt"
            output.write_text("fixture-only measured output\n", encoding="utf-8")
            path = self.root / f"docs/{record['id']}-receipt.json"
            path.write_text(json.dumps({
                "schema": "geophysics.gate-receipt/v1", "requirement": record["id"],
                "gate": "scripts/gate.py::main", "verdict": "pass",
                "source_revision": self.ledger["assessed_revision"], "command": ["python", "scripts/gate.py"],
                "measured_at": self.ledger["assessed_at"],
                "gate_sha256": CHECK.digest(self.root / "scripts/gate.py"),
                "outputs": [{"path": output.relative_to(self.root).as_posix(), "sha256": CHECK.digest(output)}],
            }), encoding="utf-8")
            record["verdict"] = "pass"
            record["receipts"] = [{"path": path.relative_to(self.root).as_posix(), "sha256": CHECK.digest(path)}]
        self.ledger["release"] = {
            "replacement_accepted": True, "class": "vps-service", "application_origins": ["https://one.example"],
            "pages_publishes_application": False,
        }

    def test_requirement_coverage_and_gate_drift(self):
        self.assertEqual(CHECK.validate(self.root, self.ledger)["unresolved"], 2)
        for modification in ("missing", "duplicate", "unknown", "gate"):
            ledger = copy.deepcopy(self.ledger)
            if modification == "missing":
                ledger["requirements"].pop()
            elif modification == "duplicate":
                ledger["requirements"].append(ledger["requirements"][0])
            elif modification == "unknown":
                ledger["requirements"][0]["id"] = "R-999"
            else:
                ledger["requirements"][0]["declared_gate"] = "scripts/gate.py::other."
            with self.assertRaises(CHECK.LedgerError, msg=modification):
                CHECK.validate(self.root, ledger)
        self.sdd.write_text(self.sdd.read_text() + "\nchanged\n", encoding="utf-8")
        with self.assertRaisesRegex(CHECK.LedgerError, "hash mismatch"):
            CHECK.validate(self.root, self.ledger)

    def test_pass_requires_checked_evidence(self):
        self.ledger["requirements"][0]["verdict"] = "pass"
        with self.assertRaisesRegex(CHECK.LedgerError, "lacks every"):
            CHECK.validate(self.root, self.ledger)
        self.measured()
        self.assertEqual(CHECK.validate(self.root, self.ledger, require_release=True)["pass"], 2)
        self.ledger["assessed_revision"] = "b" * 40
        with self.assertRaisesRegex(CHECK.LedgerError, "invalid measured receipt"):
            CHECK.validate(self.root, self.ledger)

    def test_release_rejects_partial_and_duplicate_deployment(self):
        with self.assertRaisesRegex(CHECK.LedgerError, "not accepted"):
            CHECK.validate(self.root, self.ledger, require_release=True)
        for verdict in ("fail", "unresolved", "ineligible"):
            self.measured()
            self.ledger["requirements"][0]["verdict"] = verdict
            with self.assertRaises(CHECK.LedgerError):
                CHECK.validate(self.root, self.ledger, require_release=True)
        self.measured()
        for value in (
            {"application_origins": ["https://one.example", "https://two.example"]},
            {"pages_publishes_application": True}, {"class": "github-pages"}, {"replacement_accepted": False},
            {"application_origins": ["https://one.example/path"]},
        ):
            ledger = copy.deepcopy(self.ledger)
            ledger["release"].update(value)
            with self.assertRaises(CHECK.LedgerError):
                CHECK.validate(self.root, ledger, require_release=True)

    def test_evidence_integrity_and_gate_existence(self):
        self.measured()
        CHECK.validate(self.root, self.ledger)
        (self.root / "scripts/gate.py").write_text("def other():\n    return 0\n", encoding="utf-8")
        with self.assertRaisesRegex(CHECK.LedgerError, "missing executable"):
            CHECK.validate(self.root, self.ledger)
        (self.root / "scripts/gate.py").write_text("def main():\n    return 1\n", encoding="utf-8")
        with self.assertRaisesRegex(CHECK.LedgerError, "hash mismatch"):
            CHECK.validate(self.root, self.ledger)
        for path in ("../outside", "/etc/passwd", "C:/Windows/file", "docs\\file", "missing.json"):
            with self.assertRaises(CHECK.LedgerError, msg=path):
                CHECK.checked_path(self.root, path)

    def test_receipt_tampering_and_measured_output_tampering(self):
        self.measured()
        path = self.root / "docs/R-001-output.txt"
        path.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(CHECK.LedgerError, "hash mismatch"):
            CHECK.validate(self.root, self.ledger)
        self.measured()
        receipt = self.root / "docs/R-001-receipt.json"
        receipt.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(CHECK.LedgerError, "hash mismatch"):
            CHECK.validate(self.root, self.ledger)

    def test_strict_json_and_unparsed_requirements(self):
        path = self.root / "docs/test.json"
        for content in ('{"x":1,"x":2}', '{"x":NaN}', '[]'):
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(CHECK.LedgerError):
                CHECK.strict_json(path)
        self.sdd.write_text("## 9. EARS requirements and named failing gates\nR-001 THE system SHALL work.\n", encoding="utf-8")
        with self.assertRaisesRegex(CHECK.LedgerError, "unparsed"):
            CHECK.declarations(self.sdd)

    def test_named_artifact_cannot_be_replaced_by_a_build_receipt(self):
        self.measured()
        self.sdd.write_text(self.sdd.read_text().replace(
            "Gate: scripts/gate.py::main.", "Gate: scripts/gate.py::main and docs/evaluation.json.", 1,
        ), encoding="utf-8")
        self.ledger["sdd_sha256"] = CHECK.digest(self.sdd)
        self.ledger["requirements"][0]["declared_gate"] = CHECK.declarations(self.sdd)["R-001"]
        with self.assertRaisesRegex(CHECK.LedgerError, "lacks every named evidence artifact"):
            CHECK.validate(self.root, self.ledger)
        artifact = self.root / "docs/evaluation.json"
        artifact.write_text('{"fixture":true}', encoding="utf-8")
        self.ledger["requirements"][0]["evidence"] = [{"path": "docs/evaluation.json", "sha256": CHECK.digest(artifact)}]
        CHECK.validate(self.root, self.ledger)

    def test_ledger_self_reference_has_no_hash_fixed_point(self):
        self.measured()
        self.sdd.write_text(self.sdd.read_text().replace("R-001", "R-018").replace(
            "Gate: scripts/gate.py::main.", "Gate: scripts/gate.py::main and docs/design/convergence.json.", 1,
        ), encoding="utf-8")
        self.ledger["sdd_sha256"] = CHECK.digest(self.sdd)
        record = self.ledger["requirements"][0]
        record["id"] = "R-018"
        record["declared_gate"] = CHECK.declarations(self.sdd)["R-018"]
        path = self.root / record["receipts"][0]["path"]
        receipt = CHECK.strict_json(path)
        receipt["requirement"] = "R-018"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        record["receipts"][0]["sha256"] = CHECK.digest(path)
        CHECK.validate(self.root, self.ledger)

    def test_current_product_has_nineteen_distinct_declarations(self):
        values = CHECK.declarations(ROOT / "docs/design/SDD.md")
        self.assertEqual(set(values), {f"R-{i:03d}" for i in range(1, 20)})
        methods = CHECK.method_declarations(ROOT / "docs/design/SDD.md")
        self.assertEqual(set(methods), {f"M{i:02d}" for i in range(1, 14)})

    def test_incomplete_method_table_cannot_satisfy_full_method_acceptance(self):
        self.sdd.write_text("| M01 | A correction | tests/gravity.py::test_correction |\n", encoding="utf-8")
        with self.assertRaisesRegex(CHECK.LedgerError, "not complete"):
            CHECK.method_declarations(self.sdd)


if __name__ == "__main__":
    unittest.main()
