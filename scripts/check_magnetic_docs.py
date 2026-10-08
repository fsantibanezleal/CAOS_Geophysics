"""Source/link/bilingual structural gate; never scientific or host acceptance."""
import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    docs = sorted((root/'docs/methods/magnetic-survey').glob('*.md'))
    if len(docs) != 10:
        raise ValueError('Complete ten-unit method wiki required')
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
    for label in re.findall(r'code:"([^"]+)"', course):
        for item in label.split('; '):
            name, _, symbols = item.partition(': ')
            path = root/name if '/' in name else root/'data-pipeline'/name
            tree = ast.parse(path.read_text(encoding='utf-8'))
            defined = {n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
            if symbols and any(part not in defined for part in symbols.split('.')):
                raise ValueError('Course names a nonexistent implementation: '+item)
    return dict(wiki_units=len(docs), local_links=links, course_chapters=len(ids),
                scientific_acceptance=False, parent_mount_verified=False)


def main():
    proof = check()
    print('Magnetic documentation structure/source links pass: '+str(proof))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
