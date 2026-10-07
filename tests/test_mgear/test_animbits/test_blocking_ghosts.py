"""mgear.animbits.blocking_ghosts test"""

import os

import pytest


@pytest.fixture
def core(run_with_maya_standalone, setup_path):
    from mgear.animbits.blocking_ghosts import core

    return core


# ---------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------
def test_range_times(core):
    times = [1.0, 10.0, 20.0, 30.0]
    assert core.range_times(times, 5, 25) == [10.0, 20.0]
    assert core.range_times(times, 10, 20) == [10.0, 20.0]
    assert core.range_times(times, 25, 5) == [10.0, 20.0]
    assert core.range_times(times, 40, 50) == []
    assert core.same_frame(10.0, 10.00001)
    assert not core.same_frame(10.0, 10.5)


def test_display_state_and_steps(core):
    assert core.display_state(10.0, 10.0) == core.STATE_HIDDEN
    assert core.display_state(5.0, 10.0) == core.STATE_PREV
    assert core.display_state(15.0, 10.0) == core.STATE_POST

    steps = core.spread_steps([1.0, 5.0, 10.0, 20.0], 10.0)
    assert steps == {1.0: -2, 5.0: -1, 10.0: 0, 20.0: 1}


def test_matrix_changed_and_names(core):
    assert not core.matrix_changed([0.0, 1.0], [0.0, 1.0 + 1e-7])
    assert core.matrix_changed([0.0, 1.0], [0.0, 1.1])
    assert core.frame_label(10.0) == "10"
    assert core.frame_label(-3.0) == "neg3"
    assert core.frame_label(12.5) == "12_5"
    assert core.ghost_name(10.0, "|char:geo|char:body") == "bghost_f10_char_body"


# ---------------------------------------------------------------------
# Scene fixtures
# ---------------------------------------------------------------------
def _ghost_nodes():
    from maya import cmds

    return cmds.ls("BlockingGhosts_grp", "bghost*")


def _build_rig():
    """Build the test rig in the current scene.

    ``ctl.tx`` is keyed 0 / 5 / 10 at frames 1 / 10 / 20 and drives a
    cluster on ``body`` (a deformed mesh) and the z translation of
    ``prop`` (inheritsTransform off, locked channels).
    """
    from maya import cmds

    ctl = cmds.createNode("transform", name="ctl")
    geo = cmds.createNode("transform", name="geo")
    body = cmds.polyCube(name="body")[0]
    cmds.parent(body, geo)
    cluster, handle = cmds.cluster("body")
    cmds.connectAttr(ctl + ".tx", handle + ".tx")

    prop = cmds.polySphere(name="prop")[0]
    cmds.parent(prop, geo)
    cmds.connectAttr(ctl + ".tx", prop + ".tz")
    cmds.setAttr(prop + ".inheritsTransform", False)
    for channel in ("rx", "ry", "rz", "sx", "sy", "sz"):
        cmds.setAttr(prop + "." + channel, lock=True)

    for frame, value in ((1, 0), (10, 5), (20, 10)):
        cmds.setKeyframe(ctl, attribute="tx", time=frame, value=value)


@pytest.fixture
def rig_scene(core, tmp_path):
    """The test rig, referenced with namespace "char"."""
    from maya import cmds

    cmds.file(new=True, force=True)
    _build_rig()
    rig_path = str(tmp_path / "rig.ma")
    cmds.file(rename=rig_path)
    cmds.file(save=True, type="mayaAscii", force=True)
    cmds.file(new=True, force=True)
    cmds.file(rig_path, reference=True, namespace="char")
    cmds.currentTime(10, edit=True)
    yield {
        "ctl": "|char:ctl",
        "body": "|char:geo|char:body",
        "prop": "|char:geo|char:prop",
        "dir": str(tmp_path),
    }


@pytest.fixture
def local_scene(core):
    """The test rig built directly in the scene (editable animation)."""
    from maya import cmds

    cmds.file(new=True, force=True)
    _build_rig()
    cmds.currentTime(10, edit=True)
    yield {"ctl": "|ctl", "body": "|geo|body", "prop": "|geo|prop"}


def _make_session(core, scene):
    s = core.GhostSession()
    s.objects = [scene["body"], scene["prop"]]
    s.controls = [scene["ctl"]]
    return s


@pytest.fixture
def session(core, rig_scene):
    s = _make_session(core, rig_scene)
    yield s
    s.clear()


@pytest.fixture
def local_session(core, local_scene):
    s = _make_session(core, local_scene)
    yield s
    s.clear()


def _bbox_center(node):
    from maya import cmds

    bb = cmds.exactWorldBoundingBox(node)
    return ((bb[0] + bb[3]) / 2.0, (bb[1] + bb[4]) / 2.0, (bb[2] + bb[5]) / 2.0)


def _ghosts_at(core, frame):
    from maya import cmds

    group = "|BlockingGhosts_grp|bghost_f{}".format(core.frame_label(frame))
    return cmds.listRelatives(group, children=True, fullPath=True) or []


def _ghost(core, frame, suffix):
    """Return the ghost at a frame whose name ends with ``suffix``."""
    return [g for g in _ghosts_at(core, frame) if g.endswith(suffix)][0]


def _session_callbacks():
    """Return the recorded callback names of Blocking Ghosts sessions."""
    from mgear.core import callbackManager

    names = callbackManager.RECORDED_CALLBACKS
    return [k for k in names if k.startswith("blockingGhosts.")]


# ---------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------
def test_generate_referenced_rig(core, session, rig_scene):
    from maya import cmds

    assert session.generate()
    # The current frame (10) is keyed, so it is ghosted too.
    assert session.frames() == [1.0, 10.0, 20.0]
    assert cmds.currentTime(query=True) == 10.0

    ghosts = _ghosts_at(core, 1.0)
    assert len(ghosts) == 2
    body_ghost = _ghost(core, 1.0, "char_body")
    # Cluster moved the body 0 units in x at frame 1.
    assert _bbox_center(body_ghost)[0] == pytest.approx(0.0, abs=1e-4)
    body_ghost_20 = _ghost(core, 20.0, "char_body")
    assert _bbox_center(body_ghost_20)[0] == pytest.approx(10.0, abs=1e-4)

    # Clean copies: no history, no intermediate shapes.
    assert not cmds.listHistory(body_ghost, pruneDagObjects=True)
    shapes = cmds.listRelatives(body_ghost, shapes=True, fullPath=True)
    assert len(shapes) == 1
    assert cmds.getAttr(body_ghost + ".hideOnPlayback")
    assert not cmds.ls(type="controller")


def test_generate_skips_without_keys(core, session):
    session.controls = ["|char:geo"]
    assert not session.generate()
    assert not _ghost_nodes()


def test_display_states_follow_time(core, session):
    from maya import cmds

    session.generate()
    session.refresh()
    group_1 = "|BlockingGhosts_grp|bghost_f1"
    group_20 = "|BlockingGhosts_grp|bghost_f20"
    shape_1 = cmds.listRelatives(_ghosts_at(core, 1.0)[0], shapes=True, fullPath=True)[
        0
    ]
    assert cmds.sets(shape_1, isMember="bghost_prev_matSG")

    cmds.currentTime(20, edit=True)
    session.refresh()
    assert not cmds.getAttr(group_20 + ".visibility")
    assert cmds.getAttr(group_1 + ".visibility")

    cmds.currentTime(0, edit=True)
    session.refresh()
    assert cmds.sets(shape_1, isMember="bghost_post_matSG")


def test_spacing_moves_all_ghosts(core, session, rig_scene):
    from maya import cmds
    from mgear.core import utils

    session.generate()
    prop_ghost = _ghost(core, 1.0, "char_prop")
    before = _bbox_center(prop_ghost)
    session.set_spacing(10.0)
    after = _bbox_center(prop_ghost)

    right = utils.get_camera_axis(utils.get_active_camera(), "x")
    # Positive spacing: previous poses go to the camera's right.
    expected = tuple(b + 10.0 * r for b, r in zip(before, right))
    assert after == pytest.approx(expected, abs=1e-4)

    # The source pose is kept at zero spacing.
    session.set_spacing(0.0)
    cmds.currentTime(1, edit=True)
    assert _bbox_center(prop_ghost) == pytest.approx(
        _bbox_center(rig_scene["prop"]), abs=1e-4
    )


def test_duplicate_short_names_and_original_shading(core, run_with_maya_standalone):
    from maya import cmds
    from mgear.core import shading

    cmds.file(new=True, force=True)
    ctl = cmds.createNode("transform", name="ctl")
    for frame in (1, 10, 20):
        cmds.setKeyframe(ctl, attribute="tx", time=frame)
    a = cmds.createNode("transform", name="a")
    b = cmds.createNode("transform", name="b")
    body_a = cmds.parent(cmds.polyCube(name="body")[0], a)[0]
    body_b = cmds.parent(cmds.polyCube(name="tmp")[0], b)[0]
    body_b = cmds.rename(body_b, "body")
    _, sg_a = shading.create_flat_shader("matA", (1, 0, 0))
    _, sg_b = shading.create_flat_shader("matB", (0, 1, 0))
    cmds.sets("|a|body", edit=True, forceElement=sg_a)
    cmds.sets("|b|body.f[0:2]", edit=True, forceElement=sg_b)
    cmds.currentTime(10, edit=True)

    s = core.GhostSession()
    s.objects = ["|a|body", "|b|body"]
    s.controls = ["|ctl"]
    try:
        assert s.generate()
        ghosts = _ghosts_at(core, 1.0)
        assert len(ghosts) == 2

        s.set_ghost_color(False)
        s.refresh()
        by_source = dict(zip(["|a|body", "|b|body"], ghosts))
        for source, ghost in by_source.items():
            src_shape = cmds.listRelatives(source, shapes=True, fullPath=True)[0]
            ghost_shape = cmds.listRelatives(ghost, shapes=True, fullPath=True)[0]
            assert dict(shading.get_face_shader_mapping(ghost_shape)) == dict(
                shading.get_face_shader_mapping(src_shape)
            )

        s.set_ghost_color(True)
        ghost_shape = cmds.listRelatives(ghosts[0], shapes=True, fullPath=True)[0]
        assert cmds.sets(ghost_shape, isMember="bghost_prev_matSG")
    finally:
        s.clear()


# ---------------------------------------------------------------------
# Scene safety
# ---------------------------------------------------------------------
def test_undo_queue_untouched(core, session, rig_scene):
    from maya import cmds
    from mgear.core import utils

    cmds.undoInfo(state=True, infinity=True)
    session.generate()
    marker = cmds.createNode("transform", name="user_edit")
    cmds.setAttr(marker + ".tx", 3)
    last_undo = cmds.undoInfo(query=True, undoName=True)

    for frame in (5, 15, 20, 0):
        # Scripted time changes are undoable, unlike timeline scrubbing.
        with utils.undo_disabled():
            cmds.currentTime(frame, edit=True)
        session.refresh()
    session.set_spacing(5.0)
    session.set_transparency(0.2)
    session.set_ghost_color(False)
    session.set_ghost_color(True)
    session.recapture(1.0, 0.0)
    assert cmds.undoInfo(query=True, undoName=True) == last_undo

    cmds.undo()
    assert cmds.getAttr(marker + ".tx") == 0
    assert cmds.objExists("|BlockingGhosts_grp|bghost_f1")
    assert len(_ghosts_at(core, 1.0)) == 2


def test_ghosts_not_saved(core, session, rig_scene):
    from maya import cmds

    session.generate()
    session.set_ghost_color(False)
    session.set_ghost_color(True)
    path = os.path.join(rig_scene["dir"], "shot.ma")
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii", force=True)
    session.teardown()
    cmds.file(new=True, force=True)
    cmds.file(path, open=True, force=True)
    assert not _ghost_nodes()
    assert cmds.objExists(rig_scene["body"])
    with open(path) as handle:
        assert "bghost" not in handle.read()


def test_callbacks_and_no_scriptjobs(core, session):
    from maya import cmds

    before = set(cmds.scriptJob(listJobs=True) or [])
    session.generate()
    assert set(cmds.scriptJob(listJobs=True) or []) == before
    assert len(_session_callbacks()) == 6

    # A second session replaces, not duplicates, the callbacks.
    other = core.GhostSession()
    other.objects = session.objects
    other.controls = session.controls
    other.generate()
    assert len(_session_callbacks()) == 6

    other.clear()
    session.clear()
    assert not _ghost_nodes()
    assert not _session_callbacks()


def test_new_scene_tears_down(core, session):
    from maya import cmds

    session.generate()
    assert session.frames()
    cmds.file(new=True, force=True)
    assert not session.frames()
    assert not session._callbacks.MANAGER_CALLBACKS


# ---------------------------------------------------------------------
# Re-capture
# ---------------------------------------------------------------------
def test_recapture_updates_pose_in_place(core, local_session, local_scene):
    from maya import cmds

    session = local_session
    session.generate()
    body_ghost = _ghost(core, 1.0, "_body")
    prop_ghost = _ghost(core, 1.0, "_prop")

    # Animator changes the frame-1 pose.
    cmds.setKeyframe(local_scene["ctl"], attribute="tx", time=1, value=-4)
    session.recapture(1.0, 10.0)

    assert cmds.currentTime(query=True) == 10.0
    # Same ghost nodes, updated in place.
    assert cmds.objExists(body_ghost) and cmds.objExists(prop_ghost)
    assert _bbox_center(body_ghost)[0] == pytest.approx(-4.0, abs=1e-4)
    assert _bbox_center(prop_ghost)[2] == pytest.approx(-4.0, abs=1e-4)


def test_selecting_ghost_jumps_to_frame(core, session, rig_scene):
    from maya import cmds

    session.generate()
    cmds.select(rig_scene["ctl"])
    session._on_selection_changed()
    ghost = _ghosts_at(core, 20.0)[0]
    cmds.select(ghost)
    session._on_selection_changed()
    assert cmds.currentTime(query=True) == 20.0
    assert cmds.ls(selection=True, long=True) == [rig_scene["ctl"]]


# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------
def test_ui_config_round_trip(core, local_scene, clean_settings, tmp_path):
    import json
    from maya import cmds
    from mgear.animbits.blocking_ghosts import ui

    window = ui.BlockingGhostsUI()
    try:
        window.objects_list.set_nodes([local_scene["body"]])
        window.controls_list.set_nodes([local_scene["ctl"]])
        window.start_spin.setValue(5)
        window.end_spin.setValue(15)
        window.prev_color_btn.set_color((0.1, 0.2, 0.3))
        window.spacing_slider.setValue(25)
        window.shader_toggle.setChecked(False)
        config = window.gather_config()

        path = str(tmp_path / "shot.bgh")
        with open(path, "w") as handle:
            json.dump(config, handle)
        window.apply_config({})
        assert window.objects_list.nodes() == []
        assert window.gather_config() == ui.DEFAULTS
        window.load_config_file(path)
        assert window.gather_config() == config
        assert window.shader_toggle.text() == "Original Shader"

        # Bad files only warn.
        bad = str(tmp_path / "bad.bgh")
        with open(bad, "w") as handle:
            handle.write("not json")
        window.load_config_file(bad)
        assert window.gather_config() == config

        cmds.playbackOptions(minTime=1, maxTime=20)
        window.use_timeline_range()
        assert (window.start_spin.value(), window.end_spin.value()) == (1, 20)

        window._on_generate()
        assert window.session.frames() == [1.0, 10.0, 20.0]
        window.shutdown()
        assert not _ghost_nodes()
    finally:
        window.deleteLater()


# ---------------------------------------------------------------------
# Frame range, negative spacing, key sync
# ---------------------------------------------------------------------
def test_range_limits_ghosts(core, session):
    session.start_frame = 5
    session.end_frame = 15
    assert session.generate()
    assert session.frames() == [10.0]

    session.start_frame = 40
    session.end_frame = 50
    assert not session.generate()


def test_current_pose_ghost_shows_after_moving(core, session):
    from maya import cmds

    session.generate()
    group = "|BlockingGhosts_grp|bghost_f10"
    assert not cmds.getAttr(group + ".visibility")
    cmds.currentTime(15, edit=True)
    session.refresh()
    assert cmds.getAttr(group + ".visibility")
    shape = cmds.listRelatives(_ghosts_at(core, 10.0)[0], shapes=True, fullPath=True)
    assert cmds.sets(shape[0], isMember="bghost_prev_matSG")


def test_negative_spacing_swaps_sides(core, session):
    from mgear.core import utils

    session.generate()
    cmds_right = utils.get_camera_axis(utils.get_active_camera(), "x")
    session.set_spacing(-20.0)
    prev_offset = session._frame_at(1.0).offset
    post_offset = session._frame_at(20.0).offset
    # Negative spacing: previous poses go to the camera's left.
    assert prev_offset == pytest.approx(tuple(-20.0 * r for r in cmds_right))
    assert post_offset == pytest.approx(tuple(20.0 * r for r in cmds_right))


def test_sync_keys_adds_and_removes(core, local_session, local_scene):
    from maya import cmds

    session = local_session
    session.start_frame = 1
    session.end_frame = 30
    session.generate()
    assert session.frames() == [1.0, 10.0, 20.0]

    ctl = local_scene["ctl"]
    cmds.setKeyframe(ctl, attribute="tx", time=15, value=-2)
    cmds.setKeyframe(ctl, attribute="tx", time=40, value=0)
    cmds.cutKey(ctl, attribute="tx", time=(20, 20))
    cmds.currentTime(12, edit=True)
    session._on_scrub_settled()

    assert session.frames() == [1.0, 10.0, 15.0]
    assert not cmds.objExists("|BlockingGhosts_grp|bghost_f20")
    assert cmds.currentTime(query=True) == 12.0
    body_15 = _ghost(core, 15.0, "_body")
    assert _bbox_center(body_15)[0] == pytest.approx(-2.0, abs=1e-4)

    # Nothing changed: no rebuild.
    assert not session.sync_keys()
