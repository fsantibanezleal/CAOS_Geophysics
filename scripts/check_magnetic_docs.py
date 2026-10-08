"""Source/link/bilingual structural gate; never scientific or host acceptance."""
import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    docs = sorted((root/'docs/methods/magnetic-survey').glob('*.md'))
    if len(docs) != 9:
        raise ValueError('Complete nine-unit method wiki required')
    links = 0
    for path in docs:
        text = path.read_text(encoding='utf-8')
        if re.search(r'^## .*?(?:Español|Espanol|espanol)', text, re.M) is None:
            raise ValueError('Spanish explanation missing: '+path.name)
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if target.startswith(('https://','http://','#')):
                continue
            if not (path.parent/target.split('#',1)[0]).resolve().is_file():
                raise ValueError('Unresolved actual local documentation link: '+target)
            links += 1
    course = (root/'frontend/src/data/magnetic-survey-course.ts').read_text(encoding='utf-8')
    ids = re.findall(r'\{id:"([a-z]+)",label:', course)
    if len(ids) != 9 or len(set(ids)) != 9:
        raise ValueError('Nine distinct source-bound course chapters required')
    details = (root/'frontend/src/data/magnetic-course-derivations.ts').read_text(encoding='utf-8')
    detail_ids = re.findall(r'^  ([a-z]+):\{', details, re.M)
    if set(detail_ids) != set(ids) or len(detail_ids) != 9:
        raise ValueError('Every actual course chapter needs its derivation and worked question')
    for field in ('paragraphs:', 'equation:', 'symbols:', 'steps:', 'exercise:', 'answer:', 'implementation:'):
        if len(re.findall(r'^    '+re.escape(field), details, re.M)) != 9:
            raise ValueError('Incomplete per-chapter teaching unit: '+field)
    citations = (root/'frontend/src/data/magnetic-course-citations.ts').read_text(encoding='utf-8')
    citation_ids = re.findall(r'\{id:"([a-z0-9]+)",label:', citations)
    reference_ids = re.findall(r'const [a-z]+=\{id:"([a-z0-9]+)"', course)
    if set(citation_ids) != set(reference_ids) or len(citation_ids) != 4 or citations.count('url:"https://') != 4:
        raise ValueError('All primary course references need exact linked root-registry entries')
    component = (root/'frontend/src/components/MagneticSurveyCourse.tsx').read_text(encoding='utf-8')
    if ('<Cite ' not in component or '<Refs ' not in component or '<Figure ' not in component
            or 'data-magnetic-method-diagram' not in component or component.count('<Equation ') != 2
            or 'lesson.code}' in component or '<ReferenceList' in component):
        raise ValueError('Shared citations/two equations/theme diagram or visible-path boundary missing')
    for label in re.findall(r'code:"([^"]+)"', course):
        for item in label.split('; '):
            name, _, symbols = item.partition(': ')
            path = root/name if '/' in name else root/'data-pipeline'/name
            tree = ast.parse(path.read_text(encoding='utf-8'))
            defined = {n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
            if symbols and any(part not in defined for part in symbols.split('.')):
                raise ValueError('Course names a nonexistent implementation: '+item)
    return dict(wiki_units=len(docs), local_links=links, course_chapters=len(ids), primary_citations=len(citation_ids),
                complete_derivation_units=len(detail_ids),
                scientific_acceptance=False, parent_mount_verified=False)


def main():
    proof = check()
    print('Magnetic documentation structure/source links pass: '+str(proof))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
