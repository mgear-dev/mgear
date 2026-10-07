"""mgear.core.shading test"""

import pytest


def test_index_ranges(run_with_maya_standalone, setup_path):
    from mgear.core import shading

    assert shading.index_ranges([0, 1, 2, 5, 7, 8]) == [(0, 2), (5, 5), (7, 8)]
    assert shading.index_ranges([3]) == [(3, 3)]
    assert shading.index_ranges([]) == []


def _two_material_plane():
    from maya import cmds
    from mgear.core import shading

    cmds.file(new=True, force=True)
    # 30 faces: 0-9 and 20-29 use sgA, 10-19 use sgB.
    plane = cmds.polyPlane(subdivisionsX=10, subdivisionsY=3)[0]
    shape = cmds.listRelatives(plane, shapes=True, fullPath=True)[0]
    _, sg_a = shading.create_flat_shader("matA", (1, 0, 0))
    _, sg_b = shading.create_flat_shader("matB", (0, 0, 1))
    cmds.sets(
        [shape + ".f[0:9]", shape + ".f[20:29]"],
        edit=True,
        forceElement=sg_a,
    )
    cmds.sets(shape + ".f[10:19]", edit=True, forceElement=sg_b)
    return plane, shape, sg_a, sg_b


def _unshaded_copy(plane):
    """Duplicate a mesh and reset its copy to the default shading group."""
    from maya import cmds

    copy = cmds.duplicate(plane)[0]
    copy_shape = cmds.listRelatives(copy, shapes=True, fullPath=True)[0]
    cmds.sets(copy_shape, edit=True, forceElement="initialShadingGroup")
    return copy_shape


def test_mapping_single_material(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import shading

    cmds.file(new=True, force=True)
    cube = cmds.polyCube()[0]
    mapping = shading.get_face_shader_mapping(cube)
    assert mapping == [("initialShadingGroup", [(0, 5)])]


def test_mapping_multi_material(run_with_maya_standalone, setup_path):
    from mgear.core import shading

    plane, shape, sg_a, sg_b = _two_material_plane()
    mapping = dict(shading.get_face_shader_mapping(shape))
    assert mapping[sg_a] == [(0, 9), (20, 29)]
    assert mapping[sg_b] == [(10, 19)]


def test_mapping_no_shading(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import shading

    cmds.file(new=True, force=True)
    cube = cmds.polyCube()[0]
    shape = cmds.listRelatives(cube, shapes=True, fullPath=True)[0]
    cmds.sets(shape, edit=True, remove="initialShadingGroup")
    assert shading.get_face_shader_mapping(shape) == []


def test_restore_mapping_on_copy(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import shading

    plane, shape, sg_a, sg_b = _two_material_plane()
    mapping = shading.get_face_shader_mapping(shape)
    copy_shape = _unshaded_copy(plane)

    shading.apply_face_shader_mapping(copy_shape, mapping)
    restored = dict(shading.get_face_shader_mapping(copy_shape))
    assert restored == dict(mapping)


def test_restore_skips_missing_group(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import shading

    plane, shape, sg_a, sg_b = _two_material_plane()
    mapping = shading.get_face_shader_mapping(shape)
    copy_shape = _unshaded_copy(plane)
    cmds.delete(sg_b)

    shading.apply_face_shader_mapping(copy_shape, mapping)
    restored = dict(shading.get_face_shader_mapping(copy_shape))
    assert restored[sg_a] == [(0, 9), (20, 29)]


def test_create_and_reuse_flat_shader(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import shading

    cmds.file(new=True, force=True)
    shader, sg = shading.create_flat_shader("ghost_mat", (1, 0, 0), 0.5)
    assert (shader, sg) == ("ghost_mat", "ghost_matSG")
    assert cmds.getAttr(shader + ".incandescence")[0] == (1.0, 0.0, 0.0)
    assert cmds.getAttr(shader + ".diffuse") == 0.0
    assert cmds.getAttr(shader + ".transparency")[0] == (0.5, 0.5, 0.5)

    count = len(cmds.ls(type="blinn"))
    shading.create_flat_shader("ghost_mat", (0, 1, 0), 0.25)
    assert len(cmds.ls(type="blinn")) == count
    assert cmds.getAttr(shader + ".color")[0] == (0.0, 1.0, 0.0)

    shading.set_shader_transparency(shader, 0.8)
    assert cmds.getAttr(shader + ".transparency")[0] == pytest.approx((0.8, 0.8, 0.8))
