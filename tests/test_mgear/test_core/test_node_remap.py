"""mgear.core.node_remap lookup and matcher tests"""


def _new_scene():
    from maya import cmds

    cmds.file(new=True, force=True)
    return cmds


def test_strip_namespace_path(run_with_maya_standalone, setup_path):
    from mgear.core import node_remap

    assert node_remap.strip_namespace_path("|a:grp|a:b:body") == "|grp|body"
    assert node_remap.strip_namespace_path("body") == "body"


def test_candidates_exported_with_namespace(run_with_maya_standalone, setup_path):
    from mgear.core import node_remap

    cmds = _new_scene()
    grp = cmds.createNode("transform", name="geo")
    cmds.createNode("transform", name="body", parent=grp)
    assert node_remap.find_node_candidates("char:body") == ["|geo|body"]


def test_candidates_scene_with_namespace(run_with_maya_standalone, setup_path):
    from mgear.core import node_remap

    cmds = _new_scene()
    cmds.namespace(add="rig")
    grp = cmds.createNode("transform", name="rig:geo")
    cmds.createNode("transform", name="rig:body", parent=grp)
    assert node_remap.find_node_candidates("body") == ["|rig:geo|rig:body"]


def test_candidates_clash_and_long_name(run_with_maya_standalone, setup_path):
    from mgear.core import node_remap

    cmds = _new_scene()
    for parent in ("grpA", "grpB"):
        grp = cmds.createNode("transform", name=parent)
        cmds.createNode("transform", name="body", parent=grp)

    result = node_remap.find_node_candidates("body", long_name="|grpA|body")
    assert result == ["|grpA|body"]
    ambiguous = node_remap.find_node_candidates("body")
    assert sorted(ambiguous) == ["|grpA|body", "|grpB|body"]
    # A partial path name is used as its own long name.
    assert node_remap.find_node_candidates("grpB|body") == ["|grpB|body"]


def test_candidates_namespace_remap(run_with_maya_standalone, setup_path):
    from mgear.core import node_remap

    cmds = _new_scene()
    cmds.namespace(add="new")
    cmds.createNode("transform", name="new:body")
    cmds.createNode("transform", name="body")
    result = node_remap.find_node_candidates("old:body", namespace="new:")
    assert result == ["|new:body"]
    assert node_remap.find_node_candidates("old:body", namespace="") == ["|body"]


def test_candidates_node_type(run_with_maya_standalone, setup_path):
    from mgear.core import node_remap

    cmds = _new_scene()
    grp = cmds.createNode("transform", name="grp")
    cmds.createNode("transform", name="spine", parent=grp)
    cmds.createNode("joint", name="spine")
    assert node_remap.find_node_candidates("spine", node_type="joint") == ["|spine"]
    assert node_remap.find_node_candidates("missing") == []


def test_match_by_pattern(setup_path):
    from mgear.core import node_remap

    targets = ["|rig:arm_R0_jnt", "spine_jnt", "dup", "|a|dup"]
    assert node_remap.match_by_pattern(["arm_L0_jnt"], targets, "_L", "_R") == {
        "arm_L0_jnt": "|rig:arm_R0_jnt"
    }
    assert node_remap.match_by_pattern(
        ["old_spine_jnt"], targets, "^old_", "", regex=True
    ) == {"old_spine_jnt": "spine_jnt"}
    # No unique target: clash or no hit.
    assert node_remap.match_by_pattern(["dup", "nope"], targets, "x", "y") == {}


def test_match_by_prefix_and_side(setup_path):
    from mgear.core import node_remap

    targets = ["new_spine", "leg_R0_jnt", "L_hand", "R_hand"]
    assert node_remap.match_by_prefix(
        ["old_spine"], targets, strip="old_", add="new_"
    ) == {"old_spine": "new_spine"}
    assert node_remap.match_by_side_swap(["leg_L0_jnt", "R_hand", "Lip"], targets) == {
        "leg_L0_jnt": "leg_R0_jnt",
        "R_hand": "L_hand",
    }


def test_match_by_similarity(setup_path):
    from mgear.core import node_remap

    targets = ["spine_C0_0_jnt", "neck_C0_0_jnt"]
    assert node_remap.match_by_similarity(["spine_C0_jnt"], targets) == {
        "spine_C0_jnt": "spine_C0_0_jnt"
    }
    assert node_remap.match_by_similarity(["zzz"], targets) == {}


def test_match_by_position(setup_path):
    from mgear.core import node_remap

    sources = {"jntA": (1.0, 2.0, 3.0), "far": (10.0, 0.0, 0.0), "none": None}
    targets = {"jntB": (1.0, 2.0, 3.001), "jntC": (1.0, 2.0, 3.5)}
    assert node_remap.match_by_position(sources, targets, tolerance=0.01) == {
        "jntA": "jntB"
    }
