"""Local positive/negative controls; CI runs only the cheap source guard."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("single_origin_guard", ROOT / "scripts/check_single_origin.py")
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class SingleOriginTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="geophysics-origin-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for relative in ("frontend/vite.config.ts", "frontend/package.json",
                         "frontend/src/lib/deployment.ts", "README.md", "deploy/README.md", "deploy/deploy.ps1"):
            self.write(relative, (ROOT / relative).read_text(encoding="utf-8"))
        self.write(".github/workflows/ci.yml", "name: CI\njobs: {}\n")

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_current_source(self) -> None:
        self.assertEqual(GUARD.check(ROOT), [])
        self.assertEqual(GUARD.check(self.root), [])

    def test_retired_paths(self) -> None:
        for relative in GUARD.FORBIDDEN_FILES:
            with self.subTest(path=relative):
                self.write(relative, "retired")
                self.assertTrue(GUARD.check(self.root))
                (self.root / relative).unlink()

    def test_renamed_publish_workflow(self) -> None:
        for content in ("uses: actions/deploy-pages@v4", "uses: actions/upload-pages-artifact@v3",
                        "uses: actions/configure-pages@v5", "permissions:\n  pages: write",
                        "environment:\n  name: github-pages"):
            with self.subTest(content=content):
                self.write(".github/workflows/renamed.yml", content)
                self.assertTrue(GUARD.check(self.root))

    def test_relative_project_and_conditional_base(self) -> None:
        for base in ("'./'", "'/CAOS_Geophysics/'", "mode === 'single-origin' ? '/' : './'"):
            with self.subTest(base=base):
                self.write("frontend/vite.config.ts", f"export default {{ base: {base}, }};")
                self.assertTrue(GUARD.check(self.root))

    def test_missing_sources(self) -> None:
        (self.root / "frontend/vite.config.ts").unlink()
        self.assertTrue(GUARD.check(self.root))

    def test_runtime_fallback(self) -> None:
        self.write("frontend/src/lib/deployment.ts", 'export type DeploymentMode = "legacy" | "single-origin";')
        self.assertTrue(GUARD.check(self.root))

    def test_alternate_build(self) -> None:
        path = self.root / "frontend/package.json"
        package = json.loads(path.read_text(encoding="utf-8"))
        package["scripts"]["build:pages"] = "vite build --base ./"
        self.write("frontend/package.json", json.dumps(package))
        self.assertTrue(GUARD.check(self.root))

    def test_active_secondary_link_but_historical_receipts_allowed(self) -> None:
        self.write("docs/validation/historical.md", "https://fsantibanezleal.github.io/CAOS_Geophysics/")
        self.assertEqual(GUARD.check(self.root), [])
        self.write("README.md", "https://fsantibanezleal.github.io/CAOS_Geophysics/")
        self.assertTrue(GUARD.check(self.root))

    def test_legacy_uploader_cannot_bypass_acceptance(self) -> None:
        uploader = (self.root / "deploy/deploy.ps1").read_text(encoding="utf-8")
        self.write("deploy/deploy.ps1", uploader.replace("--require-release", ""))
        self.assertTrue(GUARD.check(self.root))

    def test_built_assets_and_deep_link_duplicates(self) -> None:
        self.write("frontend/dist/index.html", '<script src="/assets/main-abc.js"></script>')
        self.assertEqual(GUARD.check(self.root, built=True), [])
        self.write("frontend/dist/benchmark/assets/main-abc.js", "duplicate")
        self.assertTrue(GUARD.check(self.root, built=True))

    def test_built_relative_and_secondary_hostname(self) -> None:
        self.write("frontend/dist/index.html", '<script src="./assets/main-abc.js"></script>')
        self.assertTrue(GUARD.check(self.root, built=True))
        self.write("frontend/dist/index.html", '<script src="/assets/main-abc.js"></script>')
        self.write("frontend/dist/CNAME", "second.example.org")
        self.assertTrue(GUARD.check(self.root, built=True))


if __name__ == "__main__":
    unittest.main()
