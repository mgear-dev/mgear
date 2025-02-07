# Stdlib imports
import re
import traceback
from functools import partial

from .six import PY2

# Maya imports
from maya import cmds
import pymel.core as pm
from pymel import versions

# mGear imports
import mgear
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets
from mgear.core import pyqt
from mgear.core import dag
from mgear.core import transform
from mgear.core import utils
from mgear.core import attribute
from mgear.core import vector
from mgear.core.attribute import reset_selected_channels_value
from mgear.core.pickWalk import get_all_tag_children

# =============================================================================
# constants
# =============================================================================
EXPR_LEFT_SIDE = re.compile("L(\d+)")
EXPR_RIGHT_SIDE = re.compile("R(\d+)")

CTRL_GRP_SUFFIX = "_controllers_grp"
PLOT_GRP_SUFFIX = "_PLOT_grp"

# spine FK/IK matching, naming ------------------------------------------------
TAN_TOKEN = "_tan_ctl"
TAN0_TOKEN = "_tan0_ctl"
TAN1_TOKEN = "_tan1_ctl"
START_IK_TOKEN = "_ik0_ctl"
END_IK_TOKEN = "_ik1_ctl"
POS_IK_TOKEN = "_spinePosition_ctl"

# No mirror attributes ------------------------------------------------
NO_MIRROR_ATTRIBUTES = ["isRig", "uiHost", "_ctl"]

##################################################
# util


def isSideElement(name):
    """Returns is name(str) side element?

    Arguments:
        name (str): Description

    Returns:
        bool

    """
    # try first wiht side labels if is a node. This will fail with attrs
    try:
        if isinstance(name, str):
            node = pm.PyNode(name)
        if node.hasAttr("side_label"):
            side = node.side_label.get()
            if side in "LR":
                return True
    except pm.MayaNodeError:
        pass

    # old logic for back compatibility
    if "_L_" in name or "_R_" in name:
        return True
    nameParts = stripNamespace(name).split("|")[-1]

    for part in nameParts.split("_"):
        if EXPR_LEFT_SIDE.match(part) or EXPR_RIGHT_SIDE.match(part):
            return True
    else:
        return False


def isSideNode(node):
    """Returns is name(str) side element?

    Arguments:
        name (node): PyNode

    Returns:
        bool
    """

    if node.hasAttr("side_label"):
        if node.side_label.get() in "LR":
            return True
        else:
            return False

    else:
        return isSideElement(node.name())


def swapSideLabel(name):
    """Returns fliped name

    Returns fliped name that replaced side label left to right or
    right to left

    Arguments:
        name(str): Name to swap the side

    Returns:
        str
    """

    for part in name.split("_"):
        if EXPR_LEFT_SIDE.match(part):
            return EXPR_LEFT_SIDE.sub(r"R\1", name)
        if EXPR_RIGHT_SIDE.match(part):
            return EXPR_RIGHT_SIDE.sub(r"L\1", name)

    else:
        if "_L_" in name:
            return name.replace("_L_", "_R_")
        elif "_R_" in name:
            return name.replace("_R_", "_L_")
        else:
            return name


def swapSideLabelNode(node):
    """Returns fliped name of a node

    Returns fliped name that replaced side label left to right or
    right to left

    Arguments:
        name(node): pyNode

    Returns:
        str
    """
    if isinstance(node, str):
        node = pm.PyNode(node)

    # first check default swapSideLabel. For defaul Shifter naming system
    name = node.stripNamespace()
    sw_name = swapSideLabel(name)
    if name != sw_name:
        return sw_name

    # try to find the mirror using custom side labels
    if node.hasAttr("side_label"):
        side = node.side_label.get()
        if side in "LR":
            # custom side label
            c_side = node.attr("{}_custom_side_label".format(side)).get()
            # mirror side label
            if side == "L":
                cm_side = node.attr("R_custom_side_label").get()
            elif side == "R":
                cm_side = node.attr("L_custom_side_label").get()
            return node.stripNamespace().replace(c_side, cm_side)
        else:
            return node.stripNamespace()

    else:
        return swapSideLabel(node.stripNamespace())


def getClosestNode(node, nodesToQuery):
    """return the closest node, based on distance, from the list provided

    Args:
        node (string): name of node
        nodesToQuery (list): of nodes to query

    Returns:
        string: name of the closest node
    """
    distance = None
    closestNode = None
    node = pm.PyNode(node)
    for index, nodeTQ in enumerate(nodesToQuery):
        nodeTQ = pm.PyNode(nodeTQ)
        tmpDist = vector.getDistance2(node, nodeTQ)
        if index == 0:
            distance = tmpDist
            closestNode = nodeTQ
        if distance > tmpDist:
            distance = tmpDist
            closestNode = nodeTQ
    return closestNode.name()


def recordNodesMatrices(nodes, desiredTime):
    """get the matrices of the nodes provided and return a dict of
    node:matrix

    Args:
        nodes (list): of nodes

    Returns:
        dict: node:node matrix
    """
    nodeToMat_dict = {}
    for fk in nodes:
        fk = pm.PyNode(fk)
        nodeToMat_dict[fk.name()] = fk.getAttr("worldMatrix", time=desiredTime)

    return nodeToMat_dict


def getRootNode():
    """Returns the root node from a selected node

    Returns:
        PyNode: The root top node
    """

    root = None

    current = pm.ls(sl=True)
    if not current:
        raise RuntimeError("You need to select at least one rig node")

    if current[0].hasAttr("is_rig"):
        root = current[0]
    else:
        holder = current[0]
        while holder.getParent() and not root:
            if holder.getParent().hasAttr("is_rig"):
                root = holder.getParent()
            else:
                holder = holder.getParent()

    if not root:
        raise RuntimeError("Couldn't find root node from your selection")

    return root


def getControlers(model, gSuffix=CTRL_GRP_SUFFIX):
    """Get thr controlers from the set

    Args:
        model (PyNode): Rig root
        gSuffix (str, optional): set suffix

    Returns:
        list: The members of the group
    """
    try:
        ctl_set = pm.PyNode(model.name() + gSuffix)
        members = ctl_set.members()

        return members
    except TypeError:
        return None


def get_control_list(control, blend_attr, extension="_ctl"):

    controls = None

    controls_attribute = blend_attr.replace("_blend", extension)
    try:
        controls = cmds.getAttr("{}.{}".format(control, controls_attribute))
    except ValueError:
        if control == "world_ctl":
            _msg = "New type attributes using world as host are not supported"
            raise RuntimeError(_msg)
        attr = "{}_{}_ctl".format(
            blend_attr.split("_")[0], control.split(":")[-1].split("_")[1]
        )
        controls = cmds.getAttr("{}.{}".format(control, attr))

    return controls


def get_ik_fk_controls(control, blend_attr, comp_ctl_list=None):
    """Returns the ik and fk controls related to the given control blend attr

    OBSOLETE:This function is obsolete and just keep for backward compatibility

    Args:
        control (str): uihost control to interact with
        blend_attr (str): attribute containing control list

    Returns:
        dict: fk and ik controls list on a dict
    """

    ik_fk_controls = {"fk_controls": [], "ik_controls": []}

    if comp_ctl_list:
        ctl_list = cmds.getAttr("{}.{}".format(control, comp_ctl_list))
    else:
        ctl_list = get_control_list(control, blend_attr)

    # filters the controls
    for ctl in ctl_list.split(","):
        if len(ctl) == 0:
            continue
        # filters ik controls
        if "_ik" in ctl.lower() or "_upv" in ctl:
            ik_fk_controls["ik_controls"].append(ctl)
        # filters fk controls
        elif "_fk" in ctl.lower():
            ik_fk_controls["fk_controls"].append(ctl)

    return ik_fk_controls


def get_ik_fk_controls_by_role(uiHost, attr_ctl_cnx):
    """Returns the ik fk controls sorted by role.
     Using the new role attr tag

     this makes obsolete get_ik_fk_controls() function.

    Args:
        uiHost (str): uihost control to interact with
        attr_ctl_cnx (str): attribute containing control list

    Returns:
        dict: with the control sorted by role
    """
    ik_controls = {"ik_control": None, "pole_vector": None, "ik_rot": None}
    fk_controls = []
    uiHost = pm.PyNode(uiHost)
    if uiHost.hasAttr(attr_ctl_cnx):
        cnxs = uiHost.attr(attr_ctl_cnx).listConnections()
        if cnxs:
            for c in cnxs:
                role = c.ctl_role.get()
                if "fk" in role:
                    fk_controls.append(c.stripNamespace())
                elif role in ["upv", "leg_pv", "arm_pv"]:
                    ik_controls["pole_vector"] = c.stripNamespace()
                elif role in ["ik", "wrist_ik", "ankle_ik"]:
                    ik_controls["ik_control"] = c.stripNamespace()
                elif role == "ikRot":
                    ik_controls["ik_rot"] = c.stripNamespace()
                elif role == "roll":
                    ik_controls["roll"] = c.stripNamespace()

    # fk_controls = sorted(fk_controls)
    return ik_controls, fk_controls


def get_host_from_node(control):
    """Returns the host control name from the given control
    Args:
        control (str): Rig control

    Returns:
        str: Host UI control name
    """

    # get host control
    namespace = getNamespace(control).split("|")[-1]
    host = cmds.getAttr("{}.uiHost".format(control))
    return "{}:{}".format(namespace, host)


def getNamespace(modelName):
    """Get the name space from rig root

    Args:
        modelName (str): Rig top node name

    Returns:
        str: Namespace
    """
    if not modelName:
        return ""

    if len(modelName.split(":")) >= 2:
        nameSpace = ":".join(modelName.split(":")[:-1])
    else:
        nameSpace = ""

    return nameSpace


def stripNamespace(nodeName):
    """Strip all the namespaces from a given name

    Args:
        nodeName (str): Node name to strip the namespaces

    Returns:
        str: Node name without namespace
    """
    return nodeName.split(":")[-1]


def getNode(nodeName):
    """Get a PyNode from the string name


    Args:
        nodeName (str): Node name

    Returns:
        PyNode or None: The node. or None if the object can't be found
    """
    try:
        return pm.PyNode(nodeName)

    except pm.MayaNodeError:
        return None


def listAttrForMirror(node):
    """List attributes to invert the value for mirror posing

    Args:
        node (PyNode): The Node with the attributes to invert

    Returns:
        list: Attributes to invert
    """
    # TODO: should "ro" be here?
    res = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "ro"]
    res.extend(pm.listAttr(node, userDefined=True, shortNames=True))
    res = list([x for x in res if not x.startswith("inv")])
    res = list(
        [x for x in res if node.attr(x).type() not in ["message", "string"]]
    )
    return res


def getInvertCheckButtonAttrName(str):
    """Get the invert check butto attribute name

    Args:
        str (str): The attribute name

    Returns:
        str: The checked attribute name
    """
    # type: (str) -> str
    return "inv{0}".format(str.lower().capitalize())


def selAll(model):
    """Select all controlers

    Args:
        model (PyNode): Rig top node
    """
    controlers = getControlers(model)
    pm.select(controlers)


def selGroup(model, groupSuffix):
    """Select the members of a given set

    Args:
        model (PyNode): Rig top node
        groupSuffix (str): Set suffix name
    """
    controlers = getControlers(model, groupSuffix)
    pm.select(controlers)


def select_all_child_controls(control, *args):  # @unusedVariable
    """Selects all child controls from the given control

    This function uses Maya's controller nodes and commands to find relevant
    dependencies between controls

    Args:
        control (str): parent animation control (transform node)
        *args: State of the menu item (if existing) send by mgear's dagmenu
    """

    # gets controller node from the given control. Returns if none is found
    # tag = cmds.ls(cmds.listConnections(control), type="controller")
    # if not tag:
    #     return

    # query child controls
    children = get_all_tag_children(control)
    if not children:
        return

    # adds to current selection the children elements
    cmds.select(children, add=True)


def quickSel(model, channel, mouse_button):
    """Select the object stored on the quick selection attributes

    Args:
        model (PyNode): The rig top node
        channel (str): The quick selection channel name
        mouse_button (QtSignal): Clicked mouse button

    Returns:
        None
    """
    qs_attr = model.attr("quicksel%s" % channel)

    if mouse_button == QtCore.Qt.LeftButton:  # Call Selection
        names = qs_attr.get().split(",")
        if not names:
            return
        pm.select(clear=True)
        for name in names:
            ctl = dag.findChild(model, name)
            if ctl:
                ctl.select(add=True)
    elif mouse_button == QtCore.Qt.MidButton:  # Save Selection
        names = [
            sel.name().split("|")[-1]
            for sel in pm.ls(selection=True)
            if sel.name().endswith("_ctl")
        ]

        qs_attr.set(",".join(names))

    elif mouse_button == QtCore.Qt.RightButton:  # Key Selection
        names = qs_attr.get().split(",")
        if not names:
            return
        else:
            keyObj(model, names)


##################################################
# KEY
##################################################
# ================================================
def keySel():
    """Key selected controls"""

    pm.setKeyframe()


# ================================================


def keyObj(model, object_names):
    """Set the keyframe in the controls pass by a list in obj_names variable

    Args:
        model (Str): Name of the namespace that will define de the model
        object_names (Str): names of the controls, without the name space

    Returns:
        None
    """
    with pm.UndoChunk():
        nodes = []
        nameSpace = getNamespace(model)
        for name in object_names:
            if nameSpace:
                node = getNode(nameSpace + ":" + name)
            else:
                node = getNode(name)

            if not node:
                continue

            if not node and nameSpace:
                mgear.log(
                    "Can't find object : %s:%s" % (nameSpace, name),
                    mgear.sev_error,
                )
            elif not node:
                mgear.log("Can't find object : %s" % (name), mgear.sev_error)
            nodes.append(node)

        if not nodes:
            return

        pm.setKeyframe(*nodes)


def keyAll(model):
    """Keyframe all the controls inside the controls group

    Note: We use the workd "group" to refer to a set in Maya

    Args:
        model (PyNode): Rig top node
    """
    controlers = getControlers(model)
    pm.setKeyframe(controlers)


def keyGroup(model, groupSuffix):
    """Keyframe all the members of a given group

    Args:
        model (PyNode): Rig top node
        groupSuffix (str): The group preffix
    """
    controlers = getControlers(model, groupSuffix)
    pm.setKeyframe(controlers)


# ================================================


def toggleAttr(model, object_name, attr_name):
    """Toggle a boolean attribute

    Args:
        model (PyNode): Rig top node
        object_name (str): The name of the control containing the attribute to
            toggle
        attr_name (str): The attribute to toggle
    """
    nameSpace = getNamespace(model)
    if nameSpace:
        node = dag.findChild(nameSpace + ":" + object_name)
    else:
        node = dag.findChild(model, object_name)

    oAttr = node.attr(attr_name)
    if oAttr.type() in ["float", "bool"]:
        oVal = oAttr.get()
        if oVal == 1:
            oAttr.set(0)
        else:
            oAttr.set(1)


# ================================================


def getComboIndex_with_namespace(namespace, object_name, combo_attr):
    """Get the index from a  combo attribute

    Args:
        namespace (str): namespace
        object_name (str): Control name
        combo_attr (str): Combo attribute name

    Returns:
        int: Current index in the combo attribute
    """
    if namespace:
        node = getNode(namespace + ":" + stripNamespace(object_name))
    else:
        node = getNode(object_name)

    oVal = node.attr(combo_attr).get()
    return oVal


def getComboIndex(model, object_name, combo_attr):
    """Get the index from a  combo attribute

    Args:
        model (PyNode): Rig top node
        object_name (str): Control name
        combo_attr (str): Combo attribute name

    Returns:
        int: Current index in the combo attribute
    """
    nameSpace = getNamespace(model)
    return getComboIndex_with_namespace(nameSpace, object_name, combo_attr)


def changeSpace_with_namespace(
    namespace, uiHost, combo_attr, cnsIndex, ctl_names
):
    """Change the space of a control

    i.e: A control with ik reference array

    Args:
        namespace (str): namespace
        uiHost (str): uiHost Name with the switch attr
        combo_attr (str): Combo attribute name
        cnsIndex (int): Combo index to change
        ctl_names ([str]): names of the target controls
    """
    if not isinstance(ctl_names, list):
        ctl_names = [ctl_names]

    if namespace:
        node = getNode(namespace + ":" + stripNamespace(uiHost))
    else:
        node = getNode(uiHost)

    sWM = []
    controls = []
    for e, c_name in enumerate(ctl_names):
        if namespace:
            ctl = getNode(namespace + ":" + stripNamespace(c_name))
        else:
            ctl = getNode(c_name)

        sWM.append(ctl.getMatrix(worldSpace=True))
        controls.append(ctl)

    oAttr = node.attr(combo_attr)
    oAttr.set(cnsIndex)

    for e, ctl in enumerate(controls):
        ctl.setMatrix(sWM[e], worldSpace=True)


def changeSpace(model, uiHost, combo_attr, cnsIndex, ctl_names):
    """Change the space of a control

    i.e: A control with ik reference array

    Args:
        model (PyNode): Rig top node
        uiHost (str): uiHost Name with the switch attr
        combo_attr (str): Combo attribute name
        cnsIndex (int): Combo index to change
        ctl_names ([str]]): Name of the target controls
    """
    nameSpace = getNamespace(model)
    return changeSpace_with_namespace(
        nameSpace, uiHost, combo_attr, cnsIndex, ctl_names
    )


def change_rotate_order(control, target_order):
    """Change current control rotate order on all frames

    Args:
        control (str): control to interact on
        target_order (str): target rotate order
    """

    if len(target_order) != 3:
        raise AttributeError(
            "Your target rotate order is not valid. "
            "Please use any of the following: "
            "xyz, yzx, zxy, xzy, yxz, zyx"
        )

    if not cmds.getAttr("{}.rotateOrder".format(control), settable=True):
        raise RuntimeError("RotateOrder is locked on the given control")

    # Maya's rotate order's index
    rotate_orders = {
        "xyz": 0,
        "yzx": 1,
        "zxy": 2,
        "xzy": 3,
        "yxz": 4,
        "zyx": 5,
    }

    # gets current control rotate order
    current_order = cmds.getAttr("{}.rotateOrder".format(control))

    # do nothing if target rotate order is the same as current one
    if current_order == rotate_orders[target_order]:
        return

    # gets anim curves on rotation values
    anim_curves = []
    for axe in ["x", "y", "z"]:
        anim_curves.extend(
            cmds.listConnections(
                "{}.r{}".format(control, axe), type="animCurve"
            )
            or []
        )

    # gets keyframe on rotateOrder attribute if any
    rotate_order_anim = (
        cmds.listConnections(
            "{}.rotateOrder".format(control), type="animCurve"
        )
        or []
    )

    # get unique timeline values for all rotate keyframe
    frames = []
    for node in anim_curves:
        [
            frames.append(x)
            for x in cmds.keyframe(node, query=True, controlPoints=True)
            if x not in frames
        ]

    # pauses viewport update
    current_frame = cmds.currentTime(query=True)
    if not cmds.ogs(query=True, pause=True):
        cmds.ogs(pause=True)

    # stores matrix position of your control for each frame
    positions = {}
    holder = cmds.createNode(
        "transform",
        name="{}_rotate_order_switch".format(control.split("|")[-1]),
    )
    cmds.setAttr("{}.rotateOrder".format(holder, rotate_orders[target_order]))
    for frame in frames:
        cmds.currentTime(frame)
        position = cmds.xform(
            control, query=True, worldSpace=True, matrix=True
        )
        cmds.xform(holder, worldSpace=True, matrix=position)
        positions[frame] = cmds.xform(
            holder, query=True, worldSpace=True, matrix=True
        )

    # change rotate order
    if rotate_order_anim:
        cmds.keyframe(
            rotate_order_anim,
            edit=True,
            valueChange=rotate_orders[target_order],
        )
    else:
        cmds.setAttr(
            "{}.rotateOrder".format(control), rotate_orders[target_order]
        )

    for frame in frames:
        cmds.currentTime(frame)
        cmds.xform(control, worldSpace=True, matrix=positions[frame])

    # filters curves
    cmds.filterCurve(anim_curves)

    # deletes holder and set back the good timeline value
    cmds.delete(holder)
    cmds.currentTime(current_frame)

    # un-pauses viewport
    if cmds.ogs(query=True, pause=True):
        cmds.ogs(pause=True)

    cmds.select(control)


##################################################
# Combo Box
##################################################
# ================================================


def getComboKeys_with_namespace(namespace, object_name, combo_attr):
    """Get the keys from a combo attribute

    Args:
        namespace (str): namespace
        object_name (str): Control name
        combo_attr (str): Combo attribute name

    Returns:
        list: Keys names from the combo attribute.
    """
    if namespace:
        node = getNode(namespace + ":" + stripNamespace(object_name))
    else:
        node = getNode(object_name)

    oAttr = node.attr(combo_attr)
    keys = list(oAttr.getEnums().keys())
    keys.append("++ Space Transfer ++")
    return keys


def getComboKeys(model, object_name, combo_attr):
    """Get the keys from a combo attribute

    Args:
        model (PyNode): Rig top node
        object_name (str): Control name
        combo_attr (str): Combo attribute name

    Returns:
        list: Keys names from the combo attribute.
    """
    nameSpace = getNamespace(model)

    return getComboKeys_with_namespace(nameSpace, object_name, combo_attr)


##################################################
# IK FK switch match
##################################################
# ================================================


def ikFkMatch_with_namespace(
    namespace,
    ikfk_attr,
    ui_host,
    fks,
    ik,
    upv,
    ik_rot=None,
    key=None,
    ik_controls=None,
    ik_val=1.0,
    fk_val=0.0,
):
    """Switch IK/FK with matching functionality

    This function is meant to work with 2 joint limbs.
    i.e: human legs or arms

    Args:
        namespace (str): Rig name space
        ikfk_attr (str): Blend ik fk attribute name
        ui_host (str): Ui host name
        fks ([str]): List of fk controls names
        ik (str): Ik control name
        upv (str): Up vector control name
        ik_rot (None, optional): Ik Rotation control if exist
        key (None, bool): optional. Whether we do an snap with animation
        ik_controls (None, optional): Ik controls
        ik_val (float, optional): Value that will define IK active
        fk_val (float, optional): Value that will define FK active

    Deleted Parameters:
        ikRot (None, str): optional. Name of the Ik Rotation control
    """
    # -----------------------------------------------
    # NOTE: the following section is a workaround to match and reset the gimbal
    # controls for legs and arms
    # this workaround doesn't support custom naming.
    gimbal_exist = False
    try:
        if "arm" in ikfk_attr or "leg" in ikfk_attr:

            fks_gimbal = [pm.PyNode(x.replace("fk", "gimbal")) for x in fks]
            ik_gimbal = pm.PyNode(ik.replace("ik", "gimbalIK"))

            # store world transforms
            fks_wtrans = [x.getMatrix(worldSpace=True) for x in fks_gimbal]
            ik_wtrans = ik_gimbal.getMatrix(worldSpace=True)

            # reset local transform
            for x in fks_gimbal:
                transform.resetTransform(x)
            transform.resetTransform(ik_gimbal)

            # apply transform to main control
            for i, x in enumerate(fks):
                pm.PyNode(x).setMatrix(fks_wtrans[i], worldSpace=True)
            pm.PyNode(ik).setMatrix(ik_wtrans, worldSpace=True)

            # keyframes
            if key:
                for x in fks_gimbal + [ik_gimbal]:
                    pm.setKeyframe(
                        x, time=(cmds.currentTime(query=True) - 1.0)
                    )
            gimbal_exist = True
    except:
        pass

    # end of workaround gimbal match
    # -----------------------------------------------

    # returns a pymel node on the given name
    def _get_node(name):
        # type: (str) -> pm.nodetypes.Transform
        name = stripNamespace(name)
        if namespace:
            node = getNode(":".join([namespace, name]))
        else:
            node = getNode(name)

        if not node:
            mgear.log("Can't find object : {0}".format(name), mgear.sev_error)

        return node

    # returns matching node
    def _get_mth(name):
        # type: (str) -> pm.nodetypes.Transform
        node = _get_node(name)
        if node.hasAttr("match_ref"):
            match_node = node.match_ref.listConnections()
            if match_node:
                return match_node[0]
        else:
            tmp = name.split("_")
            tmp[-1] = "mth"
            return _get_node("_".join(tmp))

    # get things ready
    fk_ctrls = [_get_node(x) for x in fks]
    fk_targets = [_get_mth(x) for x in fks]
    ik_ctrl = _get_node(ik)
    ik_target = _get_mth(ik)
    upv_ctrl = _get_node(upv)

    if ik_rot:
        ik_rot_node = _get_node(ik_rot)
        ik_rot_target = _get_mth(ik_rot)

    ui_node = _get_node(ui_host)
    o_attr = ui_node.attr(ikfk_attr)
    val = o_attr.get()

    # check for  FOOT cnx
    # get the information to handle the foot if the conexion exist
    foot_cnx = False
    if fk_ctrls[0].hasAttr("compRoot"):
        comp_root = fk_ctrls[0].compRoot.listConnections()[0]
        foot_IK_ctls = []
        foot_FK_matrix = []
        if comp_root.hasAttr("footCnx"):
            foot_cnx = True
            foot_root = comp_root.footCnx.listConnections()[0]
            foot_bk = [x for x in reversed(foot_root.bk_ctl.listConnections())]
            foot_IK_ctls.extend(foot_bk)
            foot_fk = foot_root.fk_ctl.listConnections()
            for c in foot_fk:
                foot_FK_matrix.append(c.getMatrix(worldSpace=True))
            heel_ctl = foot_root.heel_ctl.listConnections()[0]
            foot_IK_ctls.append(heel_ctl)
            tip_ctl = foot_root.tip_ctl.listConnections()[0]
            foot_IK_ctls.append(tip_ctl)
            if foot_root.hasAttr("roll_ctl"):
                roll_ctl = foot_root.roll_ctl.listConnections()[0]
                foot_IK_ctls.append(roll_ctl)
            else:
                roll_ctl = None
            if foot_root.hasAttr("roll_cnx"):
                roll_attr = foot_root.roll_cnx.listConnections()[0]
                bank_attr = foot_root.bank_cnx.listConnections()[0]
            else:
                roll_attr = None
                bank_attr = None

    # sets keyframes before snapping
    if key:
        _all_controls = []
        _all_controls.extend(fk_ctrls)
        _all_controls.extend([ik_ctrl, upv_ctrl, o_attr])
        if ik_rot:
            _all_controls.extend([ik_rot_node])
        if foot_cnx:
            _all_controls.extend(foot_IK_ctls)
            _all_controls.extend(foot_fk)
        [
            cmds.setKeyframe(
                "{}".format(elem), time=(cmds.currentTime(query=True) - 1.0)
            )
            for elem in _all_controls
        ]

    # if is IK then snap FK
    if val == ik_val:

        for target, ctl in zip(fk_targets, fk_ctrls):
            transform.matchWorldTransform(target, ctl)
        pm.setAttr(o_attr, fk_val)
        # we match the foot FK after switch blend attr
        if foot_cnx:
            for i, c in enumerate(foot_fk):
                c.setMatrix(foot_FK_matrix[i], worldSpace=True)

    # if is FK then sanp IK
    elif val == fk_val:
        transform.matchWorldTransform(ik_target, ik_ctrl)
        if ik_rot:
            transform.matchWorldTransform(ik_rot_target, ik_rot_node)
        # NOTE: Simple match replacing the previous logic.
        # Added TODO to researh in the future
        upv_ctrl_target = _get_mth(upv)
        transform.matchWorldTransform(upv_ctrl_target, upv_ctrl)

        # TODO: The following logic is failing with some components. Apparently
        # the control orientation for normal and binormal axis is affecting
        # transform.matchWorldTransform(fk_targets[1], upv_ctrl)
        # # calculates new pole vector position
        # start_end = fk_targets[-1].getTranslation(space="world") - fk_targets[
        #     0
        # ].getTranslation(space="world")
        # start_mid = fk_targets[1].getTranslation(space="world") - fk_targets[
        #     0
        # ].getTranslation(space="world")

        # dot_p = start_mid * start_end
        # proj = float(dot_p) / float(start_end.length())
        # proj_vector = start_end.normal() * proj
        # arrow_vector = start_mid - proj_vector
        # arrow_vector *= start_end.normal().length()

        # thre = 1e-4
        # # handle the case where three points lie on a line.
        # if (
        #     abs(arrow_vector.x) < thre
        #     and abs(arrow_vector.y) < thre
        #     and abs(arrow_vector.z) < thre
        # ):
        #     # can make roll and move up ctrl
        #     upv_ctrl_target = _get_mth(upv)
        #     transform.matchWorldTransform(upv_ctrl_target, upv_ctrl)
        # else:
        #     # ensure that the pole vector distance is a minimun of 1 unit
        #     # while arrow_vector.length() < 1.0:
        #     while arrow_vector.length() < start_mid.length():
        #         arrow_vector *= 2.0

        #     final_vector = arrow_vector + fk_targets[1].getTranslation(
        #         space="world"
        #     )
        #     upv_ctrl.setTranslation(final_vector, space="world")

        # sets blend attribute new value
        pm.setAttr(o_attr, ik_val)

        # handle the upvector roll
        roll_att_name = ikfk_attr.replace("blend", "roll")
        try:
            roll_att = ui_node.attr(roll_att_name)
        except pm.MayaAttributeError:
            # if is not in the uiHost lets check the IK ctl
            roll_att = ik_ctrl.attr(roll_att_name)
        roll_att.set(0.0)

        # reset roll ctl if exist
        if ik_controls and "roll" in ik_controls.keys():
            roll_ctl = _get_node(ik_controls["roll"])
            roll_ctl.rotateX.set(0)

        # reset IK foot ctls
        if foot_cnx:
            attribute.reset_SRT(foot_IK_ctls)
            if roll_attr:
                roll_attr.set(0)
                bank_attr.set(0)

        # we match the foot FK after switch blend attr
        if foot_cnx:
            for i, c in enumerate(foot_fk):
                c.setMatrix(foot_FK_matrix[i], worldSpace=True)

    # sets keyframes
    if key:
        [
            cmds.setKeyframe(
                "{}".format(elem), time=(cmds.currentTime(query=True))
            )
            for elem in _all_controls
        ]
        if gimbal_exist:
            for x in fks_gimbal + [ik_gimbal]:
                pm.setKeyframe(x, time=(cmds.currentTime(query=True)))
    cmds.dgdirty(a=True)


def ikFkMatch(model, ikfk_attr, ui_host, fks, ik, upv, ik_rot=None, key=None):
    """Switch IK/FK with matching functionality

    This function is meant to work with 2 joint limbs.
    i.e: human legs or arms

    Args:
        model (PyNode): Rig top transform node
        ikfk_attr (str): Blend ik fk attribute name
        ui_host (str): Ui host name
        fks ([str]): List of fk controls names
        ik (str): Ik control name
        upv (str): Up vector control name
        ikRot (None, str): optional. Name of the Ik Rotation control
        key (None, bool): optional. Whether we do an snap with animation
    """

    # gets namespace
    current_namespace = getNamespace(model)

    ikFkMatch_with_namespace(
        current_namespace,
        ikfk_attr,
        ui_host,
        fks,
        ik,
        upv,
        ik_rot=ik_rot,
        key=key,
    )


# ==============================================================================
# spine ik/fk matching/switching
# ==============================================================================
def spine_IKToFK(fkControls, ikControls, matchMatrix_dict=None):
    """position the IK controls to match, as best they can, the fk controls.
    Supports component: spine_S_shape_01, spine_ik_02

    Args:
        fkControls (list): list of fk controls, IN THE ORDER OF HIERARCHY,
        ["spine_C0_fk0_ctl", ..., ..., "spine_C0_fk6_ctl"]
        ikControls (list): all ik controls
    """
    if matchMatrix_dict is None:
        currentTime = pm.currentTime(q=True)
        matchMatrix_dict = recordNodesMatrices(
            fkControls, desiredTime=currentTime
        )

    attribute.reset_SRT(ikControls)

    for fk in fkControls:
        fk = pm.PyNode(fk)
        fk.setMatrix(matchMatrix_dict[fk.name()], worldSpace=True)


def spine_FKToIK(fkControls, ikControls, matchMatrix_dict=None):
    """Match the IK controls to the FK. Known limitations: Does not compensate
    for stretching. Does not support zig-zag, or complex fk to ik transfers.
    Supports component: spine_S_shape_01, spine_ik_02

    Args:
        fkControls (list): of of nodes, IN THE ORDER OF HIERARCHY
        ikControls (list): of of nodes
    """
    # record the position of controls prior to reseting
    if matchMatrix_dict is None:
        currentTime = pm.currentTime(q=True)
        matchMatrix_dict = recordNodesMatrices(
            fkControls, desiredTime=currentTime
        )

    # reset both fk, ik controls
    attribute.reset_SRT(ikControls)
    attribute.reset_SRT(fkControls)

    rootFk = fkControls[0]
    endFk = fkControls[-1]
    # get the ik controls sorted from the list provided
    tan1Ctl = [pm.PyNode(ik) for ik in ikControls if TAN1_TOKEN in ik][0]
    tan0Ctl = [pm.PyNode(ik) for ik in ikControls if TAN0_TOKEN in ik][0]

    # get the ik controls sorted from the list provided
    ik1Ctl = [pm.PyNode(ik) for ik in ikControls if END_IK_TOKEN in ik][0]
    ik0Ctl = [pm.PyNode(ik) for ik in ikControls if START_IK_TOKEN in ik][0]

    # optional controls
    ikPosCtl = [pm.PyNode(ik) for ik in ikControls if POS_IK_TOKEN in ik]
    tanCtl = [pm.PyNode(ik) for ik in ikControls if TAN_TOKEN in ik]

    # while the nodes are reset, get the closest counterparts
    if tanCtl:
        closestFk2Tan = getClosestNode(tanCtl[0], fkControls)

    closestFk2Tan1 = getClosestNode(tan1Ctl, fkControls)
    closestFk2Tan0 = getClosestNode(tan0Ctl, fkControls)

    # optional controls if they exist
    if ikPosCtl:
        ikPosCtl[0].setMatrix(matchMatrix_dict[endFk], worldSpace=True)

    # constrain the top and bottom of the ik controls
    ik0Ctl.setMatrix(matchMatrix_dict[rootFk], worldSpace=True)
    ik1Ctl.setMatrix(matchMatrix_dict[endFk], worldSpace=True)

    if tanCtl:
        tanCtl[0].setMatrix(matchMatrix_dict[closestFk2Tan], worldSpace=True)

    # contrain the tan controls
    tan0Ctl.setMatrix(matchMatrix_dict[closestFk2Tan0], worldSpace=True)
    tan1Ctl.setMatrix(matchMatrix_dict[closestFk2Tan1], worldSpace=True)


##################################################
# POSE
##################################################


def getMirrorTarget(nameSpace=None, node=None):
    """Find target control to apply mirroring.

    Args:
        nameSpace (str): Namespace
        node (PyNode): Node to mirror

    Returns:
        PyNode: Mirror target
    """
    if not node:
        return
    if isinstance(node, str):
        node = pm.PyNode(node)

    if isSideElement(node.name()):
        nameParts = stripNamespace(node.name()).split("|")[-1]
        nameParts = swapSideLabelNode(nameParts)
        if nameSpace:
            nameTarget = ":".join([nameSpace, nameParts])
        else:
            nameTarget = nameParts
        return getNode(nameTarget)
    else:
        # Center controls mirror onto self
        return node


def mirrorPose(flip=False, nodes=None):
    """Summary

    Args:
        flip (bool, options): Set the function behaviour to flip
        nodes (None,  [PyNode]): Controls to mirro/flip the pose
    """
    if nodes is None:
        nodes = pm.selected()

    if not nodes:
        return

    pm.undoInfo(ock=1)
    try:
        nameSpace = False
        nameSpace = getNamespace(nodes[0])

        mirrorEntries = []
        for oSel in nodes:
            target = getMirrorTarget(nameSpace, oSel)
            mirrorEntries.extend(calculateMirrorData(oSel, target))

            # To flip a pose, do mirroring both ways.
            if target not in nodes and flip:
                mirrorEntries.extend(calculateMirrorData(target, oSel))

        for dat in mirrorEntries:
            applyMirror(nameSpace, dat)

    except Exception as e:
        pm.displayWarning("Flip/Mirror pose fail")
        pm.displayWarning(
            "If you are using Custom naming rules in controls. "
            "It is possible that the name configuration makes hard to track "
            "the correct object to mirror for {}".format(oSel.name())
        )
        import traceback

        traceback.print_exc()
        print(e)

    finally:
        pm.undoInfo(cck=1)


def applyMirror(nameSpace, mirrorEntry):
    """Apply mirror pose

    Args:
        nameSpace (str): Namespace
        mirrorEntry (list): List with the mirror entry template
    """

    node = mirrorEntry["target"]
    attr = mirrorEntry["attr"]
    val = mirrorEntry["val"]

    for skip in NO_MIRROR_ATTRIBUTES:
        if attr.count(skip):
            return

    try:
        if (
            pm.attributeQuery(attr, node=node, shortName=True, exists=True)
            and not node.attr(attr).isLocked()
        ):
            node.attr(attr).set(val)

    except RuntimeError as e:
        mgear.log(
            "applyMirror failed: {0} {1}: {2}".format(node.name(), attr, e),
            mgear.sev_error,
        )


def calculateMirrorData(srcNode, targetNode, flip=False):
    """Calculate the mirror data

    Args:
        srcNode (str): The source Node
        targetNode ([dict[str]]): Target node
        flip (bool, optional): flip option

    Returns:
        [{"target": node, "attr": at, "val": flipVal}]
    """
    results = []

    # mirror attribute of source
    for attrName in listAttrForMirror(srcNode):

        # whether does attribute "invTx" exists when attrName is "tx"
        invCheckName = getInvertCheckButtonAttrName(attrName)
        if not pm.attributeQuery(
            invCheckName, node=srcNode, shortName=True, exists=True
        ):

            # if not exists, straight
            inv = 1

        else:
            # if exists, check its value
            invAttr = srcNode.attr(invCheckName)
            if invAttr.get():
                inv = -1
            else:
                inv = 1

        # if attr name is side specified, record inverted attr name
        if isSideElement(attrName):
            invAttrName = swapSideLabel(attrName)
        else:
            invAttrName = attrName

        # if flip enabled record self also
        if flip:
            flipVal = targetNode.attr(attrName).get()
            results.append(
                {"target": srcNode, "attr": invAttrName, "val": flipVal * inv}
            )

        results.append(
            {
                "target": targetNode,
                "attr": invAttrName,
                "val": srcNode.attr(attrName).get() * inv,
            }
        )
    return results

def mirrorPoseOld(flip=False, nodes=False):
    """Deprecated: Mirror pose

    Args:
        flip (bool, optional): if True will flip the pose
        nodes (bool, optional): Nodes to mirror or flip transformation
    """
    axis = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]
    aDic = {
        "tx": "invTx",
        "ty": "invTy",
        "tz": "invTz",
        "rx": "invRx",
        "ry": "invRy",
        "rz": "invRz",
        "sx": "invSx",
        "sy": "invSy",
        "sz": "invSz",
    }

    mapDic = {"L": "R", "R": "L"}
    if not nodes:
        nodes = pm.selected()
    pm.undoInfo(ock=1)
    try:
        nameSpace = False
        if nodes:
            if len(nodes[0].split(":")) == 2:
                nameSpace = nodes[0].split(":")[0]
        for oSel in nodes:
            if nameSpace:
                nameParts = oSel.name().split(":")[1].split("|")[-1].split("_")
            else:
                nameParts = oSel.name().split("|")[-1].split("_")

            if nameParts[1][0] == "C":
                if not oSel.attr("tx").isLocked():
                    oSel.attr("tx").set(oSel.attr("tx").get() * -1)
                if not oSel.attr("ry").isLocked():
                    oSel.attr("ry").set(oSel.attr("ry").get() * -1)
                if not oSel.attr("rz").isLocked():
                    oSel.attr("rz").set(oSel.attr("rz").get() * -1)
            else:
                nameParts[1] = mapDic[nameParts[1][0]] + nameParts[1][1:]
                if nameSpace:
                    nameTarget = nameSpace + ":" + "_".join(nameParts)
                else:
                    nameTarget = "_".join(nameParts)
                oTarget = getNode(nameTarget)
                for a in axis:
                    if not oSel.attr(a).isLocked():
                        if oSel.attr(aDic[a]).get():
                            inv = -1
                        else:
                            inv = 1
                        if flip:
                            flipVal = oTarget.attr(a).get()

                        oTarget.attr(a).set(oSel.attr(a).get() * inv)

                        if flip:
                            oSel.attr(a).set(flipVal * inv)
    except Exception:
        pm.displayWarning("Flip/Mirror pose fail")
        pass
    finally:
        pm.undoInfo(cck=1)


def bindPose(model, *args):
    """Restore the reset position of the rig

    Args:
        model (TYPE): Description
    """
    if isinstance(model, pm.PyNode):
        model = bindPose

    nameSpace = getNamespace(model)
    if nameSpace:
        dagPoseName = nameSpace + ":dagPose1"
    else:
        dagPoseName = "dagPose1"
    pm.dagPose(dagPoseName, restore=True)


def resetSelTrans():
    """Reset the transfom values (SRT) for the selected objects"""
    with pm.UndoChunk():
        for obj in pm.selected():
            transform.resetTransform(obj)


def reset_all_keyable_attributes(dagnodes, *args):  # @unusedVariable
    """Resets to default values all keyable attributes on the given node

    Args:
        dagnodes (list): Maya transform nodes to reset
        *args: State of the menu item (if existing) send by mgear's dagmenu
    """

    for node in dagnodes:
        keyable_attrs = cmds.listAttr(node, keyable=True)
        reset_selected_channels_value([node], keyable_attrs)


##################################################
# Transfer space
##################################################
class AbstractAnimationTransfer(QtWidgets.QDialog):
    """Abstract animation transfer class"""

    try:
        valueChanged = QtCore.Signal(int)
    except Exception:
        valueChanged = pyqt.pyqtSignal()

    def __init__(self):
        # type: () -> None

        self.comboObj = None  # type: widgets.toggleCombo
        self.comboItems = []  # type: list[str]
        self.model = None  # type: pm.nodetypes.Transform
        self.uihost = None  # type: str
        self.switchedAttrShortName = None  # type: str

    def createUI(self, parent=None):
        # type: (QtWidgets.QObject) -> None

        super(AbstractAnimationTransfer, self).__init__(parent)

        self.setWindowTitle("Space Transfer")
        self.setWindowFlags(QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)

        self.create_controls()
        self.create_layout()
        self.create_connections()

    def create_controls(self):
        # type: () -> None

        self.groupBox = QtWidgets.QGroupBox()

        # must be implemented in each specialized classes
        self.setGroupBoxTitle()

        self.onlyKeyframes_check = QtWidgets.QCheckBox("Only Keyframe Frames")
        self.onlyKeyframes_check.setChecked(True)
        self.startFrame_label = QtWidgets.QLabel("Start")
        self.startFrame_value = QtWidgets.QSpinBox()
        self.startFrame_value = QtWidgets.QSpinBox()
        self.startFrame_value.setMinimum(-999999)
        self.startFrame_value.setMaximum(999999)
        self.endFrame_label = QtWidgets.QLabel("End")
        self.endFrame_value = QtWidgets.QSpinBox()
        self.endFrame_value.setMinimum(-999999)
        self.endFrame_value.setMaximum(999999)
        self.populateRange(True)
        self.allFrames_button = QtWidgets.QPushButton("All Frames")
        self.timeSliderFrames_button = QtWidgets.QPushButton(
            "Time Slider Frames"
        )

        self.comboBoxSpaces = QtWidgets.QComboBox()
        self.comboBoxSpaces.addItems(self.comboItems)
        if self.comboObj is not None:
            # this add suport QlistWidget
            if isinstance(self.comboObj, QtWidgets.QListWidget):
                idx = self.comboObj.currentRow()
            else:
                idx = self.comboObj.currentIndex()
            self.comboBoxSpaces.setCurrentIndex(idx)

        self.spaceTransfer_button = QtWidgets.QPushButton("Space Transfer")

    def create_layout(self):
        # type: () -> None

        frames_layout = QtWidgets.QHBoxLayout()
        frames_layout.setContentsMargins(1, 1, 1, 1)
        frames_layout.addWidget(self.startFrame_label)
        frames_layout.addWidget(self.startFrame_value)
        frames_layout.addWidget(self.endFrame_label)
        frames_layout.addWidget(self.endFrame_value)

        framesSetter_layout = QtWidgets.QHBoxLayout()
        framesSetter_layout.setContentsMargins(1, 1, 1, 1)
        framesSetter_layout.addWidget(self.allFrames_button)
        framesSetter_layout.addWidget(self.timeSliderFrames_button)

        paremeter_layout = QtWidgets.QVBoxLayout(self.groupBox)
        paremeter_layout.setContentsMargins(6, 5, 6, 5)
        paremeter_layout.addWidget(self.onlyKeyframes_check)
        paremeter_layout.addLayout(frames_layout)
        paremeter_layout.addLayout(framesSetter_layout)
        paremeter_layout.addWidget(self.comboBoxSpaces)
        paremeter_layout.addWidget(self.spaceTransfer_button)

        spaceTransfer_layout = QtWidgets.QVBoxLayout()
        spaceTransfer_layout.addWidget(self.groupBox)

        self.setLayout(spaceTransfer_layout)

    def create_connections(self):
        # type: () -> None

        self.spaceTransfer_button.clicked.connect(self.doItByUI)
        self.allFrames_button.clicked.connect(
            partial(self.populateRange, False)
        )
        self.timeSliderFrames_button.clicked.connect(
            partial(self.populateRange, True)
        )

    # SLOTS ##########################################################

    def populateRange(self, timeSlider=False):
        # type: (bool) -> None
        if timeSlider:
            start = pm.playbackOptions(q=True, min=True)
            end = pm.playbackOptions(q=True, max=True)
        else:
            start = pm.playbackOptions(q=True, ast=True)
            end = pm.playbackOptions(q=True, aet=True)
        self.startFrame_value.setValue(start)
        self.endFrame_value.setValue(end)

    def setComboBoxItemsFormComboObj(self, combo):
        # type: (widegts.toggleCombo or QtWidgets.QListWidget) -> None

        del self.comboItems[:]
        for i in range(combo.count() - 1):
            # this add suport QlistWidget
            if isinstance(combo, QtWidgets.QListWidget):
                self.comboItems.append(combo.item(i).text())
            else:
                self.comboItems.append(combo.itemText(i))

    def setComboBoxItemsFormList(self, comboList):
        # type: (list[str]) -> None

        del self.comboItems[:]
        for i in range(len(comboList)):
            self.comboItems.append(comboList[i])

    # ----------------------------------------------------------------

    def setGroupBoxTitle(self):
        # type: (str) -> None
        # raise NotImplementedError("must implement transfer
        # in each specialized class")
        pass

    def setComboObj(self, combo):
        # type: (widgets.toggleCombo) -> None
        self.comboObj = combo

    def setModel(self, model):
        # type: (pm.nodetypes.Transform) -> None
        self.model = model
        self.nameSpace = getNamespace(self.model)

    def setUiHost(self, uihost):
        # type: (str) -> None
        self.uihost = uihost

    def setSwitchedAttrShortName(self, attr):
        # type: (str) -> None
        self.switchedAttrShortName = attr

    def getHostName(self):
        # type: () -> str
        return ":".join([self.nameSpace, self.uihost])

    def getWorldMatrices(
        self, start, end, val_src_nodes, pole_vector_matrices=None
    ):
        # type: (int, int, List[pm.nodetypes.Transform]) ->
        # List[List[pm.datatypes.Matrix]]
        """returns matrice List[frame][controller number]."""
        if pole_vector_matrices is None:
            pole_vector_matrices = []
        res = []
        for idx, x in enumerate(range(start, end + 1)):
            tmp = []
            for n in val_src_nodes:
                tmp.append(pm.getAttr(n + ".worldMatrix", time=x))
            try:
                tmp[-1] = pole_vector_matrices[idx]
            except IndexError:
                pass
            res.append(tmp)
        return res

    def getIKPoleVectorMatrices(self, start, end, fkc):
        # type: (int, int, List[pm.nodetypes.Transform]) ->
        # List[List[pm.datatypes.Matrix]]
        """returns matrice List[frame][controller number]."""
        from . import vector, transform

        res = []
        for x in range(start, end + 1):
            a, b, c, dist = fkc + [1.0]
            v = vector.calculatePoleVector(a, b, c, dist, time=x)
            # this needs to be a matrix for the get set method used in the
            # transfer main loop
            m = transform.setMatrixPosition(pm.dt.Matrix(), v)
            res.append(m)
        return res

    def transfer(self, startFrame, endFrame, onlyKeyframes, *args, **kwargs):
        # type: (int, int, bool, *str, **str) -> None
        raise NotImplementedError(
            "must be implemented in each " "specialized class"
        )

    def doItByUI(self):
        # type: () -> None

        # gather settings from UI
        startFrame = self.startFrame_value.value()
        endFrame = self.endFrame_value.value()
        onlyKeyframes = self.onlyKeyframes_check.isChecked()

        # main body
        self.transfer(startFrame, endFrame, onlyKeyframes)

        # set the new space value in the synoptic combobox
        if self.comboObj is not None:
            if isinstance(self.comboObj, QtWidgets.QComboBox):
                self.comboObj.setCurrentIndex(
                    self.comboBoxSpaces.currentIndex()
                )

        for c in pyqt.maya_main_window().children():
            if isinstance(c, AbstractAnimationTransfer):
                c.deleteLater()

    @utils.one_undo
    @utils.viewport_off
    def bakeAnimation(
        self,
        switch_attr_name,
        val_src_nodes,
        key_src_nodes,
        key_dst_nodes,
        startFrame,
        endFrame,
        onlyKeyframes=True,
        definition="",
    ):

        # type: (str, List[pm.nodetypes.Transform],
        # List[pm.nodetypes.Transform],
        # List[pm.nodetypes.Transform], int, int, bool) -> None

        # Temporaly turn off cycle check to avoid misleading cycle message
        # on Maya 2016.  With Maya 2016.5 and 2017 the cycle warning doesn't
        # show up
        # if versions.current() <= 20180200:
        pm.cycleCheck(e=False)
        pm.displayWarning(
            "Maya version older than: 2016.5: " "CycleCheck temporal turn OFF"
        )

        channels = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]

        # right here we need to generate the matrix positions by calculating
        # them if we have 3 fk controls.  Once we've grabbed the solved
        # pole vector positions, we'll insert them into the list by passing
        # them into the getWorldMatrix function.
        # Doing it thisway should be safe as we've touched the least amount
        # of code.
        poleVectorMatrices = []
        if definition.upper() == "IK":
            if len(key_src_nodes) == 3:
                poleVectorMatrices = self.getIKPoleVectorMatrices(
                    startFrame, endFrame, key_src_nodes
                )

        worldMatrixList = self.getWorldMatrices(
            startFrame, endFrame, val_src_nodes, poleVectorMatrices
        )

        keyframeList = sorted(
            set(pm.keyframe(key_src_nodes, at=["t", "r", "s"], q=True))
        )

        # delete animation in the space switch channel and destination ctrls
        pm.cutKey(key_dst_nodes, at=channels, time=(startFrame, endFrame))
        pm.cutKey(switch_attr_name, time=(startFrame, endFrame))

        for i, x in enumerate(range(startFrame, endFrame + 1)):

            if onlyKeyframes and x not in keyframeList:
                continue

            pm.currentTime(x)

            # set the new space in the channel
            self.changeAttrToBoundValue()

            # bake the stored transforms to the cotrols
            for j, n in enumerate(key_dst_nodes):
                n.setMatrix(worldMatrixList[i][j], worldSpace=True)

            pm.setKeyframe(key_dst_nodes, at=channels)
            pm.setKeyframe(switch_attr_name)

        # if versions.current() <= 20180200:
        pm.cycleCheck(e=True)
        pm.displayWarning("CycleCheck turned back ON")


# ================================================
# Transfer space


class ParentSpaceTransfer(AbstractAnimationTransfer):
    def __init__(self):
        # type: () -> None
        super(ParentSpaceTransfer, self).__init__()

    # ----------------------------------------------------------------

    def setCtrls(self, srcName):
        # type: (str) -> None
        self.ctrlNode = getNode(":".join([self.nameSpace, srcName]))

    def getChangeAttrName(self):
        # type: () -> str
        return "{}.{}".format(self.getHostName(), self.switchedAttrShortName)

    def changeAttrToBoundValue(self):
        # type: () -> None
        pm.setAttr(self.getChangeAttrName(), self.getValue())

    def getValue(self):
        # type: () -> int
        return self.comboBoxSpaces.currentIndex()

    def setGroupBoxTitle(self):
        if hasattr(self, "groupBox"):
            # TODO: extract logic with naming convention
            part = "_".join(
                self.ctrlNode.name().split(":")[-1].split("_")[:-1]
            )
            self.groupBox.setTitle(part)

    def transfer(self, startFrame, endFrame, onlyKeyframes, *args, **kwargs):
        # type: (int, int, bool, *str, **str) -> None

        val_src_nodes = [self.ctrlNode]
        key_src_nodes = val_src_nodes
        key_dst_nodes = val_src_nodes

        self.bakeAnimation(
            self.getChangeAttrName(),
            val_src_nodes,
            key_src_nodes,
            key_dst_nodes,
            startFrame,
            endFrame,
            onlyKeyframes,
        )

    @staticmethod
    def showUI(combo, model, uihost, switchedAttrShortName, ctrl_name, *args):
        # type: (widgets.toggleCombo,
        # pm.nodetypes.Transform, str, str, str, *str) -> None

        try:
            for c in pyqt.maya_main_window().children():
                if isinstance(c, ParentSpaceTransfer):
                    c.deleteLater()

        except RuntimeError:
            pass

        # Create minimal UI object
        ui = ParentSpaceTransfer()
        ui.setComboObj(combo)
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(switchedAttrShortName)
        ui.setCtrls(ctrl_name)
        ui.setComboBoxItemsFormComboObj(ui.comboObj)

        # Delete the UI if errors occur to avoid causing winEvent
        # and event errors (in Maya 2014)
        try:
            ui.createUI(pyqt.maya_main_window())
            ui.show()

        except Exception as e:
            ui.deleteLater()
            traceback.print_exc()
            mgear.log(e, mgear.sev_error)


class IkFkTransfer(AbstractAnimationTransfer):
    def __init__(self):
        # type: () -> None
        super(IkFkTransfer, self).__init__()
        self.getValue = self.getValueFromUI

    # ----------------------------------------------------------------

    def getChangeAttrName(self):
        # type: () -> str
        return "{}.{}".format(self.getHostName(), self.switchedAttrShortName)

    def getChangeRollAttrName(self):
        # type: () -> str
        at_name = self.switchedAttrShortName.replace("blend", "roll")
        at = "{}.{}".format(
            self.getHostName(),
            self.switchedAttrShortName.replace("blend", "roll"),
            at_name,
        )
        if pm.objExists(at):
            return at
        else:
            return self.ikCtrl[0].attr(at_name)

    def changeAttrToBoundValue(self):
        # type: () -> None
        pm.setAttr(self.getChangeAttrName(), self.getValue())

    def getValueFromUI(self):
        # type: () -> float
        if self.comboBoxSpaces.currentIndex() == 0:
            # IK
            return 1.0
        else:
            # FK
            return 0.0

    def _getNode(self, name):
        # type: (str) -> pm.nodetypes.Transform
        node = getNode(":".join([self.nameSpace, name]))

        if not node:
            mgear.log("Can't find object : {0}".format(name), mgear.sev_error)

        return node

    def _getMth(self, name):
        # type: (str) -> pm.nodetypes.Transform
        node = self._getNode(name)
        if node.hasAttr("match_ref"):
            match_node = node.match_ref.listConnections()
            if match_node:
                return match_node[0]
        else:
            tmp = name.split("_")
            tmp[-1] = "mth"
            return self._getNode("_".join(tmp))

    def setCtrls(self, fks, ik, upv, ikRot):
        # type: (list[str], str, str) -> None
        """gather core PyNode represented each controllers"""

        if not isinstance(ik, list):
            ik = [ik]
        if not isinstance(upv, list):
            upv = [upv]

        self.fkCtrls = [self._getNode(x) for x in fks]
        self.fkTargets = [self._getMth(x) for x in fks]

        self.ikCtrl = [self._getNode(x) for x in ik]
        self.ikTarget = [self._getMth(x) for x in ik]

        self.upvCtrl = [self._getNode(x) for x in upv]
        self.upvTarget = [self._getMth(x) for x in upv]

        if ikRot:
            # self.ikRotCtl = self._getNode(ikRot)
            # self.ikRotTarget = self._getMth(ikRot)
            if not isinstance(ikRot, list):
                ikRot = [ikRot]

            self.ikRotCtl = [self._getNode(x) for x in ikRot]
            self.ikRotTarget = [self._getMth(x) for x in ikRot]
            self.hasIkRot = True
        else:
            self.hasIkRot = False

    def setGroupBoxTitle(self):
        if hasattr(self, "groupBox"):
            if len(self.ikCtrl) == 1:
                # TODO: extract logic with naming convention
                part = "_".join(
                    self.ikCtrl[0].name().split(":")[-1].split("_")[:-2]
                )
            else:
                part = "MULTI Transfer"

            self.groupBox.setTitle(part)

    # ----------------------------------------------------------------

    def transfer(
        self,
        startFrame,
        endFrame,
        onlyKeyframes,
        ikRot,
        switchTo=None,
        *args,
        **kargs
    ):
        # type: (int, int, bool, str, *str, **str) -> None

        def fk_definition():
            src_nodes = self.fkTargets[:]
            key_nodes = self.ikCtrl[:] + self.upvCtrl[:]
            dst_nodes = self.fkCtrls[:]
            if ikRot:
                if isinstance(self.ikRotCtl, list):
                    key_nodes.extend(self.ikRotCtl)
                else:
                    key_nodes.append(self.ikRotCtl)
            return src_nodes, key_nodes, dst_nodes, "FK"

        def ik_definition():
            src_nodes = self.ikTarget + self.upvTarget
            key_nodes = self.fkCtrls
            dst_nodes = self.ikCtrl + self.upvCtrl
            if ikRot:
                if isinstance(self.ikRotTarget, list):
                    src_nodes.extend(self.ikRotTarget)
                else:
                    src_nodes.append(self.ikRotTarget)
                if isinstance(self.ikRotCtl, list):
                    key_nodes.extend(self.ikRotCtl)
                else:
                    key_nodes.append(self.ikRotCtl)

            roll_att = self.getChangeRollAttrName()
            pm.cutKey(roll_att, time=(startFrame, endFrame), cl=True)
            pm.setAttr(roll_att, 0)

            return src_nodes, key_nodes, dst_nodes, "IK"

        if switchTo is not None:
            if "fk" in switchTo.lower():
                val_src_n, key_src_n, key_dst_n, definition = fk_definition()
            else:
                val_src_n, key_src_n, key_dst_n, definition = ik_definition()
        else:
            if self.comboBoxSpaces.currentIndex() != 0:  # to FK
                val_src_n, key_src_n, key_dst_n, definition = fk_definition()
            else:  # to IK
                val_src_n, key_src_n, key_dst_n, definition = ik_definition()

        self.bakeAnimation(
            self.getChangeAttrName(),
            val_src_n,
            key_src_n,
            key_dst_n,
            startFrame,
            endFrame,
            onlyKeyframes,
            definition,
        )

    # ----------------------------------------------------------------
    # re implement doItbyUI to have access to self.hasIKrot option
    def doItByUI(self):
        # type: () -> None

        # gather settings from UI
        startFrame = self.startFrame_value.value()
        endFrame = self.endFrame_value.value()
        onlyKeyframes = self.onlyKeyframes_check.isChecked()

        # main body
        self.transfer(startFrame, endFrame, onlyKeyframes, self.hasIkRot)

        # set the new space value in the synoptic combobox
        if self.comboObj is not None:
            self.comboObj.setCurrentIndex(self.comboBoxSpaces.currentIndex())

        for c in pyqt.maya_main_window().children():
            if isinstance(c, AbstractAnimationTransfer):
                c.deleteLater()

    # ----------------------------------------------------------------

    @staticmethod
    def showUI(model, ikfk_attr, uihost, fks, ik, upv, ikRot, *args):
        # type: (pm.nodetypes.Transform, str, str,
        # List[str], str, str, *str) -> None

        try:
            for c in pyqt.maya_main_window().children():
                if isinstance(c, IkFkTransfer):
                    c.deleteLater()

        except RuntimeError:
            pass

        # Create minimal UI object
        ui = IkFkTransfer()
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(ikfk_attr)
        ui.setCtrls(fks, ik, upv, ikRot)
        ui.setComboObj(None)
        ui.setComboBoxItemsFormList(["IK", "FK"])

        # Delete the UI if errors occur to avoid causing winEvent
        # and event errors (in Maya 2014)
        try:
            ui.createUI(pyqt.maya_main_window())
            ui.show()

        except Exception as e:
            ui.deleteLater()
            traceback.print_exc()
            mgear.log(e, mgear.sev_error)

    @staticmethod
    def execute(
        model,
        ikfk_attr,
        uihost,
        fks,
        ik,
        upv,
        ikRot=None,
        startFrame=None,
        endFrame=None,
        onlyKeyframes=None,
        switchTo=None,
    ):
        # type: (pm.nodetypes.Transform, str, str,
        # List[str], str, str, int, int, bool, str) -> None
        """transfer without displaying UI"""

        if startFrame is None:
            startFrame = int(pm.playbackOptions(q=True, ast=True))

        if endFrame is None:
            endFrame = int(pm.playbackOptions(q=True, aet=True))

        if onlyKeyframes is None:
            onlyKeyframes = True

        if switchTo is None:
            switchTo = "fk"

        # Create minimal UI object
        ui = IkFkTransfer()

        ui.setComboObj(None)
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(ikfk_attr)
        ui.setCtrls(fks, ik, upv, ikRot)
        ui.setComboBoxItemsFormList(["IK", "FK"])
        ui.getValue = lambda: 0.0 if "fk" in switchTo.lower() else 1.0
        ui.transfer(startFrame, endFrame, onlyKeyframes, ikRot, switchTo="fk")

    @staticmethod
    def toIK(model, ikfk_attr, uihost, fks, ik, upv, ikRot, **kwargs):
        # type: (pm.nodetypes.Transform, str, str,
        # List[str], str, str, **str) -> None

        kwargs.update({"switchTo": "ik"})
        IkFkTransfer.execute(
            model, ikfk_attr, uihost, fks, ik, upv, ikRot, **kwargs
        )

    @staticmethod
    def toFK(model, ikfk_attr, uihost, fks, ik, upv, ikRot, **kwargs):
        # type: (pm.nodetypes.Transform, str, str,
        # List[str], str, str, **str) -> None

        kwargs.update({"switchTo": "fk"})
        IkFkTransfer.execute(
            model, ikfk_attr, uihost, fks, ik, upv, ikRot, **kwargs
        )


# Baker Springs


@utils.one_undo
def clearSprings(model=None):
    """Delete baked animation from spring

    Args:
        model (dagNode): The rig top node
    """

    # filters the root node from selection
    if not model:
        model = getRootNode()

    springNodes = getControlers(model, gSuffix=PLOT_GRP_SUFFIX)
    pairblends = [
        sn.listConnections(type="pairBlend")[0] for sn in springNodes
    ]

    for pb in pairblends:
        animCrvs = pb.listConnections(type="animCurveTA")
        for fcrv in animCrvs:
            for conn in fcrv.listConnections(
                connections=True, destination=True, plugs=True
            ):

                pm.disconnectAttr(conn[0], conn[1])
        # reset the value to 0
        attrs = ["inRotateX1", "inRotateY1", "inRotateZ1"]
        for attr in attrs:
            pb.attr(attr).set(0)

        # delete fcurves
        pm.delete(animCrvs)


@utils.one_undo
@utils.viewport_off
def bakeSprings(model=None):
    """Bake the automatic spring animation to animation curves

    Args:
        model (dagNode): The rig top node
    """

    # filters the root node from selection
    if not model:
        model = getRootNode()

    print("Using root: {}".format(model))

    # first clear animation
    clearSprings(model)

    # bake again
    springNodes = getControlers(model, gSuffix=PLOT_GRP_SUFFIX)
    if springNodes:

        start = pm.playbackOptions(q=True, min=True)
        end = pm.playbackOptions(q=True, max=True)
        ct = start
        for i in range(int(end - start) + 1):
            pm.currentTime(int(ct))
            pm.setKeyframe(springNodes, insertBlend=True, attribute="rotate")
            ct += 1


class SpineIkFkTransfer(AbstractAnimationTransfer):
    def __init__(self):
        super(SpineIkFkTransfer, self).__init__()
        self.fkControls = None
        self.ikControls = None

    def doItByUI(self):
        """Gather UI settings to execute transfer"""
        startFrame = self.startFrame_value.value()
        endFrame = self.endFrame_value.value()
        onlyKeyframes = self.onlyKeyframes_check.isChecked()

        # based on user input, decide where to flatten animation
        bakeToIk = self.comboBoxSpaces.currentIndex()

        self.bakeAnimation(
            self.fkControls,
            self.ikControls,
            startFrame,
            endFrame,
            bakeToIk=bakeToIk,
            onlyKeyframes=onlyKeyframes,
        )

        # Refresh the viewport by toggling time, refresh/dgdirty do not work
        pm.currentTime(startFrame)
        pm.currentTime(endFrame)
        # set the new space value in the synoptic combobox
        if self.comboObj is not None:
            self.comboObj.setCurrentIndex(self.comboBoxSpaces.currentIndex())

        for c in pyqt.maya_main_window().children():
            if isinstance(c, AbstractAnimationTransfer):
                c.deleteLater()

    def setCtrls(self, fkControls, ikControls):
        """make provided controls accessible to the class, with namespaces

        Args:
            fkControls (list): of fk  controls
            ikControls (list): of ik controls
        """
        ns = self.nameSpace
        if not ns.endswith(":") and ns != "":
            ns = "{0}:".format(ns)
        self.fkControls = ["{0}{1}".format(ns, x) for x in fkControls]
        self.ikControls = ["{0}{1}".format(ns, x) for x in ikControls]

    @staticmethod
    def showUI(topNode, uihost, fkControls, ikControls, *args):
        """Called from the synaptic qpushbutton, with the spine control names

        Args:
            topNode (string): top node of the rig
            uihost (TYPE): Description
            fkControls (list): of fkControls
            ikControls (list): of ikControls
            *args: additional signal args, n/a
        """
        try:
            for c in pyqt.maya_main_window().children():
                if isinstance(c, IkFkTransfer):
                    c.deleteLater()

        except RuntimeError:
            pass

        # Create minimal UI object
        ui = SpineIkFkTransfer()
        ui.setModel(topNode)
        ui.setUiHost(uihost)
        ui.setCtrls(fkControls, ikControls)
        ui.setComboObj(None)
        ui.setComboBoxItemsFormList(["IK >> FK", "FK >> IK"])

        # Delete the UI if errors occur to avoid causing winEvent
        # and event errors (in Maya 2014)
        try:
            ui.createUI(pyqt.maya_main_window())
            ui.setWindowTitle("Spine IKFK")
            ui.show()

        except Exception as e:
            ui.deleteLater()
            traceback.print_exc()
            mgear.log(e, mgear.sev_error)

    @utils.one_undo
    @utils.viewport_off
    def bakeAnimation(
        self,
        fkControls,
        ikControls,
        startFrame,
        endFrame,
        bakeToIk=True,
        onlyKeyframes=True,
    ):
        """bake animation to desired destination. More adding animtion than
        ik/fk transfer

        Args:
            fkControls (list): of fk controls
            ikControls (list): of ik controls
            startFrame (float): start frame
            endFrame (float): end frame
            bakeToIk (bool, optional): True, bake animation to ik, fk is false
            onlyKeyframes (bool, optional): transfer animation on other
            keyframes, if false, bake every frame
        """
        # Temporaly turn off cycle check to avoid misleading cycle message
        # on Maya 2016.  With Maya 2016.5 and 2017 the cycle warning doesn't
        # show up
        if bakeToIk:
            key_src_nodes = fkControls
            transferFunc = spine_FKToIK
            key_dst_nodes = ikControls
        else:
            key_src_nodes = ikControls
            transferFunc = spine_IKToFK
            key_dst_nodes = fkControls

        # add all nodes, to get all of the keyframes
        allAnimNodes = fkControls + ikControls
        # remove duplicates
        keyframeList = sorted(
            set(pm.keyframe(allAnimNodes, at=["t", "r", "s"], q=True))
        )

        # when getAttr over time, it warns of a cycle
        if versions.current() <= 20180200:
            pm.cycleCheck(e=False)
            print("Maya version older than: 2018.02")

        # create a dict of every frame, and every node involved on that frame
        matchMatrix_dict = {}
        for i, x in enumerate(range(startFrame, endFrame + 1)):
            if onlyKeyframes and x not in keyframeList:
                continue
            matchMatrix_dict[x] = recordNodesMatrices(fkControls, x)

        channels = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]

        # delete animation in the channel and destination ctrls
        pm.cutKey(fkControls, at=channels, time=(startFrame, endFrame))
        pm.cutKey(ikControls, at=channels, time=(startFrame, endFrame))

        if PY2:
            dic_items = matchMatrix_dict.iteritems
        else:
            dic_items = matchMatrix_dict.items

        for frame, matchDict in dic_items():
            pm.currentTime(frame)
            transferFunc(fkControls, ikControls, matchMatrix_dict=matchDict)

            pm.setKeyframe(key_dst_nodes, at=channels)
        # If there are keys on the source node outside of the provided range
        # this wont have an effect
        attribute.reset_SRT(key_src_nodes)

        # re enable cycle check
        if versions.current() <= 20180200:
            pm.cycleCheck(e=True)
            print("CycleCheck turned back ON")
