"""Exact fixture extraction, not a new migration or replaced original gate."""

import ast
from pathlib import Path


def test_current_helpers_keep_original_native_seed_projection_and_insert():
    root = Path(__file__).resolve().parents[2]
    old = ast.parse((root / 'tests/api/test_physical_persistence_schema.py').read_text(encoding='utf-8'))
    new = ast.parse((root / 'tests/ops/physical_sql_fixture.py').read_text(encoding='utf-8'))
    for name in ('seed', 'inventory', 'insert'):
        original = next(n for n in old.body if isinstance(n, ast.FunctionDef) and n.name == name)
        current = next(n for n in new.body if isinstance(n, ast.FunctionDef) and n.name == name)
        assert ast.dump(original, include_attributes=False) == ast.dump(current, include_attributes=False)
