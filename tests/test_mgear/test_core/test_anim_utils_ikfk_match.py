"""Tests for the IK/FK match of anim_utils on built Shifter rigs."""

import pytest


@pytest.fixture(scope="module")
def no_roll_ctl_rig_file(rig_plugins, setup_path, tmp_path_factory):
    """A game_biped rig with the left foot "Use Roll Ctl" off, saved once.

    Without the roll control, EPIC_foot_01 drives the foot roll and bank from
    the UI host attributes, through the ``roll_cnx`` / ``bank_cnx`` plugs.

    Returns:
        str: Path of the saved Maya ASCII file.
    """
    from maya import cmds

    from mgear import shifter
    from mgear.shifter import io

    cmds.file(new=True, force=True)
    io.import_sample_template("game_biped.sgt")
    cmds.setAttr("foot_L0_root.useRollCtl", False)
    cmds.select("guide")
    shifter.Rig().buildFromSelection()
    cmds.delete("guide")
    folder = tmp_path_factory.mktemp("no_roll_ctl")
    path = str(folder / "rig.ma").replace("\\", "/")
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii", force=True)
    return path


def _roll_bank_sources(cmds):
    """The UI host plugs feeding the foot roll_cnx and bank_cnx."""
    plugs = []
    for name in ("roll_cnx", "bank_cnx"):
        plug = "foot_L0_root.{}".format(name)
        sources = cmds.listConnections(plug, source=True, destination=False, plugs=True)
        assert sources, "{} has no input".format(plug)
        plugs.append(sources[0])
    return plugs


def test_fk_to_ik_resets_foot_roll_bank(no_roll_ctl_rig_file):
    """FK > IK with the foot roll control off resets roll and bank (#654)."""
    from maya import cmds

    from mgear.core.dagmenu.sections import control

    cmds.file(no_roll_ctl_rig_file, open=True, force=True)
    roll_plug, bank_plug = _roll_bank_sources(cmds)
    assert roll_plug.startswith("legUI_L0_ctl.")

    cmds.setAttr("legUI_L0_ctl.leg_blend", 0.0)
    cmds.setAttr(roll_plug, 25.0)
    cmds.setAttr(bank_plug, 10.0)

    control.switch_ikfk("legUI_L0_ctl", "leg_blend")

    assert cmds.getAttr("legUI_L0_ctl.leg_blend") == pytest.approx(1.0)
    assert cmds.getAttr(roll_plug) == pytest.approx(0.0)
    assert cmds.getAttr(bank_plug) == pytest.approx(0.0)
