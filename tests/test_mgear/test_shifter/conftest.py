"""Fixtures shared by the Shifter build tests."""

import pytest


@pytest.fixture
def build_rig(rig_plugins, setup_path):
    """Function building a small Shifter rig in a new scene.

    The guide has a ``control_C0`` root with an ``arm_C0`` (arm_2jnt_01)
    below it.

    Returns:
        callable: Called with ``data_collector_path`` (str, optional) to turn
            the data collector on, and ``pre_step`` / ``post_step`` (str,
            optional) as pre / post custom step paths (comma separated for
            several steps). Returns the built shifter.Rig.
    """

    def build(data_collector_path=None, post_step=None, pre_step=None):
        from maya import cmds

        import mgear.pymaya as pm
        from mgear import shifter
        from mgear.shifter import guide

        cmds.file(new=True, force=True)
        guide.Rig().drawNewComponent(None, "control_01", showUI=False)
        root = pm.PyNode("control_C0_root")
        guide.Rig().drawNewComponent(root, "arm_2jnt_01", showUI=False)
        if data_collector_path:
            cmds.setAttr("guide.data_collector", True)
            cmds.setAttr(
                "guide.data_collector_path",
                data_collector_path,
                type="string",
            )
        if pre_step:
            cmds.setAttr("guide.doPreCustomStep", True)
            cmds.setAttr("guide.preCustomStep", pre_step, type="string")
        if post_step:
            cmds.setAttr("guide.doPostCustomStep", True)
            cmds.setAttr("guide.postCustomStep", post_step, type="string")
        cmds.select("guide")
        rig = shifter.Rig()
        rig.buildFromSelection()
        cmds.select(clear=True)
        return rig

    return build


@pytest.fixture
def curve_data_calls(setup_path, count_calls):
    """Record the controls passed to curve.collect_curve_data.

    Only per-control calls (the component build data collection) are
    recorded. The build also makes one ``collect_curve_data(objs=[])`` call
    of its own, which is ignored.
    """
    from mgear.core import curve

    return count_calls(
        curve,
        "collect_curve_data",
        record=lambda args, kwargs: args[0] if args else None,
    )


@pytest.fixture
def lips_guide(lips_face, rig_plugins):
    """Function drawing a lips_01 guide for the lips_face mouth.

    Returns:
        callable: Called with parent (guide locator, optional), aim (aim
            locator world position), lip (lip locator height above the
            root: the thickness) and guide settings. Returns the guide root
            name.
    """
    from maya import cmds

    import mgear.pymaya as pm
    from mgear.shifter import guide

    def draw(parent=None, aim=(0, 0, 1.2), lip=0.03, **settings):
        before = set(cmds.ls("*_root", type="transform"))
        guide.Rig().drawNewComponent(
            pm.PyNode(parent) if parent else None, "lips_01", showUI=False
        )
        root = (set(cmds.ls("*_root", type="transform")) - before).pop()
        cmds.xform(root, worldSpace=True, translation=(0, 0, 0.75))
        cmds.xform(root.replace("_root", "_aim"), worldSpace=True, translation=aim)
        cmds.xform(
            root.replace("_root", "_lip"), worldSpace=True, translation=(0, lip, 0.75)
        )
        cmds.setAttr(root + ".vertexLoop", lips_face["vertex_loop"], type="string")
        for key, value in settings.items():
            if isinstance(value, str):
                cmds.setAttr("{}.{}".format(root, key), value, type="string")
            else:
                cmds.setAttr("{}.{}".format(root, key), value)
        return root

    return draw


@pytest.fixture
def import_template(rig_plugins, setup_path, monkeypatch):
    """Function importing a bundled guide template in a new scene.

    Returns:
        callable: Called with the template file name, returns the guide
            root node.
    """
    from maya import cmds

    import mgear
    import mgear.pymaya as pm
    from mgear.shifter import io

    monkeypatch.setattr(mgear, "log", lambda *args, **kwargs: None)

    def load(template):
        cmds.file(new=True, force=True)
        io.import_sample_template(template)
        return pm.PyNode("guide")

    return load


# world positions of the root and the 3 locators of a chain guide
CHAIN_POSITIONS = ((1.0, 5.0, 0.0), (2.0, 5.0, 0.0), (3.0, 5.0, 0.0), (4.0, 5.0, 0.0))


class _ChainSections(object):
    """Answer of the chain guide initializer dialog."""

    def __init__(self, sections_number):
        self.sections_number = sections_number
        self.dir_axis = 0
        self.spacing = 1.0


@pytest.fixture
def chain_guide(rig_plugins, setup_path, monkeypatch):
    """Function drawing a chain guide in a new scene.

    The first call makes a new scene.

    The chain guide initializer dialog is answered with the number of
    locators. Guides after the first are drawn in the same guide.

    Returns:
        callable: Called with the component type, name, side, index,
            parent (guide node name, optional), positions (root and
            locator world positions) and guide settings. Returns the guide
            root name. Its ``positions`` attribute is the default
            positions.
    """
    from maya import cmds

    import mgear.pymaya as pm
    from mgear.shifter import guide
    from mgear.shifter.component import chain_guide_initializer

    cmds.file(new=True, force=True)

    def draw(
        comp="chain_spring_gravity_02",
        name="chain",
        side="L",
        index=0,
        parent=None,
        positions=CHAIN_POSITIONS,
        **settings
    ):
        monkeypatch.setattr(
            chain_guide_initializer,
            "exec_window",
            lambda: _ChainSections(len(positions) - 1),
        )
        # draw in the existing guide, else a new guide hierarchy is made
        if not parent and cmds.objExists("guide"):
            parent = "guide"
        before = set(cmds.ls("*_root", type="transform"))
        guide.Rig().drawNewComponent(
            pm.PyNode(parent) if parent else None, comp, showUI=False
        )
        root = (set(cmds.ls("*_root", type="transform")) - before).pop()
        guide.Rig().updateProperties(pm.PyNode(root), name, side, index)
        prefix = "{}_{}{}_".format(name, side, index)
        root = prefix + "root"
        _set_chain_positions(prefix, positions)
        for key, value in settings.items():
            if isinstance(value, str):
                cmds.setAttr("{}.{}".format(root, key), value, type="string")
            else:
                cmds.setAttr("{}.{}".format(root, key), value)
        return root

    draw.positions = CHAIN_POSITIONS
    return draw


def _set_chain_positions(prefix, positions):
    """Set the root and locator world positions of a chain guide."""
    from maya import cmds

    cmds.xform(prefix + "root", worldSpace=True, translation=positions[0])
    for i, position in enumerate(positions[1:]):
        loc = "{}{}_loc".format(prefix, i)
        cmds.xform(loc, worldSpace=True, translation=position)
