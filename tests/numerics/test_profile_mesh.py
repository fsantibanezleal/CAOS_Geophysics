"""Actual triangular topology, not a centre interpolator."""
import pytest

from profile_mesh import MeshError, parameter_mesh


def test_actual_grid_triangles_and_cell_order():
    import pygimli as pg
    mesh = pg.meshtools.createMesh(pg.meshtools.createRectangle(start=[0, 0], end=[4, -3]), area=0.5)
    result = parameter_mesh(mesh)
    assert len(result["cell_node_ids"]) == mesh.cellCount()
    assert len(result["node_xz_m"]) == mesh.nodeCount()
    for index, cell in enumerate(mesh.cells()):
        assert cell.id() == index
        actual = [[float(node.x()), float(node.y())] for node in cell.nodes()]
        assert [result["node_xz_m"][i] for i in result["cell_node_ids"][index]] == actual


def test_quad_mesh_is_not_relabelled_triangular():
    import pygimli as pg
    mesh = pg.meshtools.createGrid(x=[0, 1, 2], y=[-1, 0])
    with pytest.raises(MeshError):
        parameter_mesh(mesh)


def test_mesh_count_cap_precedes_iteration():
    class TooMany:
        def nodeCount(self): return 200001
        def cellCount(self): return 10
        def nodes(self): pytest.fail("oversized mesh iterated")
    with pytest.raises(MeshError):
        parameter_mesh(TooMany())
