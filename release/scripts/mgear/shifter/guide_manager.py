import sys
import json

from mgear.core import pyqt


from maya import cmds

import mgear.pymaya as pm
from mgear.pymaya import datatypes
from mgear.core import curve
from mgear.core import transform

import mgear
from mgear import shifter
import mgear.shifter.io as sio
from mgear.shifter.utils import get_root_joint

##############################
# Helper Functions
##############################


def draw_comp(comp_type, parent=None, showUI=True):
    """Draw a new component of a given name

    Args:
        comp_type (str): Name of the component to draw
        *args: Description
    """
    guide = shifter.guide.Rig()
    if not parent and pm.selected():
        parent = pm.selected()[0]

    if parent:
        if not parent.hasAttr("isGearGuide") and not parent.hasAttr("ismodel"):
            pm.displayWarning(
                "{}: is not valid Shifter guide elemenet".format(parent)
            )
            return

    guide.drawNewComponent(parent, comp_type, showUI)


def duplicate(sym, *args):
    """Duplicate a component by drawing a new one and setting the same
    properties values

    Args:
        sym (bool): If True, will create a symmetrical component
        *args: None

    """
    oSel = pm.selected()
    if oSel:
        root = oSel[0]
        guide = shifter.guide.Rig()
        guide.duplicate(root, sym)
    else:
        mgear.log(
            "Select one component root to edit properties", mgear.sev_error
        )


def duplicate_multi(sym, *args):
    """Duplicate a multiple component by drawing a new one and setting the same
    properties values

    Args:
        sym (bool): If True, will create a symmetrical component
        *args: None

    """
    oSel = pm.selected()
    if oSel:
        for root in oSel:
            guide = shifter.guide.Rig()
            guide.duplicate(root, sym)
    else:
        mgear.log(
            "Select one or more component root to edit properties",
            mgear.sev_error,
        )


def build_from_selection(*args):
    """Build rig from current selection

    Args:
        *args: None
    """
    shifter.log_window()
    rg = shifter.Rig()
    rg.buildFromSelection()


def inspect_settings(tabIdx=0, *args):
    """Open the component or root setting UI.

    Args:
        tabIdx (int, optional): Tab index to be open when open settings
        *args: None

    Returns:
        None: None if nothing is selected
    """
    oSel = pm.selected()
    if oSel:
        root = oSel[0]
    else:
        pm.displayWarning("please select one object from the componenet guide")
        return

    comp_type = False
    guide_root = False
    while root:
        if pm.attributeQuery("comp_type", node=root, ex=True):
            comp_type = root.attr("comp_type").get()
            break
        elif pm.attributeQuery("ismodel", node=root, ex=True):
            guide_root = root
            break
        root = root.getParent()
        pm.select(root)

    if comp_type:
        guide = shifter.importComponentGuide(comp_type)
        wind = pyqt.showDialog(guide.componentSettings, dockable=True)
        wind.tabs.setCurrentIndex(tabIdx)
        return wind

    elif guide_root:
        module_name = "mgear.shifter.guide"
        level = -1 if sys.version_info < (3, 3) else 0
        guide = __import__(module_name, globals(), locals(), ["*"], level)
        wind = pyqt.showDialog(guide.guideSettings, dockable=True)
        wind.tabs.setCurrentIndex(tabIdx)
        return wind

    else:
        pm.displayError("The selected object is not part of component guide")


def extract_controls(*args):
    """Extract the selected controls from the rig to use in the new build.

    For each selected control, only the transform itself is duplicated
    (``parentOnly=True``), so the descendant hierarchy is never touched
    -- extraction time is independent of how many children, joints,
    constraints, or DG nodes hang under the control. NurbsCurve shapes
    are then rebuilt directly under the new buffer transform with the
    OpenMaya API (``MFnNurbsCurve.create``), which sidesteps the
    ``cmds.duplicate`` shape machinery entirely.

    Mesh, locator, and other non-curve shape types are filtered out
    at the source-collection step. Intermediate shapes are filtered
    too. Ghost controls (instanced/shared shapes) get an independent
    copy automatically -- no instance survives into the buffer. The
    buffer is removed from any objectSets the source belongs to.

    Args:
        *args: Ignored (Maya menu callback compatibility).
    """
    o_sel = pm.selected()

    try:
        c_grp = pm.PyNode("controllers_org")
    except TypeError:
        pm.displayWarning(
            "No controllers_org group in the scene or the group is not unique"
        )
        return

    c_grp_name = c_grp.name()

    for x in o_sel:
        if not x.hasAttr("isCtl"):
            pm.displayWarning("{}: Is not a valid mGear control".format(x.name()))
            continue

        ctl_path = x.longName()
        short_name = ctl_path.split("|")[-1]
        buffer_name = short_name + "_controlBuffer"

        curve_shapes = (
            cmds.listRelatives(
                ctl_path,
                shapes=True,
                fullPath=True,
                noIntermediate=True,
                type="nurbsCurve",
            )
            or []
        )

        # Skip before touching any existing buffer, so a control that
        # temporarily lost its curve shapes does not lose its previous
        # buffer with no replacement.
        if not curve_shapes:
            mgear.log(
                "'{}': No NurbsCurve shapes found, "
                "skipping extraction".format(short_name),
                mgear.sev_warning,
            )
            continue

        old_buffer = c_grp_name + "|" + buffer_name
        if cmds.objExists(old_buffer):
            cmds.delete(old_buffer)

        for shape in curve_shapes:
            if len(cmds.listRelatives(shape, allParents=True) or []) > 1:
                mgear.log(
                    "Instanced shape detected on '{}', "
                    "creating independent copy".format(short_name),
                    mgear.sev_warning,
                )
                break

        dup = cmds.duplicate(ctl_path, parentOnly=True, returnRootsOnly=True)[0]
        dup = cmds.parent(dup, c_grp_name)[0]
        dup = cmds.rename(dup, buffer_name)
        dup_path = cmds.ls(dup, long=True)[0]

        for i, src_shape in enumerate(curve_shapes):
            new_shape_path = curve.create_curve_shape_under(src_shape, dup_path)
            curve.copy_curve_display_attrs(src_shape, new_shape_path)
            new_name = (
                buffer_name + "Shape" if i == 0 else "{}Shape{}".format(buffer_name, i)
            )
            cmds.rename(new_shape_path, new_name)

        # objectSet membership is reachable only through instObjGroups[0]
        # connections; drop the buffer from each set the source belonged to.
        sets = (
            cmds.listConnections(ctl_path + ".instObjGroups[0]", type="objectSet") or []
        )
        for s in sets:
            try:
                cmds.sets(dup_path, remove=s)
            except RuntimeError:
                pass

        mgear.log("Extracted '{}' ({} shape(s))".format(short_name, len(curve_shapes)))


# Extract guide from rigs


def extract_guide_from_rig(*args):
    """
    Extract guide data from a selected or default rig root and import guide.

    Returns:
        pm.PyNode: Returns the rig root node if successful, otherwise None.
    """
    selection = pm.ls(selection=True)
    if not selection:
        selection = pm.ls("rig")
        if not selection or not selection[0].hasAttr("is_rig"):
            mgear.log(
                "Not rig root selected or found.\nSelect the rig root",
                mgear.sev_error,
            )
            return
    if selection[0].hasAttr("is_rig"):
        guide_dict = selection[0].guide_data.get()
        sio.import_guide_template(conf=json.loads(guide_dict))
        return selection[0]


def get_ordered_child(jnt):
    """
    Retrieve ordered child nodes under a joint.

    Args:
        jnt (pm.PyNode): The joint node to start search from.

    Returns:
        list: List of ordered child nodes if node is joint.
    """
    if jnt.type() == "joint":
        pm.select(jnt, hi=True, r=True)
        return pm.selected()
    else:
        pm.displayWarning("Object: {} is not of type joint".format(jnt.name()))


def match_guide_to_joint_pos_ori(jnt_list, ori=False):
    """
    Match guide positions and orientations to joint nodes.

    Args:
        jnt_list (list): List of joint nodes.
        ori (bool): Whether to match orientation. Default is True.
    """
    pm.displayInfo(
        "Only EPIC components can be match. Other component will be skipped"
    )
    if jnt_list:
        for j in jnt_list:
            if j.hasAttr("guide_relative"):
                for g_relative in pm.ls(j.guide_relative.get()):
                    if g_relative.hasAttr("isGearGuide"):
                        gmw = g_relative.getMatrix(worldSpace=True)
                        if ori:
                            tm = datatypes.TransformationMatrix(gmw)
                            sWM = j.getMatrix(worldSpace=True)
                            sWM = transform.setMatrixScale(
                                sWM, tm.getScale(space="world")
                            )
                        else:
                            jwp = j.getTranslation(space="world")
                            sWM = transform.setMatrixPosition(gmw, jwp)
                        g_relative.setMatrix(sWM, worldSpace=True)


def extract_match_guide_from_rig(*args):
    """
    Extract and match guide data based on joint positions and orientations.
    """
    rig_root = extract_guide_from_rig()
    if rig_root:
        root_jnt = get_root_joint(rig_root)
        match_guide_to_joint_pos_ori(get_ordered_child(root_jnt))


def snap_guide_to_root_joint(root_jnt=None):
    if not root_jnt:
        root_jnt = pm.selected()
    if root_jnt:
        root_jnt = root_jnt[0]
        match_guide_to_joint_pos_ori(get_ordered_child(root_jnt))
    else:
        pm.displayWarning("Nothing selected")
