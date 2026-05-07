import sys
import json

from mgear.core import pyqt


from maya import cmds
import maya.api.OpenMaya as om2

import mgear.pymaya as pm
from mgear.pymaya import datatypes
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


_CURVE_DISPLAY_ATTRS = (
    "overrideEnabled",
    "overrideDisplayType",
    "overrideRGBColors",
    "overrideColor",
    "overrideColorR",
    "overrideColorG",
    "overrideColorB",
    "overrideColorA",
    "lineWidth",
    "alwaysDrawOnTop",
)


def _curve_shape_copy(src_shape_path, dst_xform_path):
    """Build an independent NurbsCurve shape under ``dst_xform_path``
    that is a geometry-level copy of ``src_shape_path``, using the
    OpenMaya API directly.

    Bypasses ``cmds.duplicate`` entirely -- there is no temporary
    transform to delete and no descendant hierarchy to walk, so the
    cost is constant per shape regardless of where the source lives
    in the DAG. The result is independent of any instancing on the
    source.

    Args:
        src_shape_path (str): Full DAG path to a NurbsCurve shape.
        dst_xform_path (str): Full DAG path to the parent transform.

    Returns:
        str: Full DAG path of the newly created shape.
    """
    src_sel = om2.MSelectionList()
    src_sel.add(src_shape_path)
    src_curve = om2.MFnNurbsCurve(src_sel.getDagPath(0))

    dst_sel = om2.MSelectionList()
    dst_sel.add(dst_xform_path)
    dst_obj = dst_sel.getDependNode(0)

    new_curve = om2.MFnNurbsCurve()
    new_obj = new_curve.create(
        src_curve.cvPositions(om2.MSpace.kObject),
        src_curve.knots(),
        src_curve.degree,
        src_curve.form,
        False,  # create2D
        True,  # rational
        dst_obj,
    )
    return om2.MFnDagNode(new_obj).fullPathName()


def _copy_curve_display_attrs(src_shape, dst_shape):
    """Best-effort copy of curve display attributes (color, line
    width, override flags) from ``src_shape`` to ``dst_shape``.

    Missing or locked attributes are skipped silently so the buffer
    is created even if the source has unusual attribute state.
    """
    for attr in _CURVE_DISPLAY_ATTRS:
        src_attr = src_shape + "." + attr
        dst_attr = dst_shape + "." + attr
        if not cmds.objExists(src_attr) or not cmds.objExists(dst_attr):
            continue
        try:
            cmds.setAttr(dst_attr, cmds.getAttr(src_attr))
        except (RuntimeError, ValueError):
            pass


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

        # Delete any existing buffer for this control
        try:
            old = pm.PyNode(c_grp_name + "|" + buffer_name)
            pm.delete(old)
        except (TypeError, RuntimeError):
            pass

        # Source curve shapes (filters mesh, locator, intermediate)
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

        if not curve_shapes:
            mgear.log(
                "'{}': No NurbsCurve shapes found, "
                "skipping extraction".format(short_name),
                mgear.sev_warning,
            )
            continue

        # Warn (once) if any source shape is instanced. The OpenMaya
        # copy below produces an independent shape regardless.
        for shape in curve_shapes:
            if len(cmds.listRelatives(shape, allParents=True) or []) > 1:
                mgear.log(
                    "Instanced shape detected on '{}', "
                    "creating independent copy".format(short_name),
                    mgear.sev_warning,
                )
                break

        # Fast path: parentOnly skips all children AND all shapes;
        # only the transform is created. Cost is constant per control,
        # independent of descendant hierarchy size.
        dup = cmds.duplicate(ctl_path, parentOnly=True, returnRootsOnly=True)[0]
        dup = cmds.parent(dup, c_grp_name)[0]
        dup = cmds.rename(dup, buffer_name)
        dup_path = cmds.ls(dup, long=True)[0]

        # Build curve shapes directly via OpenMaya
        for i, src_shape in enumerate(curve_shapes):
            new_shape_path = _curve_shape_copy(src_shape, dup_path)
            _copy_curve_display_attrs(src_shape, new_shape_path)
            new_name = (
                buffer_name + "Shape" if i == 0 else "{}Shape{}".format(buffer_name, i)
            )
            cmds.rename(new_shape_path, new_name)

        # Make sure the buffer is not a member of any objectSet
        # the source control belongs to (render layers, selection
        # sets, etc. linked through instObjGroups[0]).
        try:
            sets = (
                cmds.listConnections(
                    ctl_path + ".instObjGroups[0]",
                    type="objectSet",
                )
                or []
            )
        except (TypeError, ValueError):
            sets = []
        for s in sets:
            try:
                cmds.sets(dup_path, remove=s)
            except RuntimeError:
                pass

        mgear.log(
            "Extracted '{}' ({} shape(s))".format(short_name, len(curve_shapes))
        )


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
