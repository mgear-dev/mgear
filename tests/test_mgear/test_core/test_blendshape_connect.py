"""BlendShape and morph connections on referenced and local geometry.

On referenced geometry the hidden shape from the file is the first child of
the transform and the visible one is ``<name>ShapeDeformed``. The connect
helpers must find and reorder deformers on the visible shape.
"""

import pytest

NS = "ns"
ORDER_TYPES = ("blendShape", "morph", "skinCluster")


# =============================================================================
# HELPERS
# =============================================================================


def _new_scene():
    from maya import cmds

    cmds.file(new=True, force=True)
    return cmds


def _plane(name):
    """Create a 4x4 plane without construction history."""
    from maya import cmds

    return cmds.polyPlane(
        name=name, subdivisionsX=4, subdivisionsY=4, constructionHistory=False
    )[0]


def _body(tmp_path, referenced):
    """Open a new scene with a ``body`` plane, referenced or local.

    Returns:
        str: The body transform name.
    """
    from maya import cmds

    if not referenced:
        _new_scene()
        return _plane("body")

    _new_scene()
    _plane("body")
    path = str(tmp_path / "asset.ma")
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii", force=True)
    _new_scene()
    cmds.file(path, reference=True, namespace=NS)
    return NS + ":body"


def _skin(mesh):
    """Bind a mesh to two joints in the current scene."""
    from maya import cmds

    cmds.select(clear=True)
    jnts = [cmds.joint(name="jA", position=(-0.5, 0, 0))]
    jnts.append(cmds.joint(name="jB", position=(0.5, 0, 0)))
    cmds.select(clear=True)
    return cmds.skinCluster(jnts, mesh, toSelectedBones=True)[0]


def _eval_order(mesh):
    """Return the blendShape, morph and skinCluster types of a mesh.

    Returns:
        list: Deformer types, from the first evaluated to the last.
    """
    from maya import cmds
    from mgear.core import node

    shape = node.get_visible_shape(mesh)
    history = cmds.listHistory(shape, pruneDagObjects=True) or []
    types = [cmds.nodeType(h) for h in history]
    return [t for t in reversed(types) if t in ORDER_TYPES]


def _shapes(mesh):
    from maya import cmds

    return cmds.listRelatives(mesh, shapes=True, fullPath=True) or []


# =============================================================================
# VISIBLE SHAPE
# =============================================================================


def test_visible_shape_referenced(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.core import node

    body = _body(tmp_path, referenced=True)
    _skin(body)
    hidden, visible = _shapes(body)
    assert node.is_referenced(hidden)
    assert visible.endswith("ShapeDeformed")

    assert node.get_visible_shape(body) == visible
    # A hidden shape resolves to the visible one under the same transform
    assert node.get_visible_shape(hidden) == visible


def test_visible_shape_local(run_with_maya_standalone, setup_path, tmp_path):
    import mgear.pymaya as pm
    from maya import cmds
    from mgear.core import node

    body = _body(tmp_path, referenced=False)
    _skin(body)
    visible = [s for s in _shapes(body) if not cmds.getAttr(s + ".intermediateObject")]
    assert len(visible) == 1

    assert node.get_visible_shape(body) == visible[0]
    assert node.get_visible_shape(pm.PyNode(body)) == visible[0]
    assert node.get_visible_shape(visible[0]) == visible[0]


def test_visible_shape_none(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import node

    _new_scene()
    empty = cmds.createNode("transform", name="empty")
    assert node.get_visible_shape(empty) is None


# =============================================================================
# DEFORMER ORDER
# =============================================================================


@pytest.mark.parametrize("referenced", (True, False))
def test_morph_before_skin(run_with_maya_standalone, setup_path, tmp_path, referenced):
    from mgear.core import blendshape

    body = _body(tmp_path, referenced)
    _skin(body)
    target = _plane("target")

    morph = blendshape.connectWithMorph(body, target, ffoc=True)
    assert morph.type() == "morph"
    assert _eval_order(body) == ["morph", "skinCluster"]


@pytest.mark.parametrize("referenced", (True, False))
def test_blendshape_before_skin(
    run_with_maya_standalone, setup_path, tmp_path, referenced
):
    from mgear.core import blendshape

    body = _body(tmp_path, referenced)
    _skin(body)
    target = _plane("target")

    blendshape.connectWithBlendshape(body, target, ffoc=True)
    assert _eval_order(body) == ["blendShape", "skinCluster"]


@pytest.mark.parametrize("referenced", (True, False))
def test_morph_after_blendshape_before_skin(
    run_with_maya_standalone, setup_path, tmp_path, referenced
):
    from mgear.core import blendshape

    body = _body(tmp_path, referenced)
    _skin(body)
    blendshape.connectWithBlendshape(body, _plane("bs_target"), ffoc=True)

    blendshape.connectWithMorph(body, _plane("morph_target"), ffoc=True)
    assert _eval_order(body) == ["blendShape", "morph", "skinCluster"]


# =============================================================================
# LOOKUP
# =============================================================================


@pytest.mark.parametrize("referenced", (True, False))
def test_blendshape_lookup_and_reuse(
    run_with_maya_standalone, setup_path, tmp_path, referenced
):
    from maya import cmds
    from mgear.core import blendshape

    body = _body(tmp_path, referenced)
    _skin(body)

    # A new node comes back as the list from pm.blendShape
    first = blendshape.connectWithBlendshape(body, _plane("tgtA"), ffoc=True)[0]
    found = blendshape.getBlendShape(body)
    assert found is not None
    assert found.name() == first.name()

    second = blendshape.connectWithBlendshape(body, _plane("tgtB"), wgt=0.5)
    assert second.name() == first.name()
    assert len(cmds.ls(type="blendShape")) == 1
    assert sorted(cmds.listAttr(first.name() + ".weight", multi=True)) == [
        "tgtA",
        "tgtB",
    ]
    assert cmds.getAttr(first.name() + ".tgtB") == pytest.approx(0.5)


def test_morph_lookup_referenced(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.core import blendshape

    body = _body(tmp_path, referenced=True)
    _skin(body)
    morph = blendshape.connectWithMorph(body, _plane("target"), ffoc=True)

    found = blendshape.getMorph(body)
    assert found is not None
    assert found.name() == morph.name()
