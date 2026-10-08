"""mgear.core.vector test"""

import pytest


def _transform(name, position):
    """Create a transform at a world position."""
    from maya import cmds

    node = cmds.createNode("transform", name=name)
    cmds.setAttr(node + ".translate", *position, type="double3")
    return node


def test_get_distance(run_with_maya_standalone, setup_path):
    from maya import cmds
    from maya import OpenMaya
    from mgear.core import vector

    v_1 = OpenMaya.MVector(0, 0, 0)
    v_2 = OpenMaya.MVector(1, 0, 0)
    assert vector.getDistance(v_1, v_2) == 1.0

    cmds.file(new=True, force=True)
    a = _transform("a", (0, 0, 0))
    b = _transform("b", (10, 5, 7))
    distance = cmds.createNode("distanceBetween")
    cmds.connectAttr(a + ".worldMatrix[0]", distance + ".inMatrix1")
    cmds.connectAttr(b + ".worldMatrix[0]", distance + ".inMatrix2")
    expected = cmds.getAttr(distance + ".distance")
    result = vector.getDistance(vector.get_mvector(a), vector.get_mvector(b))
    assert result == pytest.approx(expected)


def test_get_plane_binormal(run_with_maya_standalone, setup_path):
    from maya import OpenMaya
    from mgear.core import vector

    result = vector.getPlaneBiNormal(
        OpenMaya.MVector(0, 0, 0),
        OpenMaya.MVector(-1, 0, 0),
        OpenMaya.MVector(0, 0, 1),
    )
    assert isinstance(result, OpenMaya.MVector)
    assert [result.x, result.y, result.z] == [0, 0, -1]


def test_get_plane_normal(run_with_maya_standalone, setup_path):
    from maya import cmds
    from maya import OpenMaya
    from mgear.core import vector

    result = vector.getPlaneNormal(
        OpenMaya.MVector(0, 0, 0),
        OpenMaya.MVector(1, 0, 0),
        OpenMaya.MVector(0, 0, 1),
    )
    assert isinstance(result, OpenMaya.MVector)
    assert [result.x, result.y, result.z] == [0, 1, 0]

    cmds.file(new=True, force=True)
    points = [
        vector.get_mvector(_transform(name, position))
        for name, position in (
            ("a", (0, 0, 0)),
            ("b", (-1, 0, 0)),
            ("c", (0, 0, 1)),
        )
    ]
    result = vector.getPlaneNormal(*points)
    assert [result.x, result.y, result.z] == [0, -1, 0]


def test_linearly_interpolate(run_with_maya_standalone, setup_path):
    from maya import cmds
    from maya import OpenMaya
    from mgear.core import vector

    result = vector.linearlyInterpolate(
        OpenMaya.MVector(0, 0, 0), OpenMaya.MVector(2, 5, 8)
    )
    assert isinstance(result, OpenMaya.MVector)
    assert [result.x, result.y, result.z] == [1, 2.5, 4]

    result = vector.linearlyInterpolate(
        OpenMaya.MVector(0, 0, 0), OpenMaya.MVector(2, 5, 8), blend=0.25
    )
    assert [result.x, result.y, result.z] == [0.5, 1.25, 2]

    cmds.file(new=True, force=True)
    a = vector.get_mvector(_transform("a", (0, 0, 0)))
    b = vector.get_mvector(_transform("b", (2, 5, 8)))
    result = vector.linearlyInterpolate(a, b)
    assert [result.x, result.y, result.z] == [1, 2.5, 4]
