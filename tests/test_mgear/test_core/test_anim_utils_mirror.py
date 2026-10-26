"""Tests for the shared mirror and flip functions of mgear.core.anim_utils."""

import inspect

import pytest

L_ARM = "arm_L0_fk0_ctl"
R_ARM = "arm_R0_fk0_ctl"
L_LEG = "leg_L0_fk0_ctl"
R_LEG = "leg_R0_fk0_ctl"
BODY = "body_C0_ctl"


def _rz(cmds, node):
    return round(cmds.getAttr(node + ".rotateZ"), 3)


def _pose_arms(cmds, left=30.0, right=-10.0):
    cmds.setAttr(L_ARM + ".rotateZ", left)
    cmds.setAttr(R_ARM + ".rotateZ", right)


def _invert_center(cmds, node):
    # Shifter sets the center control inversion per rig, turn it on
    for attr in ("invTx", "invRy"):
        cmds.setAttr("{}.{}".format(node, attr), True)


def test_flip_pair(anim_utils, biped_rig):
    cmds = biped_rig
    _pose_arms(cmds)
    anim_utils.mirror_controls([L_ARM, R_ARM], flip=True)
    assert _rz(cmds, L_ARM) == -10.0
    assert _rz(cmds, R_ARM) == 30.0


def test_pair_order_does_not_matter(anim_utils, biped_rig):
    cmds = biped_rig
    results = []
    for order in ([L_ARM, R_ARM], [R_ARM, L_ARM]):
        _pose_arms(cmds)
        anim_utils.mirror_controls(order, flip=True)
        results.append((_rz(cmds, L_ARM), _rz(cmds, R_ARM)))
    assert results[0] == results[1] == (-10.0, 30.0)


def test_mirror_pair_both_sides_swaps(anim_utils, biped_rig):
    cmds = biped_rig
    _pose_arms(cmds)
    anim_utils.mirror_controls([L_ARM, R_ARM])
    assert (_rz(cmds, L_ARM), _rz(cmds, R_ARM)) == (-10.0, 30.0)


def test_mirror_one_side(anim_utils, biped_rig):
    cmds = biped_rig
    _pose_arms(cmds)
    anim_utils.mirror_controls([L_ARM])
    assert (_rz(cmds, L_ARM), _rz(cmds, R_ARM)) == (30.0, 30.0)


def test_center_control_is_inverted(anim_utils, biped_rig):
    cmds = biped_rig
    _invert_center(cmds, BODY)
    cmds.setAttr(BODY + ".rotateY", 20)
    cmds.setAttr(BODY + ".translateX", 3)
    anim_utils.mirror_controls([BODY])
    assert cmds.getAttr(BODY + ".rotateY") == pytest.approx(-20.0)
    assert cmds.getAttr(BODY + ".translateX") == pytest.approx(-3.0)


def test_one_undo(anim_utils, biped_rig):
    cmds = biped_rig
    cmds.undoInfo(state=True, infinity=True)
    _pose_arms(cmds)
    cmds.setAttr(L_LEG + ".rotateZ", 5)
    cmds.setAttr(R_LEG + ".rotateZ", 7)
    anim_utils.mirror_controls([L_ARM, R_ARM, L_LEG, R_LEG], flip=True)
    assert _rz(cmds, L_LEG) == 7.0
    cmds.undo()
    assert (_rz(cmds, L_ARM), _rz(cmds, R_ARM)) == (30.0, -10.0)
    assert (_rz(cmds, L_LEG), _rz(cmds, R_LEG)) == (5.0, 7.0)


def test_missing_counterpart_is_skipped(anim_utils, biped_rig):
    cmds = biped_rig
    cmds.rename("arm_R0_fk1_ctl", "arm_X0_fk1_ctl")
    cmds.setAttr("arm_L0_fk1_ctl.rotateZ", 40)
    cmds.setAttr(L_LEG + ".rotateZ", 12)
    anim_utils.mirror_controls(["arm_L0_fk1_ctl", L_LEG])
    assert _rz(cmds, R_LEG) == 12.0
    assert _rz(cmds, "arm_X0_fk1_ctl") == 0.0


def test_two_namespaces(anim_utils, two_biped_rigs):
    cmds = two_biped_rigs
    cmds.setAttr("charA:" + L_ARM + ".rotateZ", 30)
    cmds.setAttr("charB:" + L_ARM + ".rotateZ", 45)
    anim_utils.mirror_controls(["charA:" + L_ARM, "charB:" + L_ARM])
    assert _rz(cmds, "charA:" + R_ARM) == 30.0
    assert _rz(cmds, "charB:" + R_ARM) == 45.0


def test_control_side(anim_utils, biped_rig):
    assert anim_utils.get_control_side(L_ARM) == "L"
    assert anim_utils.get_control_side(R_ARM) == "R"
    assert anim_utils.get_control_side("spine_C0_fk0_ctl") is None
    assert anim_utils.get_control_side("|rig|ns:foot_L_ctl") == "L"


def test_control_side_custom_label(anim_utils, biped_rig):
    cmds = biped_rig
    node = cmds.createNode("transform", name="arm_L0_custom_ctl")
    cmds.addAttr(node, longName="side_label", dataType="string")
    cmds.setAttr(node + ".side_label", "C", type="string")
    assert anim_utils.get_control_side(node) is None
    cmds.setAttr(node + ".side_label", "R", type="string")
    assert anim_utils.get_control_side(node) == "R"


def test_mirror_side_left_to_right(anim_utils, biped_rig):
    cmds = biped_rig
    _invert_center(cmds, BODY)
    _pose_arms(cmds)
    cmds.setAttr(L_ARM + ".rotateY", 15)
    cmds.setAttr(BODY + ".rotateY", 20)
    anim_utils.mirror_side([L_ARM, R_ARM, BODY], "L")
    left = cmds.getAttr(L_ARM + ".rotate")[0]
    assert left == pytest.approx((0.0, 15.0, 30.0))
    assert cmds.getAttr(R_ARM + ".rotate")[0] == pytest.approx(left)
    assert cmds.getAttr(BODY + ".rotateY") == pytest.approx(-20.0)


def test_rig_controls(anim_utils, biped_rig):
    controls = anim_utils.get_rig_controls(L_ARM)
    assert len(controls) == 125
    assert R_LEG in controls
    assert anim_utils.get_rig_controls(biped_rig.spaceLocator()[0]) == []


def test_mirror_full_pose_right_to_left(anim_utils, biped_rig):
    cmds = biped_rig
    cmds.setAttr(R_ARM + ".rotateZ", 25)
    cmds.setAttr(R_LEG + ".rotateZ", 12)
    cmds.setAttr(L_LEG + ".rotateZ", -3)
    anim_utils.mirror_full_pose([R_ARM], "R")
    assert _rz(cmds, L_ARM) == 25.0
    assert _rz(cmds, L_LEG) == 12.0
    assert _rz(cmds, R_LEG) == 12.0


def test_flip_full_pose(anim_utils, biped_rig):
    cmds = biped_rig
    _invert_center(cmds, BODY)
    _pose_arms(cmds)
    cmds.setAttr(L_LEG + ".rotateZ", 5)
    cmds.setAttr(R_LEG + ".rotateZ", 7)
    cmds.setAttr(BODY + ".rotateY", 20)
    anim_utils.flip_full_pose([BODY])
    assert (_rz(cmds, L_ARM), _rz(cmds, R_ARM)) == (-10.0, 30.0)
    assert (_rz(cmds, L_LEG), _rz(cmds, R_LEG)) == (7.0, 5.0)
    assert cmds.getAttr(BODY + ".rotateY") == pytest.approx(-20.0)


def test_full_pose_two_rigs(anim_utils, two_biped_rigs):
    cmds = two_biped_rigs
    cmds.setAttr("charA:" + L_LEG + ".rotateZ", 8)
    cmds.setAttr("charB:" + L_LEG + ".rotateZ", 9)
    anim_utils.mirror_full_pose(["charA:" + BODY, "charB:" + L_ARM], "L")
    assert _rz(cmds, "charA:" + R_LEG) == 8.0
    assert _rz(cmds, "charB:" + R_LEG) == 9.0


def test_mirror_pose_wrapper(anim_utils, biped_rig):
    cmds = biped_rig
    assert list(inspect.signature(anim_utils.mirrorPose).parameters) == [
        "flip",
        "nodes",
    ]
    _pose_arms(cmds)
    cmds.select(L_ARM, R_ARM)
    anim_utils.mirrorPose(flip=True)
    assert (_rz(cmds, L_ARM), _rz(cmds, R_ARM)) == (-10.0, 30.0)


def test_empty_list_does_nothing(anim_utils, biped_rig):
    cmds = biped_rig
    _pose_arms(cmds)
    anim_utils.mirror_controls([])
    anim_utils.mirror_controls([], flip=True)
    anim_utils.mirror_side([], "L")
    assert (_rz(cmds, L_ARM), _rz(cmds, R_ARM)) == (30.0, -10.0)


def test_mirror_target_uses_node_namespace(anim_utils, two_biped_rigs):
    target = anim_utils.getMirrorTarget(node="charB:" + L_ARM)
    assert target.name().split("|")[-1] == "charB:" + R_ARM


def test_controls_with_children(setup_path, biped_rig):
    from mgear.core.pickWalk import get_controls_with_children

    cmds = biped_rig
    controls = get_controls_with_children([L_ARM, "arm_L0_fk1_ctl"])
    for ctl in cmds.ls([L_ARM, "arm_L0_fk1_ctl"], long=True):
        assert ctl in controls
    assert cmds.ls("arm_L0_fk2_ctl", long=True)[0] in controls
    assert len(controls) == len(set(controls))
    assert get_controls_with_children([]) == []


def _nest_legs_in_sub_set(cmds):
    # Shifter control sub-groups: a set inside the rig controllers set
    sub_set = cmds.sets([L_LEG, R_LEG], name="rig_legs_grp")
    cmds.sets([L_LEG, R_LEG], remove="rig_controllers_grp")
    cmds.sets(sub_set, add="rig_controllers_grp")
    return sub_set


def test_rig_controls_include_sub_sets(anim_utils, biped_rig):
    cmds = biped_rig
    sub_set = _nest_legs_in_sub_set(cmds)
    controls = anim_utils.get_rig_controls(L_ARM)
    assert L_LEG in controls and R_LEG in controls
    assert sub_set not in controls
    assert len(controls) == 125


def test_flip_full_pose_with_sub_sets(anim_utils, biped_rig):
    cmds = biped_rig
    _nest_legs_in_sub_set(cmds)
    cmds.setAttr(L_LEG + ".rotateZ", 5)
    cmds.setAttr(R_LEG + ".rotateZ", 7)
    anim_utils.flip_full_pose([BODY])
    assert (_rz(cmds, L_LEG), _rz(cmds, R_LEG)) == (7.0, 5.0)


def test_mirror_ignores_non_transforms(anim_utils, biped_rig):
    cmds = biped_rig
    _pose_arms(cmds)
    empty_set = cmds.sets(empty=True, name="some_set")
    anim_utils.mirror_controls([empty_set, L_ARM, R_ARM], flip=True)
    assert (_rz(cmds, L_ARM), _rz(cmds, R_ARM)) == (-10.0, 30.0)


def test_connected_channel_is_skipped(anim_utils, biped_rig):
    cmds = biped_rig
    driver = cmds.createNode("transform", name="driver")
    cmds.connectAttr(driver + ".translateX", R_ARM + ".translateX")
    _pose_arms(cmds)
    cmds.setAttr(L_ARM + ".translateX", 2)
    anim_utils.mirror_controls([L_ARM, R_ARM], flip=True)
    assert (_rz(cmds, L_ARM), _rz(cmds, R_ARM)) == (-10.0, 30.0)
    assert cmds.getAttr(R_ARM + ".translateX") == 0.0


def test_compound_attribute_does_not_block_control(anim_utils, biped_rig):
    cmds = biped_rig
    for node in (L_ARM, R_ARM):
        cmds.addAttr(node, longName="extraVector", attributeType="double3")
        for axis in "XYZ":
            cmds.addAttr(
                node,
                longName="extraVector" + axis,
                attributeType="double",
                parent="extraVector",
            )
    _pose_arms(cmds)
    anim_utils.mirror_controls([L_ARM, R_ARM], flip=True)
    assert (_rz(cmds, L_ARM), _rz(cmds, R_ARM)) == (-10.0, 30.0)


def test_control_sets(anim_utils, biped_rig):
    cmds = biped_rig
    assert anim_utils.get_rig_control_sets([L_ARM]) == []
    _nest_legs_in_sub_set(cmds)
    assert anim_utils.get_rig_control_sets([L_ARM]) == ["legs"]


def test_flip_control_set(anim_utils, biped_rig):
    cmds = biped_rig
    _nest_legs_in_sub_set(cmds)
    _pose_arms(cmds)
    cmds.setAttr(L_LEG + ".rotateZ", 5)
    cmds.setAttr(R_LEG + ".rotateZ", 7)
    anim_utils.flip_full_pose([BODY], control_set="legs")
    assert (_rz(cmds, L_LEG), _rz(cmds, R_LEG)) == (7.0, 5.0)
    assert (_rz(cmds, L_ARM), _rz(cmds, R_ARM)) == (30.0, -10.0)


def test_mirror_control_set_two_rigs(anim_utils, two_biped_rigs):
    cmds = two_biped_rigs
    for ns in ("charA:", "charB:"):
        legs = [ns + L_LEG, ns + R_LEG]
        sub_set = cmds.sets(legs, name=ns + "rig_legs_grp")
        cmds.sets(legs, remove=ns + "rig_controllers_grp")
        cmds.sets(sub_set, add=ns + "rig_controllers_grp")
    nodes = ["charA:" + BODY, "charB:" + BODY]
    assert anim_utils.get_rig_control_sets(nodes) == ["legs"]
    cmds.setAttr("charA:" + L_LEG + ".rotateZ", 4)
    cmds.setAttr("charB:" + L_LEG + ".rotateZ", 6)
    cmds.setAttr("charA:" + L_ARM + ".rotateZ", 9)
    anim_utils.mirror_full_pose(nodes, "L", control_set="legs")
    assert _rz(cmds, "charA:" + R_LEG) == 4.0
    assert _rz(cmds, "charB:" + R_LEG) == 6.0
    assert _rz(cmds, "charA:" + R_ARM) == 0.0


def test_only_changed_values_are_written(anim_utils, biped_rig, monkeypatch):
    cmds = biped_rig
    cmds.setAttr(L_ARM + ".rotateZ", 30)
    written = []
    set_attr = cmds.setAttr

    def spy(plug, *args, **kwargs):
        written.append(plug.split("|")[-1])
        return set_attr(plug, *args, **kwargs)

    monkeypatch.setattr(cmds, "setAttr", spy)
    anim_utils.flip_full_pose([BODY])
    assert sorted(written) == [L_ARM + ".rz", R_ARM + ".rz"]
    assert (_rz(cmds, L_ARM), _rz(cmds, R_ARM)) == (0.0, 30.0)


def _mirror_left_arm(anim_utils, cmds, translate, rotate):
    cmds.setAttr(L_ARM + ".translateY", translate)
    cmds.setAttr(L_ARM + ".rotateZ", rotate)
    anim_utils.mirror_controls([L_ARM])
    return (
        cmds.getAttr(R_ARM + ".translateY"),
        cmds.getAttr(R_ARM + ".rotateZ"),
    )


def test_inches_and_radians(anim_utils, biped_rig):
    cmds = biped_rig
    linear = cmds.currentUnit(query=True, linear=True)
    angle = cmds.currentUnit(query=True, angle=True)
    expected = _mirror_left_arm(anim_utils, cmds, 2.0, 0.5)
    cmds.currentUnit(linear="inch", angle="radian")
    try:
        result = _mirror_left_arm(anim_utils, cmds, 2.0, 0.5)
    finally:
        cmds.currentUnit(linear=linear, angle=angle)
    # same numbers in the scene units: no internal unit leaks
    assert result == pytest.approx(expected)
    assert abs(result[0]) == pytest.approx(2.0)


def test_custom_side_label_fallback(anim_utils, biped_rig):
    cmds = biped_rig
    nodes = {}
    for side, label in (("L", "Left"), ("R", "Right")):
        node = cmds.createNode("transform", name="hand_{}_ctl".format(label))
        for attr, value in (
            ("side_label", side),
            ("L_custom_side_label", "Left"),
            ("R_custom_side_label", "Right"),
        ):
            cmds.addAttr(node, longName=attr, dataType="string")
            cmds.setAttr("{}.{}".format(node, attr), value, type="string")
        nodes[side] = node
    cmds.setAttr(nodes["L"] + ".rotateZ", 25)
    anim_utils.mirror_controls([nodes["L"]])
    assert _rz(cmds, nodes["R"]) == 25.0


def _previous_flip(anim_utils, controls):
    # the previous algorithm: calculateMirrorData for every control, then
    # applyMirror for every value
    import mgear.pymaya as pm

    nodes = [pm.PyNode(c) for c in controls]
    names = set(str(n) for n in nodes)
    entries = []
    for node in nodes:
        target = anim_utils.getMirrorTarget(node=node)
        if target is None:
            continue
        entries.extend(anim_utils.calculateMirrorData(node, target))
        if str(target) not in names:
            entries.extend(anim_utils.calculateMirrorData(target, node))
    for entry in entries:
        try:
            anim_utils.applyMirror(None, entry)
        except Exception:
            pass


def _pose_eight(cmds):
    for i in range(8):
        ns = "c{}:".format(i)
        cmds.setAttr(ns + L_ARM + ".rotateZ", 30 + i)
        cmds.setAttr(ns + L_ARM + ".translateY", 0.5)
        cmds.setAttr(ns + R_LEG + ".rotateX", -12)
        cmds.setAttr(ns + "spine_C0_fk0_ctl.rotateY", 5)


def _trs(anim_utils, cmds, controls):
    channels = anim_utils._MIRROR_TRANSFORM_ATTRS[:-1]
    return {
        "{}.{}".format(c, a): round(cmds.getAttr("{}.{}".format(c, a)), 4)
        for c in controls
        for a in channels
    }


def test_eight_bipeds_same_result_and_faster(
    anim_utils, eight_biped_rigs, biped_rig_file, import_rig_file
):
    import time

    cmds = eight_biped_rigs
    nodes = ["c{}:{}".format(i, BODY) for i in range(8)]
    controls = anim_utils._get_full_pose_controls(nodes)
    assert len(controls) == 1000

    _pose_eight(cmds)
    start = time.time()
    _previous_flip(anim_utils, controls)
    previous_time = time.time() - start
    expected = _trs(anim_utils, cmds, controls)

    import_rig_file(biped_rig_file, ["c{}".format(i) for i in range(8)])
    _pose_eight(cmds)
    start = time.time()
    anim_utils.flip_full_pose(nodes)
    new_time = time.time() - start

    assert _trs(anim_utils, cmds, controls) == expected
    print(
        "flip 1000 controls: previous {:.2f} s, new {:.2f} s ({:.1f}x)".format(
            previous_time, new_time, previous_time / new_time
        )
    )
    assert new_time < previous_time


def _viewport_messages(anim_utils, monkeypatch):
    messages = []
    monkeypatch.setattr(anim_utils.utils, "viewport_message", messages.append)
    return messages


def test_flip_keyed_controls(anim_utils, biped_rig, monkeypatch):
    """Keyed channels get the flipped values, keyed at the current frame."""
    cmds = biped_rig
    messages = _viewport_messages(anim_utils, monkeypatch)
    for node, value in ((L_ARM, 30.0), (R_ARM, -10.0)):
        cmds.setKeyframe(node, attribute="rotateZ", time=1, value=0.0)
        cmds.setKeyframe(node, attribute="rotateZ", time=10, value=value)
    cmds.currentTime(10)
    anim_utils.mirror_controls([L_ARM, R_ARM], flip=True)
    # keyed: the pose stays when the time changes
    cmds.currentTime(1)
    cmds.currentTime(10)
    assert _rz(cmds, L_ARM) == -10.0
    assert _rz(cmds, R_ARM) == 30.0
    assert cmds.keyframe(L_ARM + ".rotateZ", query=True, keyframeCount=True) == 2
    assert len(messages) == 1 and "of <hl>2</hl> control(s)" in messages[0]
    assert "no keys yet" not in messages[0]


def test_mirror_keyed_control(anim_utils, biped_rig, monkeypatch):
    cmds = biped_rig
    messages = _viewport_messages(anim_utils, monkeypatch)
    _pose_arms(cmds)
    anim_utils.mirror_controls([L_ARM])
    expected = _rz(cmds, R_ARM)
    # not keyed, nothing said
    assert messages == []
    assert not cmds.keyframe(R_ARM + ".rotateZ", query=True, keyframeCount=True)
    # the same pose with keys on both arms
    cmds.setAttr(R_ARM + ".rotateZ", -10.0)
    for node in (L_ARM, R_ARM):
        cmds.setKeyframe(node, attribute="rotateZ", time=1)
    anim_utils.mirror_controls([L_ARM])
    cmds.currentTime(2)
    cmds.currentTime(1)
    assert _rz(cmds, R_ARM) == expected
    assert "<hl>1</hl> channel(s)" in messages[0]


def test_animated_pose_keys_the_controls_without_keys(
    anim_utils, biped_rig, monkeypatch
):
    """One keyed control is enough: every value set is keyed, so the pose
    stays consistent."""
    cmds = biped_rig
    messages = _viewport_messages(anim_utils, monkeypatch)
    _pose_arms(cmds)
    cmds.setKeyframe(L_ARM, attribute="rotateZ", time=1)
    assert not cmds.keyframe(R_ARM, query=True, keyframeCount=True)
    anim_utils.mirror_controls([L_ARM, R_ARM], flip=True)
    # the right arm had no keys: now its flipped value is keyed
    assert cmds.keyframe(R_ARM + ".rotateZ", query=True, keyframeCount=True) == 1
    cmds.currentTime(2)
    cmds.currentTime(1)
    assert _rz(cmds, L_ARM) == -10.0
    assert _rz(cmds, R_ARM) == 30.0
    assert "<hl>1</hl> of them had no keys yet" in messages[0]
    # only the right arm keyed: mirroring the left side keys it at frame 5
    cmds.cutKey(L_ARM)
    cmds.currentTime(5)
    _pose_arms(cmds, left=12.0, right=-10.0)
    anim_utils.mirror_side([L_ARM, R_ARM], "L")
    assert cmds.keyframe(R_ARM + ".rotateZ", query=True, keyframeCount=True) == 2
    # the left arm wasn't set, so it gets no keys
    assert not cmds.keyframe(L_ARM, query=True, keyframeCount=True)


def test_mirror_skips_driven_keys(anim_utils, biped_rig):
    """A channel a driven key sets isn't a keyed pose: it is skipped."""
    cmds = biped_rig
    cmds.setDrivenKeyframe(
        R_ARM + ".rotateZ", currentDriver=BODY + ".translateX", value=-10.0
    )
    cmds.setAttr(L_ARM + ".rotateZ", 30.0)
    anim_utils.mirror_controls([L_ARM])
    assert _rz(cmds, R_ARM) == -10.0
