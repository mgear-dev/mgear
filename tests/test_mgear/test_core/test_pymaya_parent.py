"""mgear.pymaya parent wrapper tests"""

import pytest


@pytest.fixture
def pymaya(setup_path):
    """The mgear.pymaya package, in a new scene with a grp and two nodes."""
    from maya import cmds

    import mgear.pymaya as pm

    cmds.file(new=True, force=True)
    cmds.createNode("transform", name="grp")
    cmds.createNode("transform", name="a")
    cmds.createNode("transform", name="b")
    return pm


def _parent_of(name):
    from maya import cmds

    return cmds.listRelatives(name, parent=True, fullPath=True)


def test_parent_moves_the_object(pymaya):
    result = pymaya.parent("a", "grp")
    assert _parent_of("a") == ["|grp"]
    assert [node.name() for node in result] == ["a"]


def test_parent_to_the_current_parent_does_not_raise(pymaya):
    # Maya 2024 raises "Maya command error" on the second call
    pymaya.parent("a", "grp")
    result = pymaya.parent("a", "grp")
    assert _parent_of("a") == ["|grp"]
    assert [node.name() for node in result] == ["a"]


def test_parent_skips_only_the_objects_already_under_the_parent(pymaya):
    pymaya.parent("a", "grp")
    result = pymaya.parent(pymaya.PyNode("a"), pymaya.PyNode("b"), "grp")
    assert _parent_of("a") == ["|grp"]
    assert _parent_of("b") == ["|grp"]
    assert [node.name() for node in result] == ["a", "b"]


def test_parent_accepts_a_list_of_objects(pymaya):
    pymaya.parent("a", "grp")
    pymaya.parent(["a", "b"], "grp")
    assert _parent_of("b") == ["|grp"]


def test_parent_world_still_works(pymaya):
    pymaya.parent("a", "grp")
    pymaya.parent("a", world=True)
    assert _parent_of("a") is None
