#!/usr/bin/env python3
"""Check the authored magnetic-survey wiki/course source contract.

This is a content and link inventory, not method or field acceptance. It checks
that the bilingual teaching source still covers the declared topics, uses the
registered versioned references, and links to real local implementation docs.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/methods/magnetic-survey/README.md"
ALGORITHMS = ROOT / "docs/design/features/m04-survey-inversion/algorithms.md"
LESSONS = ROOT / "frontend/src/data/magnetic-survey-course.ts"
DERIVATIONS = ROOT / "frontend/src/data/magnetic-course-derivations.ts"
CITATIONS = ROOT / "frontend/src/data/magnetic-course-citations.ts"
COURSE_COMPONENT = ROOT / "frontend/src/components/MagneticTheoryCourse.tsx"

LESSON_IDS = (
    "original", "physics", "likelihood", "prior", "sparse", "partition",
    "native", "diagnostics", "custody",
)
CITATION_IDS = (
    "simpeg0252magnetic", "simpeg0252regularization", "simpeg0252sparse",
    "choclo032magnetic",
)
REQUIRED_WIKI_EN = ("L2", "IRLS", "source", "covariance", "SimPEG")
REQUIRED_WIKI_ES = ("Español", "susceptibilidad", "SimPEG")
LOCAL_LINK = re.compile(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"cannot read {path}: {error}") from error


def audit(root: Path = ROOT) -> list[str]:
    """Return specific missing-source or topic findings, without scoring science."""
    root = root.resolve()
    doc, algorithms, lessons, derivations, citations, component = (
        root / path.relative_to(ROOT)
        for path in (DOC, ALGORITHMS, LESSONS, DERIVATIONS, CITATIONS, COURSE_COMPONENT)
    )
    findings: list[str] = []
    sources = {path: _read(path) for path in (doc, algorithms, lessons, derivations, citations, component)}
    wiki = sources[doc]
    algorithm_doc = sources[algorithms]
    course = sources[lessons]
    derivation = sources[derivations]
    citation_registry = sources[citations]
    component_source = sources[component]

    for marker in REQUIRED_WIKI_EN:
        if marker.casefold() not in wiki.casefold():
            findings.append(f"wiki lacks required topic marker: {marker}")
    for marker in REQUIRED_WIKI_ES:
        if marker.casefold() not in wiki.casefold():
            findings.append(f"wiki lacks Spanish topic marker: {marker}")
    if not re.search(r"(?m)^## Español\b", wiki):
        findings.append("wiki has no explicit Spanish section")

    lesson_source = course.split("export const magneticLessons", 1)[-1].split("\n];", 1)[0]
    found_ids = re.findall(r'\bid:"([a-z0-9-]+)"', lesson_source)
    if tuple(found_ids) != LESSON_IDS:
        findings.append(f"course lesson order/coverage differs: {tuple(found_ids)}")
    for lesson_id in LESSON_IDS:
        if not re.search(rf"(?m)^\s*{re.escape(lesson_id)}:\s*\{{", derivation):
            findings.append(f"course lacks bilingual worked derivation: {lesson_id}")
    if tuple(re.findall(r"(?m)^\s*([a-z]+):\s*\{", derivation)) != LESSON_IDS:
        findings.append("course derivation order/coverage differs")
    for marker in ("IRLS", "epsilon", "true smooth-p1 objective", "projected-gradient", "validation"):
        if marker.casefold() not in derivation.casefold() + course.casefold():
            findings.append(f"course lacks algorithm detail: {marker}")
    for marker in ("Sparse.update_weights", "phi_d", "covariance", "beta", "KKT"):
        if marker.casefold() not in algorithm_doc.casefold():
            findings.append(f"algorithm wiki lacks method detail: {marker}")
    if "not commands" not in wiki.casefold() or not re.search(r"no existe comando de\s+calibración", wiki, re.I):
        findings.append("wiki must state the local inversion command is not implemented in EN and ES")
    if "covarianza" not in course.casefold():
        findings.append("bilingual course lacks Spanish covariance terminology")

    for citation_id in CITATION_IDS:
        if citation_registry.count(f'id:"{citation_id}"') != 1:
            findings.append(f"citation registry must contain exactly one {citation_id}")
        if f'id:"{citation_id}"' not in course:
            findings.append(f"course does not cite registered source {citation_id}")
    if "https://raw.githubusercontent.com/" not in citation_registry:
        findings.append("version-pinned primary source URLs are missing")
    if "@fasl-work/caos-app-shell" not in component_source or "style=" in component_source:
        findings.append("course must use shared shell components without inline styles")

    for source, text in ((doc, wiki), (algorithms, algorithm_doc)):
        for link in LOCAL_LINK.findall(text):
            if link.startswith(("mailto:", "data:")):
                continue
            target = (source.parent / link.split("#", 1)[0]).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                findings.append(f"wiki local link is missing or escapes repository: {link}")

    return findings


def main() -> int:
    try:
        findings = audit()
    except ValueError as error:
        print(f"magnetic documentation check: {error}", file=sys.stderr)
        return 2
    if findings:
        for finding in findings:
            print(f"FAIL: {finding}", file=sys.stderr)
        return 1
    print("Magnetic wiki/course source contract passes; no scientific or field acceptance is inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
