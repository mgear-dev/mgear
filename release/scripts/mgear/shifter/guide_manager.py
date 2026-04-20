import sys
import json

from mgear.core import pyqt


from maya import cmds

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
                "{}: 不是有效的Shifter引导元素".format(parent)
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
            "选择一个组件根节点来编辑属性", mgear.sev_error
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
            "选择一个或多个组件根节点来编辑属性",
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
        pm.displayWarning("请从组件引导中选择一个对象")
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
        pm.displayError("所选对象不是组件引导的一部分")


def extract_controls(*args):
    """Extract the selected controls from the rig to use it
    in the new build.

    The control NurbsCurve shapes are stored under the
    controllers_org group.  The controls are renamed with
    "_controlBuffer" suffix.

    Uses ``parentOnly=True`` duplication to avoid child
    leaking, then manually copies only NurbsCurve shapes.
    Handles instanced/shared shapes (ghost controls) by
    creating independent copies.

    Args:
        *args: Ignored (Maya menu callback compatibility).
    """
    oSel = pm.selected()

    try:
        cGrp = pm.PyNode("controllers_org")
    except TypeError:
        cGrp = False
        pm.displayWarning(
            "场景中没有controllers_org组"
            "或该组不唯一"
        )
        return

    for x in oSel:
        if not x.hasAttr("isCtl"):
            pm.displayWarning(
                "{}: 不是有效的mGear控制器".format(
                    x.name()
                )
            )
            continue

        buffer_name = x.name().split("|")[-1] + "_controlBuffer"

        # Delete existing buffer if present
        try:
            old = pm.PyNode(
                cGrp.name() + "|" + buffer_name
            )
            pm.delete(old)
        except (TypeError, RuntimeError):
            pass

        # Duplicate the control once to get all shapes
        # (handles instanced shapes correctly)
        temp = pm.duplicate(x)[0]

        # Create clean buffer transform
        new = pm.createNode(
            "transform", name=buffer_name, parent=cGrp
        )

        # Check for instanced shapes on the original
        for shape in x.getShapes():
            all_parents = cmds.listRelatives(
                shape.name(), allParents=True
            ) or []
            if len(all_parents) > 1:
                mgear.log(
                    "检测到 '{}' 上的实例化形状，"
                    "创建独立副本".format(
                        x.name()
                    ),
                    mgear.sev_warning,
                )
                break

        # Move only NurbsCurve shapes to the buffer,
        # skip intermediate objects and non-curve types
        shape_count = 0
        for shape in temp.getShapes():
            if shape.type() != "nurbsCurve":
                continue
            if shape.intermediateObject.get():
                continue
            pm.parent(
                shape, new, shape=True, relative=True
            )
            pm.rename(shape, buffer_name + "Shape")
            shape_count += 1

        # Delete the temp transform (children and
        # leftover non-curve shapes)
        pm.delete(temp)

        # Validate: skip empty buffers
        if shape_count == 0:
            mgear.log(
                "'{}': 未找到NurbsCurve形状，"
                "跳过提取".format(x.name()),
                mgear.sev_warning,
            )
            pm.delete(new)
            continue

        mgear.log(
            "已提取 '{}' ({} 个形状)".format(
                x.name(), shape_count
            )
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
                "未选择或找到绑定根节点。\n请选择绑定根节点",
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
        pm.displayWarning("对象: {} 不是关节类型".format(jnt.name()))


def match_guide_to_joint_pos_ori(jnt_list, ori=False):
    """
    Match guide positions and orientations to joint nodes.

    Args:
        jnt_list (list): List of joint nodes.
        ori (bool): Whether to match orientation. Default is True.
    """
    pm.displayInfo(
        "只能匹配EPIC组件。其他组件将被跳过"
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
        pm.displayWarning("未选择任何对象")
