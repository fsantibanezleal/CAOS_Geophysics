"""Light source contract: transport refactoring cannot remove science predicates.

No fixture DB, HTTP, scientific import/fit, child, native or runtime acceptance.
"""

import ast
from pathlib import Path
import subprocess


PIN = '3e8ee19d06089d1273cfaf5d15e343cb0823047e'
ROOT = Path(__file__).resolve().parents[2]


def function(body, name):
    return next(node for node in ast.parse(body).body if isinstance(node, ast.FunctionDef) and node.name == name)


def previous(path, name):
    body = subprocess.check_output(['git', '-C', str(ROOT), 'show', PIN+':'+path])
    return function(body, name)


def current(path, name):
    return function((ROOT/path).read_bytes(), name)


def encoded(body):
    return [ast.dump(node, include_attributes=False) for node in body]


def commit(node):
    assert isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    assert ast.dump(node.value.func) == ast.dump(ast.parse('connection.commit()', mode='eval').body.func)


def test_terminal_publication_preserves_every_original_science_binding_byte_and_sql_predicate():
    old = previous('app/physical_publication.py', '_publish')
    new = current('app/physical_publication.py', '_publish')
    original = next(node for node in old.body if isinstance(node, ast.Try)).body
    shared = next(node for node in new.body if isinstance(node, ast.With)).body
    commit(original[-2])
    assert encoded(original[:-2]+original[-1:]) == encoded(shared)


def test_child_allocator_preserves_complete_parent_stage_dual_target_capacity_and_terminal_predicates():
    old = previous('app/physical_forest.py', 'reserve_child_intent')
    new = current('app/physical_forest.py', '_reserve_child_intent')
    original = next(node for node in old.body if isinstance(node, ast.Try)).body
    shared = next(node for node in new.body if isinstance(node, ast.With)).body
    # Only the transaction's old exact-candidate schema predicate moved to the
    # candidate context; native context separately validates full closed DDL.
    assert isinstance(original[0], ast.Expr) and original[0].value.args[-1].value == 'forest_schema_binding'
    commit(original[-2])
    assert encoded(original[1:-2]+original[-1:]) == encoded(shared)
