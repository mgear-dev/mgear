"""mgear.core undo, camera, keyframe and playback helpers test"""

import pytest


def test_undo_disabled_keeps_queue(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import utils

    cmds.file(new=True, force=True)
    cmds.undoInfo(state=True, infinity=True)
    node = cmds.createNode("transform", name="undo_test")
    cmds.setAttr(node + ".tx", 5)
    with utils.undo_disabled():
        cmds.setAttr(node + ".ty", 7)
    assert cmds.undoInfo(query=True, state=True)

    # Undo reverts the recorded tx edit, not the unrecorded ty edit.
    cmds.undo()
    assert cmds.getAttr(node + ".tx") == 0
    assert cmds.getAttr(node + ".ty") == 7


def test_undo_disabled_restores_on_error(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import utils

    cmds.undoInfo(state=True)
    with pytest.raises(ValueError):
        with utils.undo_disabled():
            raise ValueError("boom")
    assert cmds.undoInfo(query=True, state=True)


def test_undo_disabled_nested(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import utils

    cmds.undoInfo(state=True)
    with utils.undo_disabled():
        with utils.undo_disabled():
            pass
        assert not cmds.undoInfo(query=True, state=True)
    assert cmds.undoInfo(query=True, state=True)


def test_get_camera_axis(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import utils

    cmds.file(new=True, force=True)
    cam = cmds.camera()[0]
    cmds.setAttr(cam + ".ry", 90)
    x = utils.get_camera_axis(cam, "x")
    assert x == pytest.approx((0.0, 0.0, -1.0), abs=1e-6)
    y = utils.get_camera_axis(cam, "y")
    assert y == pytest.approx((0.0, 1.0, 0.0), abs=1e-6)

    matrix = cmds.xform(cam, query=True, matrix=True, worldSpace=True)
    assert utils.get_camera_axis(None, "x", matrix=matrix) == pytest.approx(x)

    assert utils.get_camera_axis("missing_cam") == (1.0, 0.0, 0.0)
    assert utils.get_camera_axis(None, "z") == (0.0, 0.0, 1.0)


def test_get_active_camera_batch(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import utils

    cmds.file(new=True, force=True)
    assert utils.get_active_camera() == "|persp"


def test_get_keyframe_times(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import anim_utils

    cmds.file(new=True, force=True)
    a = cmds.createNode("transform", name="ctl_a")
    b = cmds.createNode("transform", name="ctl_b")
    for frame in (10, 1, 20):
        cmds.setKeyframe(a, attribute="tx", time=frame)
    for frame in (20, 15):
        cmds.setKeyframe(b, attribute="ry", time=frame)

    times = anim_utils.get_keyframe_times([a, b, "missing_ctl"])
    assert times == [1.0, 10.0, 15.0, 20.0]
    assert anim_utils.get_keyframe_times([]) == []
    assert anim_utils.get_keyframe_times(["missing_ctl"]) == []


def test_viewport_suspended_restores(run_with_maya_standalone, setup_path):
    from mgear.core import utils

    with pytest.raises(ValueError):
        with utils.viewport_suspended():
            raise ValueError("boom")


def test_set_hide_on_playback_no_tag(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import node

    cmds.file(new=True, force=True)
    grp = cmds.createNode("transform", name="ghost_grp")
    node.set_hide_on_playback([grp])
    assert cmds.getAttr(grp + ".hideOnPlayback")
    assert not cmds.ls(type="controller")
    node.set_hide_on_playback([grp], enabled=False)
    assert not cmds.getAttr(grp + ".hideOnPlayback")
