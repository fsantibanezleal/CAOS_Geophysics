"""Actual source-bound course structure; not rendered or scientific acceptance."""
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('magnetic_course_guard', ROOT/'scripts/check_magnetic_docs.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def test_actual_complete_bilingual_course_and_source_symbols():
    result = guard.check(ROOT)
    assert result['course_chapters'] == result['complete_derivation_units'] == 9
    assert result['primary_citations'] == 4
    assert result['scientific_acceptance'] is result['parent_mount_verified'] is False


@pytest.mark.parametrize('name,before,after', [
    ('data/magnetic-course-derivations.ts', '    paragraphs:', '    missing_paragraphs:'),
    ('data/magnetic-course-derivations.ts', '  original:{', '  unknown:{'),
    ('data/magnetic-course-citations.ts', 'id:"simpeg0252magnetic"', 'id:"unregistered"'),
    ('components/MagneticSurveyCourse.tsx', '<Refs ', '<ReferenceList '),
    ('components/MagneticSurveyCourse.tsx', '<Equation ', '<UncaptionedEquation '),
])
def test_guard_refuses_incomplete_units_and_unmounted_shared_primitives(monkeypatch, name, before, after):
    target = ROOT/'frontend/src'/name
    read = Path.read_text

    def altered(path, *args, **kwargs):
        text = read(path, *args, **kwargs)
        if path == target:
            assert before in text
            return text.replace(before, after, 1)
        return text

    monkeypatch.setattr(Path, 'read_text', altered)
    with pytest.raises(ValueError):
        guard.check(ROOT)
