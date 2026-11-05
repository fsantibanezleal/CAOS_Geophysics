"""Source/handbook contract checks, not numerical or API acceptance."""
import ast
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'docs/data-contract/03_gravity-survey-native-integration.md'


def test_manifest_exports_name_existing_product_definitions():
    text = MANIFEST.read_text(encoding='utf-8')
    exports = re.findall(r'\b(gravity_[a-z0-9_]+)\.([a-z0-9_]+)', text)
    assert len(exports) == 12
    for module, name in exports:
        tree = ast.parse((ROOT / 'data-pipeline' / (module + '.py')).read_text(encoding='utf-8'))
        functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        assert name in functions, (module, name)
    for module in ('gravity_l2', 'gravity_irls'):
        tree = ast.parse((ROOT / 'data-pipeline' / (module + '.py')).read_text(encoding='utf-8'))
        epoch = next(ast.literal_eval(node.value) for node in tree.body
                     if isinstance(node, ast.Assign) and any(
                         isinstance(target, ast.Name) and target.id == 'RUNTIME_EPOCH'
                         for target in node.targets))
        assert epoch in text


def test_inspection_proposal_has_named_gates_and_is_not_an_implemented_mount():
    folder = ROOT / 'docs/design/features/m02-result-inspection'
    requirements = (folder / 'requirements.md').read_text(encoding='utf-8')
    assert 'Status: proposed; review required before implementation.' in requirements
    parts = re.split(r'(?m)^MV-\d{2}\b', requirements)[1:]
    assert len(parts) == 13
    assert all('Gate: proposed ' in part for part in parts)
    design = ' '.join((folder / 'design.md').read_text(encoding='utf-8').split())
    for predicate in ('observed_minus_predicted', 'fit_sha256', 'frame_model_sha256',
                      'recipe_sha256', 'field_eligible=false', 'host_accepted=false',
                      'not a common M02/M11 result DTO', 'not the FastAPI event loop'):
        assert predicate in design
    text = MANIFEST.read_text(encoding='utf-8')
    assert 'protected profiles' in text and 'queued M08' in text
    assert 'not an\nactivated API' in text


def test_new_handbook_relative_links_resolve():
    paths = [MANIFEST, ROOT / 'docs/design/features/m02-survey-l2/armijo-scale-cause.md',
             *(ROOT / 'docs/design/features/m02-result-inspection').glob('*.md')]
    for path in paths:
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if target.startswith('https://'):
                continue
            resolved = (path.parent / target.split('#', 1)[0]).resolve()
            assert resolved.is_relative_to(ROOT) and resolved.is_file(), (path, target)
