"""Shifter stackable chain helpers test"""

import pytest

COMPATIBLE = ("chain_spring_gravity_02", "lite_chain_stack_02")


@pytest.mark.parametrize(
    "index, offset, expected",
    [(0, 0, 0), (2, 0, 2), (0, 1, 1), (1, 1, 2), (2, 1, 2), (0, 5, 2)],
)
def test_master_index(setup_path, index, offset, expected):
    from mgear.shifter.component import chain_stack

    assert chain_stack.master_index(index, offset, 3) == expected


def test_check_valid_master(chain_guide):
    import mgear.pymaya as pm
    from mgear.shifter.component import chain_stack

    master = chain_guide(name="master")
    slave = chain_guide(name="slave")
    name, warning = chain_stack.check_master_chain(
        pm.PyNode(slave), pm.PyNode(master), COMPATIBLE
    )
    assert (name, warning) == ("master_L0", None)


def test_check_own_root(chain_guide):
    import mgear.pymaya as pm
    from mgear.shifter.component import chain_stack

    root = pm.PyNode(chain_guide())
    name, warning = chain_stack.check_master_chain(root, root, COMPATIBLE)
    assert name is None
    assert "Cycle" in warning


def test_check_incompatible_type(chain_guide):
    import mgear.pymaya as pm
    from mgear.shifter import guide
    from mgear.shifter.component import chain_stack

    root = chain_guide()
    guide.Rig().drawNewComponent(pm.PyNode("guide"), "control_01", showUI=False)
    name, warning = chain_stack.check_master_chain(
        pm.PyNode(root), pm.PyNode("control_C0_root"), COMPATIBLE
    )
    assert name is None
    for comp_type in COMPATIBLE:
        assert comp_type in warning


def test_check_master_too_short(chain_guide):
    import mgear.pymaya as pm
    from mgear.shifter.component import chain_stack

    master = chain_guide(name="master", positions=chain_guide.positions[:3])
    slave = chain_guide(name="slave")
    name, warning = chain_stack.check_master_chain(
        pm.PyNode(slave), pm.PyNode(master), COMPATIBLE
    )
    assert name is None
    assert "4" in warning and "3" in warning
