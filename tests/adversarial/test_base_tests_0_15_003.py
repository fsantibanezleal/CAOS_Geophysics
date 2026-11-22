"""Plant the 0.15.003 base-test adoption defect: shared frontend tests identify themselves as verbatim base tests,
and the gate-plan test reads this product's own route declaration instead of embedding example story routes."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from planting import NODE, NODE_MODULES

ROOT = Path(__file__).resolve().parents[2]
MARK = "A product takes this file verbatim"
# A base script is a frontend/scripts/*.mjs that is not a product module (*.product.mjs, 0.15.005): a test of the latter is the product's.
SCRIPT_IMPORT = re.compile(r"""(?:from\s+|new URL\(\s*)['"](?:\.\./)+scripts/[^'"]+(?<!\.product)\.mjs['"]""")
needs_web = pytest.mark.skipif(NODE is None or not (NODE_MODULES / "@fasl-work").is_dir(),
                               reason="needs node and `npm ci` in frontend/")


def base_script_tests(root: Path) -> list[Path]:
    src = root / "frontend" / "src"
    # `src/test` is the product-owned suite; its contracts may intentionally exercise a shared build helper.
    # Base tests live beside shared library code or at the src root and carry the copy-verbatim marker.
    return sorted(p for p in src.rglob("*.test.ts*")
                  if p.relative_to(src).parts[0] != "test" and SCRIPT_IMPORT.search(p.read_text(encoding="utf-8")))


def test_every_frontend_test_of_a_base_script_says_it_is_taken_verbatim() -> None:
    found = base_script_tests(ROOT)
    rels = [p.relative_to(ROOT).as_posix() for p in found]
    assert {"frontend/src/gate-script.test.ts", "frontend/src/lib/declared.test.ts",
            "frontend/src/lib/copy-data.test.ts"} <= set(rels), rels
    unmarked = [r for p, r in zip(found, rels) if MARK not in p.read_text(encoding="utf-8")]
    assert not unmarked, f"a base test under frontend/src that does not say it is taken verbatim: {unmarked}"


@needs_web
def test_the_gate_runner_test_passes_for_this_products_declared_story() -> None:
    r = subprocess.run([NODE, str(NODE_MODULES / "vitest" / "vitest.mjs"), "run", "src/gate-script.test.ts"],
                       cwd=ROOT / "frontend", capture_output=True, encoding="utf-8", errors="replace", timeout=900)
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
    assert "failed" not in r.stdout.split("Test Files")[-1].split("\n")[0], r.stdout[-2000:]
