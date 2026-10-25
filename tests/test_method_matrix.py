"""Structural contract tests for the fail-closed M01-M13 method audit."""

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_method_matrix", ROOT / "scripts/check_method_matrix.py")
CHECK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECK
SPEC.loader.exec_module(CHECK)


class TestMethodMatrix(unittest.TestCase):
    def test_repository_matrix_lists_all_thirteen_and_reports_missing_gates(self):
        rows = CHECK.audit()
        self.assertEqual(tuple(row.method_id for row in rows), CHECK.EXPECTED_METHODS)
        self.assertTrue(any(not row.gate_exists for row in rows))
        output = io.StringIO()
        with redirect_stdout(output):
            status = CHECK.main([])
        self.assertEqual(status, 1)
        self.assertIn("scientific_acceptance=false", output.getvalue())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(CHECK.main(["--report-only"]), 0)

    def test_complete_structure_is_not_labelled_scientific_acceptance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tests/numerics").mkdir(parents=True)
            (root / "frontend/e2e").mkdir(parents=True)
            (root / "tests/numerics/gates.py").write_text("def gate():\n    return None\n", encoding="utf-8")
            (root / "frontend/e2e/gate.spec.ts").write_text("// fixture gate file\n", encoding="utf-8")
            lines = ["## 4. Method ladder and acceptance oracle", "",
                     "| ID | Scientific workflow and release acceptance | Named gate |",
                     "| --- | --- | --- |"]
            lines.extend(f"| M{i:02} | workflow {i} | tests/numerics/gates.py::gate |" for i in range(1, 13))
            lines.append("| M13 | browser workflow | tests/numerics/gates.py::gate and frontend/e2e/gate.spec.ts |")
            sdd = root / "SDD.md"
            sdd.write_text("\n".join(lines), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                status = CHECK.main(["--sdd", str(sdd), "--root", str(root), "--json"])
            self.assertEqual(status, 0)
            self.assertIn('"scientific_acceptance": false', output.getvalue())

    def test_missing_method_row_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lines = ["## 4. Method ladder and acceptance oracle", "",
                     "| ID | Scientific workflow and release acceptance | Named gate |",
                     "| --- | --- | --- |"]
            lines.extend(f"| M{i:02} | workflow {i} | tests/numerics/gates.py::gate |" for i in range(1, 13))
            sdd = root / "SDD.md"
            sdd.write_text("\n".join(lines), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly M01-M13"):
                CHECK.audit(sdd, root)


if __name__ == "__main__":
    unittest.main()
