"""Closed real documentation/source inventory; no numerical fitting."""
import importlib.util
from pathlib import Path
import re
import shutil

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('magnetic_docs_guard',
    ROOT/'scripts/check_magnetic_docs.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


@pytest.fixture
def copied_source(tmp_path):
    """Copy only actual wiki and course-referenced sources into external test temp."""
    docs = tmp_path/'docs/methods/magnetic-survey'
    docs.mkdir(parents=True)
    for source in (ROOT/'docs/methods/magnetic-survey').glob('*.md'):
        shutil.copyfile(source, docs/source.name)
    course = ROOT/'frontend/src/data/magnetic-survey-course.ts'
    destination = tmp_path/course.relative_to(ROOT)
    destination.parent.mkdir(parents=True)
    shutil.copyfile(course, destination)
    for label in re.findall(r'code:"([^"]+)"', course.read_text(encoding='utf-8')):
        for item in label.split('; '):
            name = item.partition(': ')[0]
            relative = Path(name) if '/' in name else Path('data-pipeline')/name
            target = tmp_path/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/relative, target)
    # Preserve each actual linked design/method document, without copying
    # numerical data, runtime files or unrelated method sources.
    for source in (ROOT/'docs/methods/magnetic-survey').glob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)', source.read_text(encoding='utf-8')):
            if link.startswith(('https://', 'http://', '#')):
                continue
            actual = (source.parent/link.split('#', 1)[0]).resolve()
            target = tmp_path/actual.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(actual, target)
    return tmp_path


def test_actual_closed_wiki():
    result = guard.check(ROOT)
    assert result['wiki_units'] == 13 and result['course_chapters'] == 9
    assert result['local_links'] > 0
    assert result['scientific_acceptance'] is False
    assert result['parent_mount_verified'] is False


@pytest.mark.parametrize('filename', sorted(guard.WIKI_FILES))
def test_every_missing_unit_refuses(copied_source, filename):
    (copied_source/'docs/methods/magnetic-survey'/filename).unlink()
    with pytest.raises(ValueError, match='Closed thirteen-unit'):
        guard.check(copied_source)


def test_unknown_unit_refuses(copied_source):
    (copied_source/'docs/methods/magnetic-survey/unknown.md').write_text(
        '# Unknown\n\n## Español\nNot an admitted unit.\n', encoding='utf-8')
    with pytest.raises(ValueError, match='unknown='):
        guard.check(copied_source)


@pytest.mark.parametrize('filename', [
    '10_exact-dataset-byte-custody.md', 'original10-final648-prerequisite.md',
    '11_authenticated-generation-replay.md'])
def test_added_unit_language_requirement_retained(copied_source, filename):
    path = copied_source/'docs/methods/magnetic-survey'/filename
    path.write_text(re.sub(r'^## Español.*$', '## Removed language heading',
        path.read_text(encoding='utf-8'), flags=re.M), encoding='utf-8')
    with pytest.raises(ValueError, match='Spanish explanation missing'):
        guard.check(copied_source)


def test_local_link_refusal_retained(copied_source):
    path = copied_source/'docs/methods/magnetic-survey/README.md'
    path.write_text(path.read_text(encoding='utf-8')+'\n[Broken](missing.md)\n',
        encoding='utf-8')
    with pytest.raises(ValueError, match='Unresolved actual local documentation link'):
        guard.check(copied_source)


def test_source_symbol_refusal_retained(copied_source):
    path = copied_source/'frontend/src/data/magnetic-survey-course.ts'
    text = path.read_text(encoding='utf-8')
    label = re.findall(r'code:"([^"]+)"', text)[0]
    name = label.split('; ')[0].partition(': ')[0]
    path.write_text(text.replace('code:"'+label+'"',
        'code:"'+name+': nonexistent_original_symbol"', 1), encoding='utf-8')
    with pytest.raises(ValueError, match='Course names a nonexistent implementation'):
        guard.check(copied_source)
