"""mgear_curveCns and mgear_rollSplineKine array input test (C++ plug-in)"""

import pytest

# Matrix array inputs registered with setIndexMatters(false), so a
# connection does not have to pick an index. Maya ignores setIndexMatters
# while the attribute is not a multi yet, so setArray(true) comes first.
ARRAY_INPUTS = (
    ("mgear_curveCns", "inputs"),
    ("mgear_rollSplineKine", "ctlParent"),
    ("mgear_rollSplineKine", "inputs"),
)


def _attribute(cmds, node, attr):
    """The MFnAttribute of an attribute of a node."""
    from maya.api import OpenMaya

    selection = OpenMaya.MSelectionList()
    selection.add(node)
    node_fn = OpenMaya.MFnDependencyNode(selection.getDependNode(0))
    return OpenMaya.MFnAttribute(node_fn.attribute(attr))


@pytest.mark.parametrize("node_type, attr", ARRAY_INPUTS)
def test_array_input_index_does_not_matter(solvers, node_type, attr):
    cmds = solvers
    attribute = _attribute(cmds, cmds.createNode(node_type), attr)
    assert attribute.array
    assert not attribute.indexMatters


@pytest.mark.parametrize("node_type, attr", ARRAY_INPUTS)
def test_array_input_takes_next_available(solvers, node_type, attr):
    cmds = solvers
    plug = "{}.{}".format(cmds.createNode(node_type), attr)
    for _ in range(3):
        source = cmds.createNode("transform") + ".worldMatrix[0]"
        cmds.connectAttr(source, plug, nextAvailable=True)
    assert cmds.getAttr(plug, multiIndices=True) == [0, 1, 2]
