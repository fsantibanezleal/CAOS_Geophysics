"""Serialize actual ordered triangular parameter cells in physical x/elevation."""
import math


class MeshError(ValueError):
    """Unsupported, oversized or inconsistent parameter mesh."""


def parameter_mesh(mesh):
    if not 3 <= mesh.nodeCount() <= 200000 or not 1 <= mesh.cellCount() <= 100000:
        raise MeshError("bounded parameter mesh required")
    nodes, mapping = [], {}
    for node in mesh.nodes():
        node_id = int(node.id())
        if node_id in mapping:
            raise MeshError("duplicate parameter node identity")
        point = [float(node.x()), float(node.y())]
        if not all(math.isfinite(value) for value in point):
            raise MeshError("nonfinite parameter node")
        mapping[node_id] = len(nodes)
        nodes.append(point)
    if len(nodes) != mesh.nodeCount():
        raise MeshError("parameter node count disagreement")
    cells = []
    for index, cell in enumerate(mesh.cells()):
        if int(cell.id()) != index or cell.nodeCount() != 3:
            raise MeshError("ordered three-node parameter cells required")
        try:
            references = [mapping[int(node.id())] for node in cell.nodes()]
        except KeyError as error:
            raise MeshError("unknown parameter node reference") from error
        if len(references) != 3 or len(set(references)) != 3:
            raise MeshError("three distinct parameter nodes required")
        a, b, c = [nodes[i] for i in references]
        area2 = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        if not math.isfinite(area2) or area2 == 0:
            raise MeshError("degenerate parameter cell")
        cells.append(references)
    if len(cells) != mesh.cellCount():
        raise MeshError("parameter cell count disagreement")
    return {"schema": "geophysics.profile-parameter-mesh/v1", "coordinate_unit": "m",
            "vertical_positive": "up", "node_xz_m": nodes, "cell_node_ids": cells}
