"""A reusable evaluation study must not masquerade as a forecasting proposal."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


_HELPER_PATH = Path(__file__).parent / "adversarial" / "test_manuscript_depth.py"
_SPEC = importlib.util.spec_from_file_location("geophysics_manuscript_depth_fixtures", _HELPER_PATH)
_HELPERS = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _HELPERS
_SPEC.loader.exec_module(_HELPERS)

REPORT = _HELPERS.report_tex()
PAPER = _HELPERS.paper_tex()
SDD = _HELPERS.SDD


def tree(root: Path, manuscripts: list[dict], *, sdd: str = SDD) -> Path:
    _HELPERS.product(root, sdd=sdd)
    manifest = json.loads((root / "product.json").read_text(encoding="utf-8"))
    for entry in manuscripts:
        manifest_entry = {key: entry[key] for key in ("kind", "title")}
        if manifest_entry not in manifest["manuscripts"]:
            manifest["manuscripts"].append(manifest_entry)
    (root / "product.json").write_text(json.dumps(manifest), encoding="utf-8")
    for entry in manuscripts:
        folder = root / "manuscripts" / entry.get("slug", "research-study")
        folder.mkdir(parents=True)
        (folder / "main.tex").write_text(PAPER, encoding="utf-8")
        claims = entry.get("claims", {claim: "sec:proposed" for claim in entry.get("covers", [])})
        (folder / "coverage.json").write_text(json.dumps({"kind": "manuscript",
            "title_support": ["tab:p0"], "claims": claims}), encoding="utf-8")
    return root


def run(root: Path) -> subprocess.CompletedProcess:
    script = Path(__file__).parents[1] / "scripts" / "check_manuscript_depth.py"
    return subprocess.run([sys.executable, str(script), str(root)], capture_output=True, text=True, timeout=30)


def test_novel_protocol_and_dataset_have_their_own_coverage(tmp_path):
    sdd = SDD + "\n## Novel contributions\n\nNC-1: a replay protocol.\nNC-2: a dataset.\n"
    study = {"kind": "manuscript", "title": "A reusable evaluation study", "slug": "reusable-evaluation-study",
        "claims": {"NC-1": "sec:protocol", "NC-2": "sec:dataset"}}
    root = tree(tmp_path, [study], sdd=sdd)
    source = PAPER.replace("\\end{document}",
        _HELPERS.sec("Protocol", _HELPERS.prose(1600) + _HELPERS.eqs(6, "protocol"), "sec:protocol")
        + _HELPERS.sec("Dataset", _HELPERS.prose(1600) + _HELPERS.eqs(6, "dataset"), "sec:dataset")
        + "\\end{document}")
    folder = root / "manuscripts" / "reusable-evaluation-study"
    (folder / "main.tex").write_text(source, encoding="utf-8")
    result = run(root)
    assert result.returncode == 0, result.stdout


def test_adversarial_novel_id_from_an_unrelated_section_is_not_a_declaration(tmp_path):
    sdd = SDD + "\n## Other notes\n\nNC-1 is discussed but not declared here.\n"
    result = run(tree(tmp_path, [{"kind": "manuscript", "title": "A reusable evaluation study", "covers": ["NC-1"]}], sdd=sdd))
    assert result.returncode == 1 and "Novel contributions" in result.stdout


def test_adversarial_unknown_novel_id_is_refused(tmp_path):
    result = run(tree(tmp_path, [{"kind": "manuscript", "title": "A reusable evaluation study", "covers": ["NC-9"]}]))
    assert result.returncode == 1 and "NC-9" in result.stdout


def test_adversarial_fenced_novel_id_is_not_a_declaration(tmp_path):
    sdd = SDD + "\n## Novel contributions\n\n```text\nNC-1: example only.\n```\n"
    result = run(tree(tmp_path, [{"kind": "manuscript", "title": "A reusable evaluation study", "covers": ["NC-1"]}], sdd=sdd))
    assert result.returncode == 1 and "NC-1" in result.stdout


def test_adversarial_method_id_in_novel_section_does_not_authorize_a_method(tmp_path):
    sdd = SDD + "\n## Novel contributions\n\nBS-9: deliberately misplaced.\n"
    result = run(tree(tmp_path, [{"kind": "manuscript", "title": "A reusable evaluation study", "covers": ["BS-9"]}], sdd=sdd))
    assert result.returncode == 1 and "BS-9" in result.stdout
