"""Regression tests for the bilingual magnetic documentation inventory."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_magnetic_docs", ROOT / "scripts/check_magnetic_docs.py"
)
CHECK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECK
assert SPEC.loader is not None
SPEC.loader.exec_module(CHECK)


class TestMagneticDocs(unittest.TestCase):
    def test_current_wiki_and_course_cover_declared_source_contract(self):
        self.assertEqual(CHECK.audit(), [])

    def test_missing_bilingual_topic_and_local_link_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (
                "docs/methods/magnetic-survey/README.md",
                "docs/design/features/m04-survey-inversion/algorithms.md",
                "frontend/src/data/magnetic-survey-course.ts",
                "frontend/src/data/magnetic-course-derivations.ts",
                "frontend/src/data/magnetic-course-citations.ts",
                "frontend/src/components/MagneticTheoryCourse.tsx",
            ):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                source = (ROOT / relative).read_text(encoding="utf-8")
                if relative.endswith("README.md"):
                    source = source.replace("Español", "Spanish")
                    source += "\n[missing](../../does-not-exist.md)\n"
                target.write_text(source, encoding="utf-8")
            for relative in (
                "docs/methods/magnetic-survey/README.md",
                "docs/design/features/m04-survey-inversion/algorithms.md",
            ):
                source_path = ROOT / relative
                for link in CHECK.LOCAL_LINK.findall(source_path.read_text(encoding="utf-8")):
                    if link.startswith(("mailto:", "data:")):
                        continue
                    linked = (source_path.parent / link.split("#", 1)[0]).resolve()
                    if linked.is_file():
                        target = root / linked.relative_to(ROOT)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(linked.read_bytes())
            findings = CHECK.audit(root)
        self.assertTrue(any("Spanish topic marker" in item for item in findings))
        self.assertTrue(any("local link is missing" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
