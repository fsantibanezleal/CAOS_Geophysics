#!/usr/bin/env python3
"""Check that every SDD method has substantive, implementation-linked wiki coverage.

This is a structural documentation gate only. It cannot establish scientific
correctness, source rights, completeness of the teaching material, or release
acceptance; reviewers must assess those separately.
"""

from __future__ import annotations

import re
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = {
    "docs/wiki/methods/m01-m06.md": range(1, 7),
    "docs/wiki/methods/m07-m13.md": range(7, 14),
}
SPANISH_CHAPTERS = {
    "docs/wiki/methods/m01-m06.es.md": range(1, 7),
    "docs/wiki/methods/m07-m13.es.md": range(7, 14),
}
TRANSLATION_PAIRS = (
    ("docs/wiki/methods/m01-m06.md", "docs/wiki/methods/m01-m06.es.md"),
    ("docs/wiki/methods/m07-m13.md", "docs/wiki/methods/m07-m13.es.md"),
)
METHOD_COVERAGE = "docs/validation/source-content-coverage.json"
SOURCE_REVIEW = "docs/validation/source-to-content-review.md"
NOTEBOOK_ROOTS = ("notebooks/en", "notebooks/es")
REQUIRED_TERMS = {
    "equations": (r"(?:\\\[|\$\$)", r"(?:\\\]|\$\$)"),
    "assumptions and limits": (r"assumption", r"limit"),
    "reproduction status": (r"reproduction|reproduce", r"unavailable|reproduc"),
    "references": (r"references|primary sources", r"https?://|doi\.org"),
}
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
DISPLAY_MATH = re.compile(r"\$\$.*?\$\$|\\\[.*?\\\]", re.S)
FENCED_CODE = re.compile(r"(?:```|~~~).*?(?:```|~~~)", re.S)
INLINE_CODE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
NUMBER_TOKEN = re.compile(r"(?<![A-Za-z])(?:\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)(?![A-Za-z])")
INLINE_CODE_PATH = re.compile(
    r"(?<![\w/.-])(?:data-pipeline|app|frontend/src|tests|scripts)/"
    r"[A-Za-z0-9_./-]+(?:\.tsx|\.ts|\.mjs|\.py|\.json|\.ps1|\.md)"
)
REPOSITORY_PATH = re.compile(
    r"(?<![\w/.-])((?:data-pipeline|app|frontend/src|tests|scripts)/"
    r"[A-Za-z0-9_./-]+\.(?:tsx|ts|mjs|py|json|ps1|md))"
)


def fail(message: str) -> int:
    print(f"DOCS MATRIX FAIL: {message}", file=sys.stderr)
    return 1


def check_source_content_coverage(errors: list[str]) -> tuple[int, int]:
    """Bind the human source-to-content review to the current methods and notebook files."""
    manifest_path = ROOT / METHOD_COVERAGE
    review_path = ROOT / SOURCE_REVIEW
    if not manifest_path.is_file() or not review_path.is_file():
        errors.append(f"missing source-to-content review or coverage manifest: {METHOD_COVERAGE}, {SOURCE_REVIEW}")
        return 0, 0
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid source-to-content coverage manifest: {exc}")
        return 0, 0
    if manifest.get("schema") != "caos.geophysics.source-content-coverage/v1":
        errors.append("source-to-content manifest has an unsupported schema")
    entries = manifest.get("notebooks")
    if not isinstance(entries, list):
        errors.append("source-to-content manifest notebooks must be a list")
        return 0, 0

    actual_en = {p.relative_to(ROOT).as_posix() for p in (ROOT / NOTEBOOK_ROOTS[0]).rglob("*.ipynb")}
    actual_es = {p.relative_to(ROOT).as_posix() for p in (ROOT / NOTEBOOK_ROOTS[1]).rglob("*.ipynb")}
    expected_en = {p.replace("notebooks/es/", "notebooks/en/") for p in actual_es}
    if actual_en != expected_en:
        errors.append("current English and Spanish notebook paths are not mirrored")
    seen_paths: set[str] = set()
    seen_methods: set[str] = set()
    review = review_path.read_text(encoding="utf-8")
    for target in LINK.findall(review):
        if target.startswith(("https://", "http://", "mailto:", "#")):
            continue
        local_target = target.split("#", 1)[0]
        if local_target and not (review_path.parent / local_target).resolve().is_file():
            errors.append(f"{SOURCE_REVIEW}: broken local link {target}")
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("source-to-content notebook entry is not an object")
            continue
        en, es = entry.get("en"), entry.get("es")
        if not isinstance(en, str) or not isinstance(es, str):
            errors.append("source-to-content notebook entry lacks EN/ES paths")
            continue
        if en in seen_paths or es in seen_paths:
            errors.append(f"duplicate notebook in source-to-content manifest: {en} / {es}")
        seen_paths.update((en, es))
        if en not in actual_en or es not in actual_es or en.replace("notebooks/en/", "notebooks/es/") != es:
            errors.append(f"manifest notebook pair is missing or not mirrored: {en} / {es}")
            continue
        for relative in (en, es):
            try:
                notebook = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"cannot read manifest notebook {relative}: {exc}")
                continue
            caos = notebook.get("metadata", {}).get("caos", {})
            if relative == en:
                if entry.get("title") != caos.get("title"):
                    errors.append(f"manifest title is stale for {en}")
                if entry.get("sources") != caos.get("sources"):
                    errors.append(f"manifest source URLs are stale for {en}")
                ids = entry.get("methods")
                if not isinstance(ids, list) or any(not isinstance(mid, str) or not re.fullmatch(r"M\d{2}", mid) for mid in ids):
                    errors.append(f"invalid method associations for {en}")
                    continue
                seen_methods.update(ids)
                if en not in review or es not in review:
                    errors.append(f"source-to-content review does not list notebook pair {en} / {es}")
                if en not in review or caos.get("title", "") not in review:
                    errors.append(f"source-to-content review does not identify current notebook title: {en}")
                if not isinstance(entry.get("content_scope"), str) or len(entry["content_scope"].split()) < 4:
                    errors.append(f"source-to-content review lacks a bounded content scope for {en}")
                elif entry["content_scope"] not in review:
                    errors.append(f"source-to-content review is missing the declared scope for {en}")
                for source in entry.get("sources", []):
                    if not isinstance(source, str) or source not in review:
                        errors.append(f"source-to-content review is missing a declared citation URL for {en}: {source}")
            if caos.get("language") != ("en" if relative == en else "es"):
                errors.append(f"notebook language metadata disagrees with path: {relative}")
    expected_paths = actual_en | actual_es
    if seen_paths != expected_paths:
        errors.append(
            "source-to-content manifest inventory differs from current notebooks: "
            f"missing={sorted(expected_paths - seen_paths)}, extra={sorted(seen_paths - expected_paths)}"
        )
    if len(actual_en) != 28 or len(actual_es) != 28:
        errors.append(f"expected the reviewed 28 EN + 28 ES notebook set, found {len(actual_en)} + {len(actual_es)}")

    method_entries = manifest.get("methods")
    expected_methods = {f"M{i:02d}" for i in range(1, 14)}
    if not isinstance(method_entries, list):
        errors.append("source-to-content manifest methods must be a list")
        method_entries = []
    method_ids: list[str] = []
    for method in method_entries:
        if not isinstance(method, dict):
            errors.append("source-to-content method entry is not an object")
            continue
        method_id = method.get("id")
        method_ids.append(method_id)
        if method_id not in expected_methods:
            errors.append(f"unexpected source-to-content method ID: {method_id}")
            continue
        en_chapter = method.get("wiki_en")
        es_chapter = method.get("wiki_es")
        if not isinstance(en_chapter, str) or not isinstance(es_chapter, str):
            errors.append(f"{method_id}: missing bilingual wiki anchors")
            continue
        en_target = "../wiki/methods/" + en_chapter.removeprefix("docs/wiki/methods/")
        es_target = "../wiki/methods/" + es_chapter.removeprefix("docs/wiki/methods/")
        if en_target not in review or es_target not in review:
            errors.append(f"source-to-content review does not link both wiki chapters for {method_id}")
        associated = [entry for entry in entries if method_id in entry.get("methods", [])]
        if not associated:
            errors.append(f"{method_id}: no notebook lesson is associated in the review manifest")
        for chapter in (en_chapter.split("#", 1)[0], es_chapter.split("#", 1)[0]):
            path = ROOT / chapter
            heading = None if not path.is_file() else re.search(rf"^(## {method_id}\. .+)$", path.read_text(encoding="utf-8"), re.M)
            if heading is None:
                errors.append(f"{method_id}: manifest points to a missing method heading in {chapter}")
                continue
            slug = unicodedata.normalize("NFKD", heading[1]).encode("ascii", "ignore").decode().lower()
            slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
            if chapter + "#" + slug not in (en_chapter, es_chapter):
                errors.append(f"{method_id}: manifest heading anchor does not match {chapter}")
    if len(method_ids) != len(set(method_ids)) or set(method_ids) != expected_methods:
        errors.append(f"method review inventory is {sorted(set(method_ids))}, expected M01-M13 exactly once")
    if not expected_methods.issubset(seen_methods):
        errors.append(f"notebook method associations do not cover: {sorted(expected_methods - seen_methods)}")

    return len(actual_en) + len(actual_es), len(method_ids)


def main() -> int:
    errors: list[str] = []
    covered: set[int] = set()
    for relative, expected_ids in CHAPTERS.items():
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing chapter: {relative}")
            continue
        content = path.read_text(encoding="utf-8")
        chapter_ids = [int(value) for value in re.findall(r"^## M(\d{2})\.", content, re.M)]
        if chapter_ids != list(expected_ids):
            errors.append(f"{relative}: expected method headings {list(expected_ids)}, found {chapter_ids}")
        for method_id in chapter_ids:
            if method_id in covered:
                errors.append(f"M{method_id:02d}: appears in more than one chapter")
            covered.add(method_id)
        for label, patterns in REQUIRED_TERMS.items():
            if not all(re.search(pattern, content, re.I) for pattern in patterns):
                errors.append(f"{relative}: missing structural evidence for {label}")
        normalized_content = content.replace("\\", "/")
        sections = re.split(r"(?=^## M\d{2}\.)", normalized_content, flags=re.M)
        for section in sections:
            heading = re.match(r"^## M(\d{2})\.", section)
            if not heading:
                continue
            method_id = int(heading[1])
            refs = set(REPOSITORY_PATH.findall(section))
            missing = [ref for ref in refs if not (ROOT / ref).is_file()]
            if missing:
                missing = [
                    ref for ref in missing
                    if not any(
                        re.search(r"planned|absent|does not exist|not found", section[max(0, match.start() - 120):match.end() + 180], re.I)
                        for match in re.finditer(re.escape(ref), section)
                    )
                ]
            if missing:
                errors.append(f"M{method_id:02d}: implementation references missing paths: {sorted(missing)}")
            if not any(ref.startswith(("data-pipeline/", "app/", "frontend/src/", "scripts/")) for ref in refs):
                errors.append(f"M{method_id:02d}: no implementation path cited")
            if not any(ref.startswith("tests/") or ref.startswith("frontend/e2e/") for ref in refs):
                errors.append(f"M{method_id:02d}: no test or browser acceptance path cited")
            has_commands = bool(re.search(r"pytest|ruff check|npx playwright|python (?:scripts|data-pipeline)/", section, re.I))
            if not has_commands:
                errors.append(f"M{method_id:02d}: no runnable or explicitly bounded reproduction command")
        for target in LINK.findall(content):
            if target.startswith(("https://", "http://", "mailto:", "#")):
                continue
            local_target = target.split("#", 1)[0]
            if local_target and not (path.parent / local_target).resolve().is_file():
                errors.append(f"{relative}: broken local link {target}")
    if covered != set(range(1, 14)):
        errors.append(f"method coverage is {sorted(covered)}, expected M01-M13")
    spanish_covered: set[int] = set()
    for relative, expected_ids in SPANISH_CHAPTERS.items():
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing Spanish chapter: {relative}")
            continue
        content = path.read_text(encoding="utf-8")
        chapter_ids = [int(value) for value in re.findall(r"^## M(\d{2})\.", content, re.M)]
        if chapter_ids != list(expected_ids):
            errors.append(f"{relative}: expected method headings {list(expected_ids)}, found {chapter_ids}")
        spanish_covered.update(chapter_ids)
        for label, patterns in {
            "equations": (r"(?:\\\[|\$\$)", r"(?:\\\]|\$\$)"),
            "supuestos y límites": (r"supuesto|hipótesis|elegibilidad", r"límite|limitación|no establece"),
            "reproducción": (r"reproduc|reproducibilidad", r"pytest|python |UNAVAILABLE"),
            "referencias": (r"referencias|fuentes primarias", r"https?://|doi\.org"),
        }.items():
            if not all(re.search(pattern, content, re.I) for pattern in patterns):
                errors.append(f"{relative}: missing Spanish structural evidence for {label}")
        normalized_content = content.replace("\\", "/")
        sections = re.split(r"(?=^## M\d{2}\.)", normalized_content, flags=re.M)
        for section in sections:
            heading = re.match(r"^## M(\d{2})\.", section)
            if not heading:
                continue
            method_id = int(heading[1])
            refs = set(REPOSITORY_PATH.findall(section))
            if not any(ref.startswith(("data-pipeline/", "app/", "frontend/src/", "scripts/")) for ref in refs):
                errors.append(f"M{method_id:02d} ES: no implementation path cited")
            if not any(ref.startswith(("tests/", "frontend/e2e/")) for ref in refs):
                errors.append(f"M{method_id:02d} ES: no test or browser acceptance path cited")
            if not re.search(r"pytest|ruff check|npx playwright|python (?:scripts|data-pipeline)/", section, re.I):
                errors.append(f"M{method_id:02d} ES: no runnable or explicitly bounded reproduction command")
        for target in LINK.findall(content):
            if target.startswith(("https://", "http://", "mailto:", "#")):
                continue
            local_target = target.split("#", 1)[0]
            if local_target and not (path.parent / local_target).resolve().is_file():
                errors.append(f"{relative}: broken local link {target}")
    if spanish_covered != set(range(1, 14)):
        errors.append(f"Spanish method coverage is {sorted(spanish_covered)}, expected M01-M13")
    for english_relative, spanish_relative in TRANSLATION_PAIRS:
        english_path, spanish_path = ROOT / english_relative, ROOT / spanish_relative
        if not english_path.is_file() or not spanish_path.is_file():
            continue
        english, spanish = english_path.read_text(encoding="utf-8"), spanish_path.read_text(encoding="utf-8")
        for label, pattern in (
            ("display equations", DISPLAY_MATH),
            ("code blocks", FENCED_CODE),
            ("inline code identifiers", INLINE_CODE),
            ("link targets", LINK),
            ("numeric tokens", NUMBER_TOKEN),
        ):
            if pattern.findall(english) != pattern.findall(spanish):
                errors.append(f"translation parity mismatch for {label}: {english_relative} vs {spanish_relative}")
    notebook_count, reviewed_method_count = check_source_content_coverage(errors)
    if errors:
        return fail("\n  - " + "\n  - ".join(errors))
    print("DOCS MATRIX STRUCTURE PASS: EN/ES M01-M13 chapters, equations, assumptions/limits, reproduction, references, implementation links.")
    print(f"SOURCE-TO-CONTENT COVERAGE PASS: {reviewed_method_count} methods and {notebook_count} current bilingual notebook files are bound to the review manifest.")
    print("Scientific correctness, source rights, full teaching quality, and release acceptance remain manual/separate gates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
