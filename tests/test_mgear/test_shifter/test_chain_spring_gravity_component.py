"""Shifter chain_spring_gravity_02 component test"""

import pytest


def _build(attr_prefix=True):
    from maya import cmds
    from mgear import shifter

    # anim params of each component, not shared by component type
    cmds.setAttr("guide.attrPrefixName", attr_prefix)
    cmds.select("guide")
    rig = shifter.Rig()
    rig.buildFromSelection()
    cmds.select(clear=True)
    return rig


def _position(node):
    from maya import cmds

    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def _matrix(node):
    from maya import cmds

    return cmds.xform(node, query=True, worldSpace=True, matrix=True)


def _anim_attr(attr, name="chain"):
    """Return the node.attr of a component anim param.

    The params are on the global control, prefixed with the component name
    (``attrPrefixName`` is on, see ``_build``).
    """
    from maya import cmds

    plug = "global_C0_ctl.{}_{}".format(name, attr)
    assert cmds.objExists(plug), plug
    return plug


def _joints(prefix="chain_L0"):
    from maya import cmds

    return sorted(
        cmds.ls(prefix + "_*_jnt", type="joint"),
        key=lambda name: int(name.split("_")[-2]),
    )


def _mirror(positions):
    return tuple((-x, y, z) for x, y, z in positions)


def _step(frames):
    """Step the time one frame at a time, as the spring solver needs."""
    from maya import cmds

    start = int(cmds.currentTime(query=True))
    for frame in range(start + 1, start + frames + 1):
        cmds.currentTime(frame)


def _scale_rig(scale=2.0):
    """Scale the global control and return the scale."""
    from maya import cmds

    for axis in "xyz":
        cmds.setAttr("global_C0_ctl.s" + axis, scale)
    return scale


def _assert_scaled(joints, rest, scale=2.0, abs_tol=1e-4):
    """Check the joints are at the scaled rest positions, with world scale."""
    from maya import cmds

    for jnt, position in zip(joints, rest):
        expected = [v * scale for v in position]
        assert _position(jnt) == pytest.approx(expected, abs=abs_tol), jnt
        world_scale = cmds.xform(jnt, query=True, worldSpace=True, scale=True)
        assert [abs(v) for v in world_scale] == pytest.approx(
            [scale] * 3, abs=1e-3
        ), jnt


def test_guide_params(chain_guide):
    from maya import cmds

    root = chain_guide()
    for node in ("chain_L0_0_loc", "chain_L0_1_loc", "chain_L0_2_loc"):
        assert cmds.objExists(node), node
    assert cmds.objExists("chain_L0_blade")
    defaults = {
        "mirrorBehaviour": False,
        "extraTweak": False,
        "tweakEnd": False,
        "masterChainLocal": "",
        "masterChainGlobal": "",
        "cnxOffset": 0,
        "useIndex": False,
        "parentJointIndex": -1,
    }
    for key, value in defaults.items():
        assert cmds.getAttr("{}.{}".format(root, key)) == value, key


def test_default_param_names(chain_guide):
    from maya import cmds

    chain_guide()
    _build(attr_prefix=False)
    for name in ("spring_intensity", "damping_0", "collide_softness_2"):
        assert cmds.objExists("global_C0_ctl.chainSpringGravity_" + name), name


def test_rest_pose_matches_v01(chain_guide):
    chain_guide(comp="chain_spring_gravity_01", name="old")
    chain_guide(name="new")
    _build()
    old = _joints("old_L0")
    new = _joints("new_L0")
    assert len(old) == len(new) == 3
    for old_jnt, new_jnt in zip(old, new):
        assert _matrix(new_jnt) == pytest.approx(_matrix(old_jnt), abs=1e-4)


def test_spring_intensity_off_keeps_fk(chain_guide):
    from maya import cmds

    chain_guide()
    _build()
    joints = _joints()
    rest = [_position(j) for j in joints]
    for frame in range(1, 6):
        cmds.currentTime(frame)
        cmds.setAttr("global_C0_ctl.tz", frame * 0.5)
    for jnt, position in zip(joints, rest):
        moved = [position[0], position[1], position[2] + 2.5]
        assert _position(jnt) == pytest.approx(moved, abs=1e-4)


def test_mirror_behaviour(chain_guide):
    from maya import cmds

    chain_guide(mirrorBehaviour=True)
    chain_guide(
        side="R", positions=_mirror(chain_guide.positions), mirrorBehaviour=True
    )
    _build()
    for side in "LR":
        cmds.setAttr("chain_{}0_fk0_ctl.rz".format(side), 30)
    for left, right in zip(_joints("chain_L0"), _joints("chain_R0")):
        x, y, z = _position(left)
        assert _position(right) == pytest.approx((-x, y, z), abs=1e-4)
        for axis in "xyz":
            assert cmds.getAttr("{}.s{}".format(right, axis)) > 0


STACK_CASES = [
    (comp, setting, side)
    for comp in ("lite_chain_stack_02", "chain_stack_01")
    for setting in ("masterChainLocal", "masterChainGlobal")
    for side in ("L", "R")
]


@pytest.mark.parametrize("comp, setting, side", STACK_CASES)
def test_stack_follows_spring_master(chain_guide, comp, setting, side):
    from maya import cmds

    positions = chain_guide.positions if side == "L" else _mirror(chain_guide.positions)
    chain_guide(side=side, positions=positions, mirrorBehaviour=True)
    chain_guide(
        comp=comp,
        name="stack",
        side=side,
        positions=positions,
        **{setting: "chain_{}0".format(side)}
    )
    _build()
    cmds.setAttr("chain_{}0_fk0_ctl.rz".format(side), 30)
    cmds.setAttr("chain_{}0_fk1_ctl.ry".format(side), 20)
    for i in range(3):
        master = _position("chain_{}0_fk{}_ctl".format(side, i))
        slave = _position("stack_{}0_fk{}_ctl".format(side, i))
        assert slave == pytest.approx(master, abs=1e-4), i


@pytest.mark.parametrize("setting", ["masterChainLocal", "masterChainGlobal"])
def test_spring_slave_follows_lite_master(chain_guide, setting):
    from maya import cmds

    chain_guide(comp="lite_chain_stack_02", name="lite")
    chain_guide(**{setting: "lite_L0"})
    _build()
    cmds.setAttr("lite_L0_fk0_ctl.rz", 30)
    cmds.setAttr("lite_L0_fk1_ctl.ry", 20)
    for i in range(3):
        master = _position("lite_L0_fk{}_ctl".format(i))
        slave = _position("chain_L0_fk{}_ctl".format(i))
        assert slave == pytest.approx(master, abs=1e-4), i


def test_chain_stack_under_spring_master(chain_guide):
    from maya import cmds

    chain_guide()
    chain_guide(comp="chain_stack_01", name="stack", masterChainGlobal="chain_L0")
    _build()
    for channel in ("mid_twist", "tip_twist", "mid_wide", "tip_depth"):
        assert cmds.isConnected(
            "chain_L0_root.{}_out".format(channel),
            "stack_L0_root.{}_in".format(channel),
        ), channel


def test_slave_follows_master(chain_guide):
    from maya import cmds

    chain_guide(name="master")
    chain_guide(name="slave", masterChainLocal="master_L0")
    _build()
    cmds.setAttr("master_L0_fk0_ctl.rz", 30)
    for i in range(3):
        master = _matrix("master_L0_fk{}_ctl".format(i))
        slave = _matrix("slave_L0_fk{}_ctl".format(i))
        assert slave == pytest.approx(master, abs=1e-4)


def test_local_blend_off(chain_guide):
    from maya import cmds

    chain_guide(name="master")
    chain_guide(name="slave", masterChainLocal="master_L0")
    _build()
    joints = _joints("slave_L0")
    rest = [_position(j) for j in joints]
    cmds.setAttr(_anim_attr("localBlend", "slave"), 0)
    cmds.setAttr("master_L0_fk0_ctl.rz", 30)
    for jnt, position in zip(joints, rest):
        assert _position(jnt) == pytest.approx(position, abs=1e-4)


def test_offset_past_master_end(chain_guide):
    from maya import cmds

    chain_guide(name="master")
    chain_guide(name="slave", masterChainLocal="master_L0", cnxOffset=1)
    _build()
    for i, master_i in enumerate((1, 2, 2)):
        blend = cmds.listConnections(
            "slave_L0_fk{}_local_in.translate".format(i),
            source=True,
            destination=False,
        )[0]
        source = cmds.listConnections(
            blend + ".inTranslate2", source=True, destination=False
        )[0]
        assert source == "master_L0_fk{}_local_out".format(master_i)


def test_master_without_channels(chain_guide):
    from maya import cmds

    chain_guide(comp="lite_chain_stack_02", name="lite")
    chain_guide(masterChainLocal="lite_L0")
    _build()
    assert not cmds.listConnections(
        "chain_L0_root.mid_twist_in", source=True, destination=False
    )
    assert cmds.getAttr("chain_L0_root.mid_twist_in") == 0
    assert cmds.getAttr("chain_L0_root.mid_wide_in") == 1


def test_global_scale_at_rest(chain_guide):
    from maya import cmds

    chain_guide()
    _build()
    joints = _joints()
    rest = [_position(j) for j in joints]
    nodes = ["chain_L0_fk{}_ctl".format(i) for i in range(3)]
    nodes += ["chain_L0_spring{}".format(i) for i in range(3)]
    rest_local = [cmds.xform(n, query=True, matrix=True) for n in nodes]
    _scale_rig()
    _step(1)
    _assert_scaled(joints, rest)
    for name, matrix in zip(nodes, rest_local):
        local = cmds.xform(name, query=True, matrix=True)
        assert local == pytest.approx(matrix, abs=1e-4), name


def test_spring_settles_after_scaling(chain_guide):
    from maya import cmds

    chain_guide()
    _build()
    cmds.setAttr(_anim_attr("spring_intensity"), 1)
    _step(5)
    joints = _joints()
    rest = [_position(j) for j in joints]
    _scale_rig()
    _step(60)
    _assert_scaled(joints, rest, abs_tol=1e-2)


def test_options_under_scale(chain_guide):
    positions = _mirror(chain_guide.positions)
    chain_guide(side="R", name="master", positions=positions)
    chain_guide(
        side="R",
        positions=positions,
        mirrorBehaviour=True,
        extraTweak=True,
        tweakEnd=True,
        masterChainLocal="master_R0",
    )
    _build()
    joints = _joints("chain_R0")
    assert len(joints) == 4
    rest = [_position(j) for j in joints]
    _scale_rig()
    _step(1)
    _assert_scaled(joints, rest)


def test_gravity_not_scaled(chain_guide):
    from maya import cmds

    chain_guide()
    _build()
    gravity = _anim_attr("gravity_0")
    cmds.setAttr(gravity, 1)
    _scale_rig()
    solver = cmds.listConnections(
        gravity, source=False, destination=True, type="mgear_springGravityNode"
    )[0]
    assert cmds.getAttr(solver + ".gravity") == pytest.approx(1)


def test_extra_tweak_moves_its_joint(chain_guide):
    from maya import cmds

    chain_guide(extraTweak=True)
    _build()
    joints = _joints()
    rest = [_position(j) for j in joints]
    tweak = "chain_L0_extraTweak1_ctl"
    tweak_rest = _position(tweak)
    cmds.setAttr(tweak + ".ty", 0.5)
    offset = [a - b for a, b in zip(_position(tweak), tweak_rest)]
    assert sum(o * o for o in offset) == pytest.approx(0.25, abs=1e-4)
    for i, (jnt, position) in enumerate(zip(joints, rest)):
        if i == 1:
            position = [p + o for p, o in zip(position, offset)]
        assert _position(jnt) == pytest.approx(position, abs=1e-4), jnt


def test_tweak_visibility(chain_guide):
    from maya import cmds

    chain_guide(extraTweak=True)
    _build()
    vis = _anim_attr("Tweak_vis")
    for i in range(3):
        ctl = "chain_L0_extraTweak{}_ctl".format(i)
        for shape in cmds.listRelatives(ctl, shapes=True):
            assert cmds.isConnected(vis, shape + ".visibility")
            assert cmds.getAttr(shape + ".visibility") is False


@pytest.mark.parametrize("side", ["L", "R"])
def test_tweak_end_tip_joint(chain_guide, side):
    positions = chain_guide.positions if side == "L" else _mirror(chain_guide.positions)
    chain_guide(side=side, positions=positions, mirrorBehaviour=True, tweakEnd=True)
    _build()
    joints = _joints("chain_{}0".format(side))
    assert len(joints) == 4
    assert _position(joints[-1]) == pytest.approx(positions[-1], abs=1e-4)


def test_child_follows_tweak_end(chain_guide):
    from maya import cmds

    import mgear.pymaya as pm
    from mgear.shifter import guide

    chain_guide(tweakEnd=True)
    guide.Rig().drawNewComponent(
        pm.PyNode("chain_L0_2_loc"), "control_01", showUI=False
    )
    _build()
    control = cmds.ls("control_*_ctl")[0]
    rest = _position(control)
    cmds.setAttr("chain_L0_tweakEnd_ctl.ty", 0.5)
    moved = _position(control)
    assert moved != pytest.approx(rest, abs=1e-3)
    assert moved == pytest.approx(_position("chain_L0_tweakEnd_ctl"), abs=1e-3)
