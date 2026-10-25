#!/usr/bin/env python3
"""Check that every SDD method has substantive, implementation-linked wiki coverage.

This is a structural documentation gate only. It cannot establish scientific
correctness, source rights, completeness of the teaching material, or release
acceptance; reviewers must assess those separately.
"""

from __future__ import annotations

import re
import sys
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
    if errors:
        return fail("\n  - " + "\n  - ".join(errors))
    print("DOCS MATRIX STRUCTURE PASS: EN/ES M01-M13 chapters, equations, assumptions/limits, reproduction, references, implementation links.")
    print("Scientific correctness, source rights, full teaching quality, and release acceptance remain manual/separate gates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
