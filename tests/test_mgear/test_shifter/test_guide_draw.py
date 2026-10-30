"""Shifter guide draw tests

Drawing a guide template must create the same guide as before the guide
draw performance change: transforms, hierarchy, world matrices, attribute
values, connections and node types. Only guide icon shape names may
differ, so shapes are compared by index. The expected snapshots are stored
gzipped in ``data/`` (``check_golden``).
"""

import pytest

TEMPLATES = ("biped.sgt", "EPIC_metahuman_y_up.sgt")
# Connections that depend on the Maya version, not on the guide draw: Maya
# 2025 and newer connect a deformer's original shape to its
# originalGeometry, Maya 2024 doesn't
VERSION_DEPENDENT_ATTRS = (".originalGeometry[",)


def plug_key(plug, shape_index):
    """Return a plug name with shapes named by their parent and index.

    Args:
        plug (str): Plug name, ``node.attribute``.
        shape_index (dict): Shape long name to ``parent|shape#index``.

    Returns:
        str: The normalized plug name.
    """
    from maya import cmds

    node, _, attr = plug.partition(".")
    long_name = (cmds.ls(node, long=True) or [node])[0]
    return "{}.{}".format(shape_index.get(long_name, long_name), attr)


def attribute_values(node):
    """Return the user-defined attribute values of a node."""
    from maya import cmds

    values = {}
    for attr in cmds.listAttr(node, userDefined=True) or []:
        try:
            values[attr] = cmds.getAttr("{}.{}".format(node, attr))
        except (RuntimeError, ValueError):
            values[attr] = None
    return values


def guide_snapshot(describe_shapes, default_nodes):
    """Describe the guide in the scene, independent of shape names.

    Args:
        describe_shapes (callable): The ``describe_shapes`` fixture.
        default_nodes (set): Nodes of an empty scene, left out.

    Returns:
        dict: transforms, node type counts and connections.
    """
    from maya import cmds

    transforms = cmds.ls("guide", dag=True, long=True, type="transform")
    shape_index = {}
    for transform in transforms:
        shapes = cmds.listRelatives(transform, shapes=True, fullPath=True) or []
        for index, shape in enumerate(shapes):
            shape_index[shape] = "{}|shape#{}".format(transform, index)

    nodes = [n for n in cmds.ls(long=True) if n not in default_nodes]
    type_counts = {}
    connections = set()
    for node in nodes:
        node_type = cmds.nodeType(node)
        type_counts[node_type] = type_counts.get(node_type, 0) + 1
        pairs = cmds.listConnections(
            node, source=True, destination=False, connections=True, plugs=True
        )
        pairs = pairs or []
        for dst, src in zip(pairs[::2], pairs[1::2]):
            if any(attr in dst for attr in VERSION_DEPENDENT_ATTRS):
                continue
            connections.add(
                "{} -> {}".format(
                    plug_key(src, shape_index), plug_key(dst, shape_index)
                )
            )

    return {
        "transforms": {
            t: {
                "type": cmds.nodeType(t),
                "matrix": cmds.xform(t, query=True, matrix=True, worldSpace=True),
                "attributes": attribute_values(t),
                "shapes": describe_shapes(t, names=False),
            }
            for t in transforms
        },
        "node_types": type_counts,
        "connections": sorted(connections),
        "selection": cmds.ls(selection=True),
    }


@pytest.fixture
def default_nodes(rig_plugins, setup_path):
    """Long names of the nodes in an empty scene."""
    from maya import cmds

    cmds.file(new=True, force=True)
    return set(cmds.ls(long=True))


@pytest.mark.parametrize("template", TEMPLATES)
def test_draw_guide_unchanged(
    import_template, describe_shapes, default_nodes, check_golden, template
):
    import_template(template)
    snapshot = guide_snapshot(describe_shapes, default_nodes)
    check_golden("guide_draw_" + template.split(".")[0], snapshot)


def test_rig_controls_unchanged(import_template, describe_shapes, check_golden):
    from maya import cmds

    from mgear import shifter

    # the biped has few control buffers: most controls are built from icons
    import_template("biped.sgt")
    cmds.select("guide")
    shifter.Rig().buildFromSelection()

    controls = sorted(cmds.ls("*_ctl", type="transform"))
    assert len(controls) > 100
    check_golden(
        "rig_controls_biped",
        {ctl: describe_shapes(ctl) for ctl in controls},
    )


def test_x_ray_shapes_checked_once(rig_plugins, setup_path, count_calls):
    from maya import cmds

    import mgear.pymaya as pm
    from mgear.shifter import guide
    from mgear.shifter import utils as shifter_utils

    cmds.file(new=True, force=True)
    guide.Rig().drawNewComponent(None, "control_01", showUI=False)
    root = pm.PyNode("control_C0_root")
    calls = count_calls(
        cmds,
        "listConnections",
        record=lambda args, kwargs: (
            args[0] if str(args[0]).endswith(".alwaysDrawOnTop") else None
        ),
    )
    guide.Rig().drawNewComponent(root, "arm_2jnt_01", showUI=False)

    x_ray = shifter_utils.get_guide_x_ray_plug("guide")
    shapes = cmds.listRelatives(
        cmds.ls("arm_C0_*", type="transform"), shapes=True, fullPath=True
    )
    # each shape is checked once, even when shapes are added to a locator
    assert len(calls) == len(set(calls))
    for shape in shapes:
        if cmds.attributeQuery("alwaysDrawOnTop", node=shape, exists=True):
            assert cmds.listConnections(
                shape + ".alwaysDrawOnTop", source=True, plugs=True
            ) == [x_ray]


def test_control_buffer_replace_shapes(import_template, describe_shapes):
    from maya import cmds

    import mgear.pymaya as pm
    from mgear.core import curve

    guide_root = import_template("EPIC_metahuman_y_up.sgt")
    buffers = [
        pm.PyNode(name)
        for name in cmds.listRelatives("controllers_org", children=True)
        if name.endswith("_controlBuffer")
    ]
    data = curve.collect_curve_data(objs=buffers)
    name = next(n for n in data["curves_names"] if len(data[n]["shapes_names"]) > 1)
    before = describe_shapes(name, names=False)
    transforms = set(cmds.ls(type="transform"))

    curve.create_curve_from_data_by_name(
        name, data, replaceShape=True, model=guide_root
    )

    assert describe_shapes(name, names=False) == before
    assert set(cmds.ls(type="transform")) == transforms


def test_reference_shapes_scaled_parent(
    rig_plugins, setup_path, describe_shapes, check_golden
):
    from maya import cmds

    import mgear.pymaya as pm
    from mgear.shifter import guide

    # control_01 adds a reference axis and joint to its root. They bake the
    # world scale of the element they are added to.
    cmds.file(new=True, force=True)
    guide.Rig().drawNewComponent(None, "control_01", showUI=False)
    cmds.setAttr("control_C0_root.rotate", 20, 35, -10)
    cmds.setAttr("control_C0_root.scale", 2, 1, 0.5)
    guide.Rig().drawNewComponent(
        pm.PyNode("control_C0_root"), "control_01", showUI=False
    )

    transforms = cmds.ls("control_C1_*", type="transform", long=True)
    assert transforms
    check_golden(
        "reference_shapes_scaled_parent",
        {t: describe_shapes(t, names=False) for t in transforms},
    )


def test_draw_guide_selection(rig_plugins, setup_path, count_calls):
    import json
    import os

    from maya import cmds

    import mgear.pymaya as pm
    from mgear import shifter
    from mgear.shifter import io

    template = os.path.join(
        os.path.dirname(io.__file__), "component", "_templates", "biped.sgt"
    )
    with open(template) as f:
        conf = json.load(f)

    cmds.file(new=True, force=True)
    selects = count_calls(pm, "select")
    rig = shifter.Rig()
    rig.guide.set_from_dict(conf)
    rig.guide.draw_guide()

    roots = {str(comp.root) for comp in rig.guide.components.values()}
    root_selects = [args for args in selects if args and str(args[0]) in roots]
    # one root selection at the end, not one per component
    assert len(root_selects) == 1
    last = rig.guide.components[rig.guide.componentsIndex[-1]].root
    assert cmds.ls(selection=True, long=True) == [last.longName()]


def test_duplicate_selection(import_template):
    from maya import cmds

    import mgear.pymaya as pm
    from mgear import shifter

    import_template("biped.sgt")
    shifter.Rig().guide.duplicate(pm.PyNode("arm_L0_root"))

    # the duplicated branch root is selected
    selection = cmds.ls(selection=True)
    assert len(selection) == 1
    assert selection[0].startswith("arm_L") and selection[0] != "arm_L0_root"
