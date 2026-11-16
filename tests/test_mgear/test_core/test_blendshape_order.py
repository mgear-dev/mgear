"""mgear.core.blendshape front of chain order test"""

import pytest


def _scene(tweak):
    """A sphere skinned to a joint, with a legacy tweak node if asked."""
    from maya import cmds

    cmds.file(new=True, force=True)
    sphere = cmds.polySphere(name="body")[0]
    for name in ("bsTarget", "morphTarget"):
        cmds.polySphere(name=name)
    if tweak:
        cmds.deformer(sphere, type="tweak", name="tweakA")
    cmds.select(clear=True)
    joint = cmds.joint(name="j1")
    cmds.skinCluster(joint, sphere, name="skinA")
    return sphere


def _evaluation_order(geometry):
    """Deformers from the first evaluated to the last, tweaks included."""
    from maya import cmds

    history = cmds.listHistory(geometry, pruneDagObjects=True, interestLevel=1)
    types = ("skinCluster", "blendShape", "morph", "tweak")
    return [n for n in reversed(history) if cmds.nodeType(n) in types]


@pytest.mark.parametrize("tweak", (False, True))
def test_blendshape_foc(run_with_maya_standalone, setup_path, tweak):
    from mgear.core import blendshape

    sphere = _scene(tweak)
    bs = blendshape.connectWithBlendshape(sphere, "bsTarget", ffoc=True)

    expected = ["tweakA"] if tweak else []
    expected += [bs[0].name(), "skinA"]
    assert _evaluation_order(sphere) == expected


@pytest.mark.parametrize("tweak", (False, True))
def test_morph_after_blendshape(run_with_maya_standalone, setup_path, tweak):
    """Regression: with a tweak, the morph pushed the skinCluster first."""
    from mgear.core import blendshape

    sphere = _scene(tweak)
    bs = blendshape.connectWithBlendshape(sphere, "bsTarget", ffoc=True)
    morph = blendshape.connectWithMorph(sphere, "morphTarget", ffoc=True)

    expected = ["tweakA"] if tweak else []
    expected += [bs[0].name(), morph.name(), "skinA"]
    assert _evaluation_order(sphere) == expected


@pytest.mark.parametrize("tweak", (False, True))
def test_morph_foc_without_blendshape(run_with_maya_standalone, setup_path, tweak):
    from mgear.core import blendshape

    sphere = _scene(tweak)
    morph = blendshape.connectWithMorph(sphere, "morphTarget", ffoc=True)

    expected = ["tweakA"] if tweak else []
    expected += [morph.name(), "skinA"]
    assert _evaluation_order(sphere) == expected
