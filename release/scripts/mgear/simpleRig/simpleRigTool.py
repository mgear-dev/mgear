import datetime
import getpass
import json
import sys

import mgear
import mgear.core.icon as ico
import mgear.pymaya as pm
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from mgear import shifter
from mgear.core import transform, node, attribute, applyop, pyqt, utils, curve
from mgear.vendor.Qt import QtCore, QtWidgets
from mgear.pymaya import versions
from mgear.pymaya import datatypes

from mgear.core import string
from mgear.simpleRig import simpleRigUI as srUI

CTL_TAG_ATTR = "is_simple_rig_ctl"
RIG_ROOT = "rig"

if sys.version_info[0] == 2:
    string_types = (basestring,)
else:
    string_types = (str,)

# driven attr ===========================================


def _driven_attr(dagNode):
    """message attribute to store a list of object affected
    by the root or pivot

    Args:
        dagNode (PyNode): dagNode

    Returns:
        Attr: Attribute
    """
    if not dagNode.hasAttr("drivenElements"):
        dagNode.addAttr("drivenElements", attributeType="message", multi=True)
    return dagNode.attr("drivenElements")


def _add_to_driven_attr(dagNode, driven):
    """add one or more elements to the driven list
    should check is not in another driven attr and remove from others

    Args:
        dagNode (PyNode): dagNode with the attribute
        driven (PyNode): driven elements
    """

    d_attr = _driven_attr(dagNode)
    if not isinstance(driven, list):
        driven = [driven]
    for d in driven:
        if not _is_valid_ctl(d):
            _remove_from_driven_attr(d)
            ni = _get_driven_attr_next_available_index(d_attr)
            pm.connectAttr(
                d.message, d_attr.attr("drivenElements[{}]".format(str(ni)))
            )
        else:
            pm.displayWarning(
                "{} is a simple rig control and can't be "
                " driven by another control".format(d)
            )


def _remove_from_driven_attr(driven):
    """Remove one or more elements to the driven attr

    Args:
        driven (list of dagNode): Driven elements
    """

    if not isinstance(driven, list):
        driven = [driven]
    for x in driven:
        for o in x.message.connections(p=True):
            if "drivenElements" in o.name():
                pm.disconnectAttr(x.message, o)


def _get_from_driven_attr(dagNode):
    """Return a list of all elements in the driven attr as PyNodes

    Args:
        dagNode (PyNode): Driver dagNode

    Returns:
        TYPE: Description
    """

    d_attr = _driven_attr(dagNode)
    return d_attr.inputs()


def _get_driven_attr_next_available_index(d_attr):
    """Get the next available index for the drivenElements attr

    Args:
        d_attr (attr): driven attribute

    Returns:
        int: next available index
    """
    return attribute.get_next_available_index(d_attr)


# creators ===========================================

# @utils.timeFunc
def _create_control(
    name,
    t,
    radio,
    parent=None,
    icon="circle",
    side="C",
    indx=0,
    color=17,
    driven=None,
    sets_config=None,
):
    """Crete control

    Args:
        name (str): Name of the control
        t (matrix): transform matrix
        radio (double): Size Radio
        parent (dagNode, optional): Parent Control
        icon (str, optional): Icon shape
        side (str, optional): Side. Can be C, L or R
        indx (int, optional): Index
        color (int, optional): Colort
        driven (None, optional): Driven elements
        sets_config (None, optional): Groups/sets where the new control will be
            added

    Returns:
        dagNode: New control
    """
    name = _validate_name(name)
    # @utils.timeFunc
    def _set_name(extension):
        if side:
            fullName = "{}_{}{}_{}".format(name, side, str(indx), extension)
            i = 0
            while pm.ls(fullName):
                i += 1
                fullName = "{}_{}{}_{}".format(name, side, str(i), extension)
        else:
            fullName = "{}_{}".format(name, extension)
        return fullName

    npo = pm.createNode("transform", n=_set_name("npo"))
    npo.setTransformation(t)
    if parent:
        pm.parent(npo, parent)
    attribute.lockAttribute(npo)

    ctl = ico.create(
        npo,
        _set_name("ctl"),
        t,
        color,
        icon=icon,
        w=radio * 2,
        h=radio * 2,
        d=radio * 2,
    )

    attribute.addAttribute(ctl, "conf_icon", "string", icon)
    attribute.addAttribute(ctl, "conf_sets", "string", sets_config)
    attribute.addAttribute(ctl, "conf_radio", "float", radio, keyable=False)
    attribute.addAttribute(ctl, "conf_color", "long", color, keyable=False)
    attribute.addAttribute(ctl, CTL_TAG_ATTR, "bool", True, keyable=False)
    attribute.addAttribute(ctl, "edit_mode", "bool", False, keyable=False)
    # pm.parent(ctl, npo)
    attribute.setKeyableAttributes(ctl)

    if driven:
        if not isinstance(driven, list):
            driven = [driven]
        _add_to_driven_attr(ctl, driven)
        _update_driven(ctl)

    grp = _get_sets_grp()
    grp.add(ctl)
    if sets_config:
        for ef in _extra_sets(sets_config):
            ef.add(ctl)

    return ctl


def _create_base_structure(rigName):
    """Create base structure

    Args:
        rigName (str): Rig name

    Returns:
        dagNode: rig root
    """

    rig = pm.createNode("transform", n=rigName)

    attribute.addAttribute(rig, "is_rig", "bool", True, keyable=False)
    attribute.addAttribute(rig, "is_simple_rig", "bool", True, keyable=False)
    attribute.addAttribute(rig, "geoUnselectable", "bool", True)
    attribute.addAttribute(rig, "rig_name", "string", rigName)
    attribute.addAttribute(rig, "user", "string", getpass.getuser())
    attribute.addAttribute(rig, "date", "string", str(datetime.datetime.now()))

    attribute.addAttribute(
        rig,
        "maya_version",
        "string",
        str(pm.mel.eval("getApplicationVersionAsFloat")),
    )

    attribute.addAttribute(rig, "gear_version", "string", mgear.getVersion())
    attribute.addAttribute(rig, "ctl_vis", "bool", True)
    attribute.addAttribute(rig, "jnt_vis", "bool", False)

    attribute.addAttribute(rig, "quickselA", "string", "")
    attribute.addAttribute(rig, "quickselB", "string", "")
    attribute.addAttribute(rig, "quickselC", "string", "")
    attribute.addAttribute(rig, "quickselD", "string", "")
    attribute.addAttribute(rig, "quickselE", "string", "")
    attribute.addAttribute(rig, "quickselF", "string", "")
    attribute.addAttribute(rig, "synoptic", "string", "")
    attribute.addAttribute(rig, "comments", "string", "")

    rig.addAttr("rigGroups", at="message", m=1)
    rig.addAttr("rigPoses", at="message", m=1)
    rig.addAttr("rigCtlTags", at="message", m=1)

    # Create sets
    meshList = []
    ctlList = []

    ctlSet = pm.sets(ctlList, n="{}_controllers_grp".format(rigName))
    deformersSet = pm.sets(meshList, n="{}_deformers_grp".format(rigName))
    compGroup = pm.sets(meshList, n="{}_componentsRoots_grp".format(rigName))

    rigSets = pm.sets([ctlSet, deformersSet, compGroup], n="rig_sets_grp")

    pm.connectAttr(rigSets.attr("message"), "{}.rigGroups[0]".format(rigName))
    pm.connectAttr(ctlSet.attr("message"), "{}.rigGroups[2]".format(rigName))
    pm.connectAttr(
        deformersSet.attr("message"), "{}.rigGroups[3]".format(rigName)
    )
    pm.connectAttr(
        compGroup.attr("message"), "{}.rigGroups[4]".format(rigName)
    )

    return rig


@utils.one_undo
# @utils.timeFunc
def _create_simple_rig_root(
    rigName=RIG_ROOT,
    selection=None,
    world_ctl=True,
    sets_config=None,
    ctl_wcm=False,
    fix_radio=False,
    radio_val=100,
    gl_shape="square",
    w_shape="circle",
):
    """Create the simple rig root

    create the simple rig root
    have the attr: is_simple_rig and is_rig
    should not create if there is a another simple rig root
    should have synoptic attr. (synoptic configuration in UI)
    use World_ctl should be optional

    Args:
        rigName (str, optional): Rig Name
        selection (dagNode list, optional): Elements selected to be included
            in the rig
        world_ctl (bool, optional): if True, will create world_ctl
        sets_config (None, optional): Groups to include the ctl
        ctl_wcm (bool, optional): If True, the world_ctl will ve placed in the
            scene world center
        fix_radio (bool, optional): If True, will use a fix radio value,
            instead of the bbox radio
        radio_val (int, optional): Fix value for Radio
        gl_shape (str, optional): Global and local control shape
        w_shape (str, optional): World control shape

    Returns:
        dagNode: local control
    """

    # check if there is another rig root in the scene
    rig_models = _get_simple_rig_root()
    if rig_models:
        pm.displayWarning(
            "Simple rig root already exist in the "
            "scene: {}".format(str(rig_models))
        )
        return

    if not selection:
        if pm.selected():
            selection = pm.selected()
        else:
            pm.displayWarning("Selection is needed to create the root")
            return

    volCenter, radio, bb = _get_branch_bbox_data(selection)

    if fix_radio:
        radio = radio_val

    rig = _create_base_structure(rigName)

    if ctl_wcm:
        t = datatypes.Matrix()
    else:
        t = transform.getTransformFromPos(volCenter)

    # configure selectable geo
    connect_selectable(rig, selection)

    ctt = None
    # create world ctl
    if world_ctl:
        world_ctl = _create_control(
            "world",
            t,
            radio * 1.5,
            parent=rig,
            icon=w_shape,
            side=None,
            indx=0,
            color=13,
            driven=None,
            sets_config=sets_config,
        )
        if versions.current() >= 201650:
            ctt = node.add_controller_tag(world_ctl, None)
            _connect_tag_to_rig(rig, ctt)
    else:
        world_ctl = rig

    # create global ctl
    global_ctl = _create_control(
        "global",
        t,
        radio * 1.1,
        parent=world_ctl,
        icon=gl_shape,
        side="C",
        indx=0,
        color=17,
        driven=None,
        sets_config=sets_config,
    )
    if versions.current() >= 201650:
        ctt = node.add_controller_tag(global_ctl, ctt)
        _connect_tag_to_rig(rig, ctt)

    # create local ctl
    local_ctl = _create_control(
        "local",
        t,
        radio,
        parent=global_ctl,
        icon=gl_shape,
        side="C",
        indx=0,
        color=17,
        driven=selection,
        sets_config=sets_config,
    )
    if versions.current() >= 201650:
        ctt = node.add_controller_tag(local_ctl, ctt)
        _connect_tag_to_rig(rig, ctt)

    return local_ctl


@utils.one_undo
# @utils.timeFunc
def _create_custom_pivot(
    name, side, icon, yZero, selection=None, parent=None, sets_config=None
):
    """Create a custom pivot control

    Args:
        name (str): Custompivot control name
        side (str): Side. can be C, L or R
        icon (str): Control shape
        yZero (bool): If True, the control will be placed in the lowest
            position of the bbox
        selection (list of dagNode, optional): Elements affected by the
            custom pivot
        parent (dagNode, optional): Parent of the custom pivot. Should be
            another ctl
        sets_config (str, optional): Sets to add the controls

    Returns:
        TYPE: Description
    """
    # should have an options in UI and store as attr for rebuild
    #   -side
    #   -Control Shape
    #   -Place in base or place in BBOX center

    if not selection:
        if pm.selected():
            selection = pm.selected()
        else:
            pm.displayWarning("Selection is needed to create the root")
            return

    if not parent:
        if selection and _is_valid_ctl(selection[-1]):
            parent = selection[-1]
            selection = selection[:-1]

        else:
            pm.displayWarning(
                "The latest selected element should be a CTL. "
                "PARENT is needed!"
            )
            return

    # handle the 3rd stat for yZero
    # this state will trigger to put it in world center
    wolrd_center = False
    if yZero > 1:
        yZero = True
        wolrd_center = True

    volCenter, radio, bb = _get_branch_bbox_data(selection, yZero)
    if volCenter:
        if wolrd_center:
            t = datatypes.Matrix()
        else:
            t = transform.getTransformFromPos(volCenter)

        ctl = _create_control(
            name,
            t,
            radio,
            parent,
            icon,
            side,
            indx=0,
            color=14,
            driven=selection,
            sets_config=sets_config,
        )

        # add ctl tag
        if versions.current() >= 201650:
            parentTag = pm.PyNode(pm.controller(parent, q=True)[0])
            ctt = node.add_controller_tag(ctl, parentTag)
            _connect_tag_to_rig(ctl.getParent(-1), ctt)

        return ctl


# Getters ===========================================


def _get_simple_rig_root():
    """get the root from the scene.

    If there is more than one It will return none and print warning

    Returns:
        dagNode: Rig root
    """

    rig_models = [
        item for item in pm.ls(transforms=True) if _is_simple_rig_root(item)
    ]
    if rig_models:
        return rig_models[0]


def connect_selectable(rig, selection):
    """Configure selectable geo

    Args:
        rig (dagNode): rig root with geo Unselectable attr
        selection (list): List of object to connect
    """
    # configure selectable geo
    for e in selection:
        pm.connectAttr(
            rig.geoUnselectable, e.attr("overrideEnabled"), force=True
        )
        e.attr("overrideDisplayType").set(2)

# @utils.timeFunc
def _get_children(dagNode):
    """Get all children node

    Args:
        dagNode (PyNode): dagNode to get the childrens

    Returns:
        list of dagNode: children dagNodes
    """

    children = dagNode.listRelatives(allDescendents=True, type="transform")
    return children

# @utils.timeFunc
def _get_bbox_data(obj=None, yZero=True, *args):
    """Calculate the bounding box data

    Args:
        obj (None, optional): The object to calculate the bounding box
        yZero (bool, optional): If true, sets the hight to the lowest point
        *args: Maya dummy

    Returns:
        mutiy: volumen center vector position, radio and bounding box (bbox)

    """
    volCenter = False

    if not obj:
        obj = pm.selected()[0]
    shapes = pm.listRelatives(obj, ad=True, s=True)
    shapes = [shp for shp in shapes if shp.type() == "mesh"]
    if shapes:
        bb = pm.polyEvaluate(shapes, b=True)
        volCenter = [(axis[0] + axis[1]) / 2 for axis in bb]
        if yZero:
            volCenter[1] = bb[1][0]
        radio = max([bb[0][1] - bb[0][0], bb[2][1] - bb[2][0]]) / 1.7

        return volCenter, radio, bb
    return volCenter, None, None

# @utils.timeFunc
def _get_branch_bbox_data(selection=None, yZero=True, *args):
    """Get the bounding box from a hierachy branch

    Args:
        selection (None, optional): Description
        yZero (bool, optional): Description
        *args: Description

    Returns:
        multi: Absolute center, absoulte radio and absolute bbox
    """
    absBB = None
    absCenter = None
    absRadio = 0.5
    bbox_elements = []

    if not isinstance(selection, list):
        selection = [selection]

    for e in selection:
        bbox_elements.append(e)
        for c in _get_children(e):
            if c.getShapes():
                bbox_elements.append(c)

    for e in bbox_elements:
        if not _is_valid_ctl(e):
            bbCenter, bbRadio, bb = _get_bbox_data(e)
            if bbCenter:
                if not absBB:
                    absBB = bb
                else:
                    absBB = [
                        [
                            min(bb[0][0], absBB[0][0]),
                            max(bb[0][1], absBB[0][1]),
                        ],
                        [
                            min(bb[1][0], absBB[1][0]),
                            max(bb[1][1], absBB[1][1]),
                        ],
                        [
                            min(bb[2][0], absBB[2][0]),
                            max(bb[2][1], absBB[2][1]),
                        ],
                    ]

                absCenter = [(axis[0] + axis[1]) / 2 for axis in absBB]
                absRadio = (
                    max([absBB[0][1] - absBB[0][0], absBB[2][1] - absBB[2][0]])
                    / 1.7
                )

                # set the cencter in the floor
                if yZero:
                    absCenter[1] = absBB[1][0]

    return absCenter, absRadio, absBB


# Build and IO ===========================================


def _collect_configuration_from_rig():
    """Collects the configuration from the rig and create a dictionary with it

    Returns:
        dict: Configuration dictionary
    """

    rig_conf_dict = {}
    ctl_settings = {}
    # get root and name
    rig_root = _get_simple_rig_root()

    # get controls list in hierarchycal order
    descendents = reversed(
        rig_root.listRelatives(allDescendents=True, type="transform")
    )
    ctl_list = [d for d in descendents if d.hasAttr("is_simple_rig_ctl")]
    ctl_names_list = []
    # get setting for each ctl
    for c in ctl_list:

        # settings
        if not c.edit_mode.get() and _is_in_npo(c):
            ctl_name = c.name()
            ctl_names_list.append(ctl_name)

            conf_icon = c.conf_icon.get()
            # back compatible:
            if c.hasAttr("conf_sets"):
                conf_sets = c.conf_sets.get()
            else:
                conf_sets = ""
            conf_radio = c.conf_radio.get()
            conf_color = c.conf_color.get()
            ctl_color = curve.get_color(c)
            if len(ctl_name.split("_")) == 2:
                ctl_side = None
                ctl_index = 0
            else:
                ctl_side = ctl_name.split("_")[-2][0]
                ctl_index = ctl_name.split("_")[-2][1:]
            ctl_short_name = ctl_name.split("_")[0]
            ctl_parent = c.getParent(2).name()
            m = c.getMatrix(worldSpace=True)
            ctl_transform = m.get()

            # driven list
            driven_list = [n.name() for n in _get_from_driven_attr(c)]

        else:
            pm.displayWarning(
                "Configuration can not be collected for Ctl in "
                "edit pivot mode or not reset SRT "
                "Finish edit pivot for or reset "
                "SRT: {}".format(c)
            )
            return None
        shps = curve.collect_curve_data(c)
        conf_ctl_dict = {
            "conf_icon": conf_icon,
            "conf_radio": conf_radio,
            "conf_color": conf_color,
            "ctl_color": ctl_color,
            "ctl_side": ctl_side,
            "ctl_shapes": shps,
            "ctl_index": ctl_index,
            "ctl_parent": ctl_parent,
            "ctl_transform": ctl_transform,
            "ctl_short_name": ctl_short_name,
            "driven_list": driven_list,
            "sets_list": conf_sets,
        }

        ctl_settings[ctl_name] = conf_ctl_dict

    rig_conf_dict["ctl_list"] = ctl_names_list
    rig_conf_dict["ctl_settings"] = ctl_settings
    rig_conf_dict["root_name"] = rig_root.name()

    return rig_conf_dict


# @utils.one_undo
# @utils.timeFunc
def _build_rig_from_model(
    dagNode,
    rigName=RIG_ROOT,
    suffix="geoRoot",
    sets_config=None,
    ctl_wcm=False,
    fix_radio=False,
    radio_val=100,
    gl_shape="square",
    world_ctl=True,
    w_shape="circle",
):
    """Build a rig from a model structure.

     using suffix keyword from a given model build a rig.

    Args:
        dagNode (dagNode): model root node
        rigName (str, optional): Name of the rig
        suffix (str, optional): suffix to check inside the model structure
            in order identify the custom pivots
        sets_config (str, optional): list of sets in string separated by ","
        ctl_wcm (bool, optional): If True, the world_ctl will ve placed in the
            scene world center
        fix_radio (bool, optional): If True, will use a fix radio value,
            instead of the bbox radio
        radio_val (int, optional): Fix value for Radio
        gl_shape (str, optional): Global and local control shape
        world_ctl (bool, optional): if True, will create world_ctl
        w_shape (str, optional): World control shape
        sets_config (None, optional): Groups to include the ctl
    """

    suf = "_{}".format(string.removeInvalidCharacter(suffix))
    pm.displayInfo("Searching elements using suffix: {}".format(suf))

    parent_dict = {}
    local_ctl = _create_simple_rig_root(
        rigName,
        sets_config=sets_config,
        ctl_wcm=ctl_wcm,
        fix_radio=fix_radio,
        radio_val=radio_val,
        gl_shape=gl_shape,
        world_ctl=world_ctl,
        w_shape=w_shape,
    )
    if local_ctl:
        descendents = dagNode.listRelatives(allDescendents=True, type="transform")

        suff_list = suffix.split(",")
        for d in descendents:
            if list(filter(d.name().endswith, suff_list)) != []:
                name = d.name().replace(suf, "")
                if d.getParent().name() in parent_dict:
                    parent = parent_dict[d.getParent().name()]
                else:
                    parent = local_ctl
                print(d)
                ctl = _create_custom_pivot(
                    name,
                    "C",
                    "circle",
                    True,
                    selection=d,
                    parent=parent,
                    sets_config=sets_config,
                )
                parent_dict[d.name()] = ctl


def _build_rig_from_configuration(configDict):
    """Buiold rig from configuration

    Args:
        configDict (dict): The configuration dictionary
    """
    rig = _create_base_structure(configDict["root_name"])
    for c in configDict["ctl_list"]:
        ctl_conf = configDict["ctl_settings"][c]
        driven = []
        for drv in ctl_conf["driven_list"]:
            obj = pm.ls(drv)
            if obj:
                driven.append(obj[0])
            else:
                pm.displayWarning(
                    "Driven object {}: " "Can't be found.".format(drv)
                )
        t = datatypes.Matrix(ctl_conf["ctl_transform"])
        _create_control(
            ctl_conf["ctl_short_name"],
            t,
            ctl_conf["conf_radio"],
            ctl_conf["ctl_parent"],
            ctl_conf["conf_icon"],
            ctl_conf["ctl_side"],
            indx=ctl_conf["ctl_index"],
            color=ctl_conf["ctl_color"],
            driven=driven,
            sets_config=ctl_conf["sets_list"],
        )
        curve.update_curve_from_data(ctl_conf["ctl_shapes"])
        connect_selectable(rig, driven)


def export_configuration(filePath=None):
    """Export configuration to json file

    Args:
        filePath (str, optional): Path to save the file

    """

    rig_conf_dict = _collect_configuration_from_rig()
    data_string = json.dumps(rig_conf_dict, indent=4, sort_keys=True)
    if not filePath:
        startDir = pm.workspace(q=True, rootDirectory=True)
        filePath = pm.fileDialog2(
            dialogStyle=2,
            fileMode=0,
            startingDirectory=startDir,
            fileFilter="Simple Rig Configuration .src (*%s)" % ".src",
        )
    if not filePath:
        return
    if not isinstance(filePath, string_types):
        filePath = filePath[0]
    f = open(filePath, "w")
    f.write(data_string)
    f.close()


def import_configuration(filePath=None):
    """Import configuration from filePath

    Args:
        filePath (str, optional): File path to the configuration json file
    """

    if not filePath:
        startDir = pm.workspace(q=True, rootDirectory=True)
        filePath = pm.fileDialog2(
            dialogStyle=2,
            fileMode=1,
            startingDirectory=startDir,
            fileFilter="Simple Rig Configuration .src (*%s)" % ".src",
        )
    if not filePath:
        return
    if not isinstance(filePath, string_types):
        filePath = filePath[0]
    configDict = json.load(open(filePath))
    _build_rig_from_configuration(configDict)


# Convert to SHIFTER  ===========================================


def _shifter_init_guide(name, worldCtl=False):
    """Initialize shifter guide

    Args:
        name (str): Name for the rig
        worldCtl (bool, optional): if True, will set the guide to use world_ctl

    Returns:
        TYPE: Description
    """
    guide = shifter.guide.Rig()
    guide.initialHierarchy()
    model = guide.model
    # set there attribute for guide root
    model.rig_name.set(name)
    model.worldCtl.set(worldCtl)

    return guide


def _shifter_control_component(
    name, side, indx, t, guide, parent=None, grps=""
):
    """creates shifter control_01 component and sets the correct settings

    Args:
        name (str): Name of the component
        side (str): side
        indx (int): index
        t (matrix): Transform Matrix
        guide (guide): Shifter guide object
        parent (dagNode, optional): Parent
        grps (str, optional): groups

    Returns:
        TYPE: Description
    """

    comp_guide = guide.getComponentGuide("control_01")
    if parent is None:
        parent = guide.model
    if not isinstance(parent, str):
        parent = pm.PyNode(parent)

    comp_guide.draw(parent)
    comp_guide.rename(comp_guide.root, name, side, indx)
    root = comp_guide.root
    # set the attributes for component
    root.setMatrix(t, worldSpace=True)
    root.neutralRotation.set(False)
    root.joint.set(True)
    root.ctlGrp.set(grps)

    return root


def convert_to_shifter_guide():
    """Convert the configuration to a shifter guide.

    Returns:
        multi: guide and configuration dictionary
    """

    # get configuration dict
    configDict = _collect_configuration_from_rig()

    if configDict:

        # Create the guide
        root_name = configDict["root_name"]
        if "world_ctl" in configDict["ctl_list"]:
            worldCtl = True
            # we asume the world_ctl is always the first in the list
            configDict["ctl_list"] = configDict["ctl_list"][1:]
        else:
            worldCtl = False
        guide = _shifter_init_guide(root_name, worldCtl)

        # dic to store the parent relation from the original rig to the guide
        parentRelation = {}
        if worldCtl:
            parentRelation["world_ctl"] = guide.model
        else:
            first_ctl = configDict["ctl_list"][0]
            p = configDict["ctl_settings"][first_ctl]["ctl_parent"]
            parentRelation[p] = guide.model
        # create components
        for c in configDict["ctl_list"]:
            ctl_conf = configDict["ctl_settings"][c]
            t = datatypes.Matrix(ctl_conf["ctl_transform"])
            # we need to parse the grps list in order to extract the first grp
            # without sub groups. Shifter doesn't support this feature yet
            grps = ctl_conf["sets_list"]
            grps = [g.split(".")[-1] for g in grps.split(",")][0]
            root = _shifter_control_component(
                ctl_conf["ctl_short_name"],
                ctl_conf["ctl_side"],
                int(ctl_conf["ctl_index"]),
                t,
                guide,
                parent=parentRelation[ctl_conf["ctl_parent"]],
                grps=grps,
            )
            parentRelation[c] = root

        return guide, configDict
    else:
        return None, None


# @utils.one_undo
def convert_to_shifter_rig():
    """Convert simple rig to Shifter rig

    It will create the guide and build the rig from configuration
    skinning automatic base on driven attr
    """

    simple_rig_root = _get_simple_rig_root()
    if simple_rig_root:
        guide, configDict = convert_to_shifter_guide()
        if guide:
            # ensure the objects are removed from the original rig
            for c in configDict["ctl_list"]:
                ctl_conf = configDict["ctl_settings"][c]
                for d in ctl_conf["driven_list"]:
                    driven = pm.ls(d)
                    if driven and driven[0].getParent(-1).hasAttr(
                        "is_simple_rig"
                    ):
                        pm.displayWarning(
                            "{}: cut for old rig hierarchy"
                            "to avoid delete it when delete "
                            "the old rig!!"
                        )
                        pm.parent(driven, w=True)

            # delete original rig
            pm.delete(simple_rig_root)

            # build guide
            pm.select(guide.model)
            rig = shifter.Rig()
            rig.buildFromSelection()
            rig.model.jnt_vis.set(0)

            attribute.addAttribute(rig.model, "geoUnselectable", "bool", True)

            # skin driven to new rig and  apply control shapes
            driven = None
            for c in configDict["ctl_list"]:
                ctl_conf = configDict["ctl_settings"][c]
                for d in ctl_conf["driven_list"]:
                    driven = pm.ls(d)
                    jnt = pm.ls(c.replace("ctl", "0_jnt"))
                    connect_selectable(rig.model, [driven[0]])
                    if driven and jnt:
                        try:
                            pm.skinCluster(
                                jnt[0],
                                driven[0],
                                tsb=True,
                                nw=2,
                                n="{}_skinCluster".format(d),
                            )
                        except RuntimeError:
                            pm.displayWarning(
                                "Automatic skinning, can't be "
                                "created for"
                                " {}. Skipped.".format(d)
                            )

                curve.update_curve_from_data(ctl_conf["ctl_shapes"])

            # ensure geo root is child of rig root
            if driven:
                pm.parent(driven[0].getParent(-1), rig.model)
        else:
            pm.displayWarning("The guide can not be extracted. Check log!")
    else:
        pm.displayWarning("No simple root to convert!")


# Edit ===========================================


def _remove_element_from_ctl(ctl, dagNode):
    """Remove element from a rig control

    Args:
        ctl (dagNode): Control to remove the  element
        dagNode (dagNode): Element to be removed

    Returns:
        TYPE: Description
    """
    # Check the ctl is reset
    if not _is_in_npo(ctl):
        pm.displayWarning(
            "{}: have SRT values. Reset, before edit " "elements".format(ctl)
        )
        return

    # get affected by pivot
    driven = _get_from_driven_attr(ctl)

    # if dagNode is not in affected by pivot disconnect
    if dagNode in driven:
        _disconnect_driven(dagNode)
        _remove_from_driven_attr(dagNode)
        _update_driven(ctl)
    else:
        pm.displayWarning(
            "{} is is not connected to the ctl {}".format(dagNode, ctl)
        )


def _add_element_to_ctl(ctl, dagNode):
    """Add element to control

    Args:
        ctl (dagNode): Control to add element
        dagNode (dagNode): Element to add to the control

    """
    # ensure the element is not yet in pivot
    driven = _get_from_driven_attr(ctl)
    # Check the ctl is reset
    if not _is_in_npo(ctl):
        pm.displayWarning(
            "{}: have SRT values. Reset, before edit " "elements".format(ctl)
        )
        return
    # if dagNode is not in affected by pivot disconnect
    if dagNode not in driven:
        # move\add the selected elements to new pivot.
        _add_to_driven_attr(ctl, dagNode)
        _update_driven(ctl)


def _delete_pivot(dagNode):
    """Remove custom pivot control

    It will move all dependent elements and children pivots to his parent
    element or move to the root if there is not parent pivot

    Args:
        dagNode (PyNode): Control to be removed

    Returns:
        TYPE: Description
    """

    if _is_valid_ctl(dagNode):
        # get children pivots
        # Check the ctl is reset
        if not _is_in_npo(dagNode):
            pm.displayWarning(
                "{}: have SRT values. Reset, before edit "
                "elements".format(dagNode)
            )
            return
        children = dagNode.listRelatives(type="transform")
        if children:
            pm.parent(children, dagNode.getParent(2))

        # clean connections
        for d in _get_from_driven_attr(dagNode):
            _disconnect_driven(d)

        # delete pivot
        pm.delete(dagNode.getParent())
        pm.select(clear=True)


def _parent_pivot(pivot, parent):
    """Reparent pivot to another pivot or root

    Should avoid to parent under world_ctl or local_C0_ctl


    Args:
        pivot (dagNode): Custom pivot control
        parent (dagNode): New parent
    """

    # check it parent is valid pivot
    if _is_valid_ctl(parent):
        if _is_valid_ctl(pivot):
            # Check the ctl is reset
            if not _is_in_npo(pivot):
                pm.displayWarning(
                    "{}: have SRT values. Reset, before edit "
                    "elements".format(pivot)
                )
            npo = pivot.getParent()
            attribute.unlockAttribute(npo)
            pm.parent(npo, parent)
            attribute.lockAttribute(npo)
            # re-connect controller tag

            pivotTag = pm.PyNode(pm.controller(pivot, q=True)[0])
            node.controller_tag_connect(pivotTag, parent)

            pm.select(clear=True)
        else:
            pm.displayWarning(
                "The selected Pivot: {} is not a "
                "valid simple rig ctl.".format(parent.name())
            )
    else:
        pm.displayWarning(
            "The selected parent: {} is not a "
            "valid simple rig ctl.".format(parent.name())
        )


@utils.one_undo
def _edit_pivot_position(ctl):
    """Edit control pivot

    set the pivot in editable mode
    check that is in neutral pose

    Args:
        ctl (dagNode): Pivot to edit


    """

    if not _is_in_npo(ctl):
        pm.displayWarning(
            "The control: {} should be in reset" " position".format(ctl.name())
        )
        return
    if not ctl.attr("edit_mode").get():
        # move child to parent
        children = ctl.listRelatives(type="transform")
        if children:
            pm.parent(children, ctl.getParent())
        # disconnect the driven elements
        driven = _get_from_driven_attr(ctl)
        ctl.attr("edit_mode").set(True)
        for d in driven:
            # first try to disconnect
            _disconnect_driven(d)
        pm.select(ctl)
    else:
        pm.displayWarning(
            "The control: {} Is already in"
            " Edit pivot Mode".format(ctl.name())
        )
        return


@utils.one_undo
def _consolidate_pivot_position(ctl):
    """Consolidate the pivot position after editing

    Args:
        ctl (dagNode): control to consolidate the new pivot position
    """
    #

    if ctl.attr("edit_mode").get():
        # unparent the  children
        # rig = pm.PyNode(RIG_ROOT)
        rig = _get_simple_rig_root()
        npo = ctl.getParent()
        attribute.unlockAttribute(npo)
        children = npo.listRelatives(type="transform")
        if children:
            for ch in children:
                attribute.unlockAttribute(ch)
            pm.parent(children, rig)
        # filter out the ctl
        children = [c for c in children if c != ctl]
        # set the npo to his position
        transform.matchWorldTransform(ctl, npo)
        pm.parent(ctl, npo)
        # reparent childrens
        if children:
            pm.parent(children, ctl)
            for ch in children:
                attribute.lockAttribute(ch)
        # re-connect/update driven elements
        _update_driven(ctl)
        ctl.attr("edit_mode").set(False)
        attribute.lockAttribute(npo)
        pm.select(ctl)
    else:
        pm.displayWarning(
            "The control: {} Is NOT in" " Edit pivot Mode".format(ctl.name())
        )


@utils.one_undo
def _delete_rig():
    """Delete the rig

    Delete the rig and clean all connections on the geometry
    """
    rig = _get_simple_rig_root()
    if rig:
        confirm = pm.confirmDialog(
            title="Confirm Delete Simple Rig",
            message="Are you sure?",
            button=["Yes", "No"],
            defaultButton="Yes",
            cancelButton="No",
            dismissString="No",
        )
        if confirm == "Yes":
            children = rig.listRelatives(allDescendents=True, type="transform")
            to_delete = []
            not_npo = []
            for c in children:
                if _is_valid_ctl(c):
                    if _is_in_npo(c):
                        to_delete.append(c)
                    else:
                        not_npo.append(c.name())
            if not_npo:
                pm.displayWarning(
                    "Please set all the controls to reset "
                    "position before delete rig. The following"
                    " controls are not "
                    "reset:{}".format(str(not_npo))
                )
                return
            for c in to_delete:
                _delete_pivot(c)
            pm.delete(rig)
    else:
        pm.displayWarning("No rig found to delete!")


# utils ===========================================


def _connect_tag_to_rig(rig, ctt):
    """Connect control tag"""
    ni = attribute.get_next_available_index(rig.rigCtlTags)
    pm.connectAttr(ctt.message, rig.attr("rigCtlTags[{}]".format(str(ni))))


def _validate_name(name):
    """Check and correct bad name formating

    Args:
        name (str): Name

    Returns:
        str: Corrected Name
    """

    return string.removeInvalidCharacter(name)


def _is_valid_ctl(dagNode):
    """Check if the dagNode is a simple rig ctl

    Args:
        dagNode (PyNode): Control to check

    Returns:
        bool: True is has the expected tag attr
    """
    return dagNode.hasAttr(CTL_TAG_ATTR)


def _is_simple_rig_root(dagNode):
    """Check if the dagNode is a simple rig ctl

    Args:
        dagNode (PyNode): Control to check

    Returns:
        bool: Return true if is simple rig
    """

    return dagNode.hasAttr("is_simple_rig")


def _is_in_npo(dagNode):
    """check if the SRT is reset

    SRT = Scale, Rotation, Translation

    Args:
        dagNode (PyNode): control to check

    Returns:
        bool: neutral pose status
    """
    #
    trAxis = ["tx", "ty", "tz", "rx", "ry", "rz"]
    sAxis = ["sx", "sy", "sz"]
    npo_status = True
    for axis in trAxis:
        val = dagNode.attr(axis).get()
        if val != 0.0:
            npo_status = False
            pm.displayWarning(
                "{}.{} is not neutral! Value is {}, "
                "but should be {}".format(
                    dagNode.name(), axis, str(val), "0.0"
                )
            )
    for axis in sAxis:
        val = dagNode.attr(axis).get()
        if val != 1.0:
            npo_status = False
            pm.displayWarning(
                "{}.{} is not neutral! Value is {}, "
                "but should be {}".format(
                    dagNode.name(), axis, str(val), "1.0"
                )
            )
    return npo_status


# groups ==============================================


def _get_sets_grp(grpName="controllers_grp"):
    """Get set group

    Args:
        grpName (str, optional): group name

    Returns:
        PyNode: Set
    """
    rig = _get_simple_rig_root()
    sets = rig.listConnections(type="objectSet")

    controllersGrp = None
    for oSet in sets:
        if grpName in oSet.name():
            controllersGrp = oSet

    return controllersGrp


def _extra_sets(sets_config):
    """Configure the extra sets from string

    exp: sets_config = "animSets.basic.test,animSets.facial"
    Args:
        sets_config (str): extra sets configuration

    Returns:
        list: extra sets list
    """
    sets_grp = _get_sets_grp("sets_grp")
    sets_list = sets_config.split(",")
    last_sets_list = []
    for s in sets_list:
        set_fullname = ".".join([sets_grp.name(), s])
        parent_set = None
        # ss is the subset
        for ss in set_fullname.split("."):
            if pm.ls(ss):
                parent_set = pm.ls(ss)[0]
            else:
                child_set = pm.sets(None, n=ss)
                if parent_set:
                    parent_set.add(child_set)
                parent_set = child_set
        last_sets_list.append(parent_set)

    return last_sets_list


# Connect ===========================================


def _connect_driven(driver, driven):
    """Connect the driven element with multiply matrix

    Before connect check if the driven is valid.
    I.E. only elements not under geoRoot.

    Args:
        driver (PyNode): Driver control
        driven (PyNode): Driven control

    """

    if _is_valid_ctl(driven):
        pm.displayWarning(
            "{} can't not be driven or connected to a ctl, "
            "because is a simple rig control".format(driven)
        )
        return

        # Check the ctl is reset
        if not _is_in_npo(driver):
            pm.displayWarning(
                "{}: have SRT values. Reset, before connect "
                "elements".format(driver)
            )
    # connect message of the matrix mul nodes to the driven.
    # So later is easy to delete
    mOperatorNodes = "mOperatorNodes"
    if not driven.hasAttr(mOperatorNodes):
        driven.addAttr(mOperatorNodes, attributeType="message", multi=True)
        # print driven.attr(mOperatorNodes)
    mOp_attr = driven.attr(mOperatorNodes)
    m = driven.worldMatrix.get()

    im = driver.worldMatrix.get().inverse()
    mul_node0 = applyop.gear_mulmatrix_op(im, driver.worldMatrix)
    mul_node1 = applyop.gear_mulmatrix_op(m, mul_node0.output)
    mul_node2 = applyop.gear_mulmatrix_op(
        mul_node1.output, driven.parentInverseMatrix
    )
    dm_node = node.createDecomposeMatrixNode(mul_node2.output)

    pm.connectAttr(dm_node.outputTranslate, driven.t)
    pm.connectAttr(dm_node.outputRotate, driven.r)
    pm.connectAttr(dm_node.outputScale, driven.s)
    pm.connectAttr(dm_node.outputShear, driven.shear)

    pm.connectAttr(
        mul_node0.message, mOp_attr.attr("{}[0]".format(mOperatorNodes))
    )
    pm.connectAttr(
        mul_node1.message, mOp_attr.attr("{}[1]".format(mOperatorNodes))
    )
    pm.connectAttr(
        mul_node2.message, mOp_attr.attr("{}[2]".format(mOperatorNodes))
    )
    pm.connectAttr(
        dm_node.message, mOp_attr.attr("{}[3]".format(mOperatorNodes))
    )


def _disconnect_driven(driven):
    """Disconnect driven control

    delete the matrix mult nodes

    Args:
        driven (PyNode): Driven control to disconnect
    """

    mOperatorNodes = "mOperatorNodes"
    if driven.hasAttr(mOperatorNodes):
        pm.delete(driven.attr(mOperatorNodes).inputs())


# @utils.one_undo
def _update_driven(driver):
    """Update the driven connections using the driver drivenElements attr

    Args:
        driver (PyNode): Driver control
    """

    driven = _get_from_driven_attr(driver)
    for d in driven:
        # first try to disconnect
        _disconnect_driven(d)
        # Connect
        _connect_driven(driver, d)


####################################
# Simple Rig dialog
####################################


class simpleRigUI(QtWidgets.QMainWindow, srUI.Ui_MainWindow):

    """UI dialog"""

    def __init__(self, parent=None):
        super(simpleRigUI, self).__init__(parent)
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installEventFilter(self)

    def keyPressEvent(self, event):
        if not event.key() == QtCore.Qt.Key_Escape:
            super(simpleRigUI, self).keyPressEvent(event)


class simpleRigTool(MayaQWidgetDockableMixin, QtWidgets.QDialog):

    valueChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        self.toolName = "SimpleRigTool"
        super(simpleRigTool, self).__init__(parent)
        self.srUIInst = simpleRigUI()

        self.setup_simpleRigWindow()
        self.create_layout()
        self.create_connections()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installEventFilter(self)

    def keyPressEvent(self, event):
        if not event.key() == QtCore.Qt.Key_Escape:
            super(simpleRigTool, self).keyPressEvent(event)

    def setup_simpleRigWindow(self):

        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Simple Rig")
        self.resize(280, 260)

    def create_layout(self):

        self.sr_layout = QtWidgets.QVBoxLayout()
        self.sr_layout.addWidget(self.srUIInst)

        self.setLayout(self.sr_layout)

    def create_connections(self):
        self.srUIInst.createRoot_pushButton.clicked.connect(self.create_root)
        self.srUIInst.createCtl_pushButton.clicked.connect(self.create_ctl)
        self.srUIInst.selectAffected_pushButton.clicked.connect(
            self.select_affected
        )
        self.srUIInst.reParentPivot_pushButton.clicked.connect(
            self.parent_pivot
        )
        self.srUIInst.add_pushButton.clicked.connect(self.add_to_ctl)
        self.srUIInst.remove_pushButton.clicked.connect(self.remove_from_ctl)
        self.srUIInst.editPivot_pushButton.clicked.connect(self.edit_pivot)
        self.srUIInst.setPivot_pushButton.clicked.connect(self.set_pivot)
        self.srUIInst.autoRig_pushButton.clicked.connect(self.auto_rig)

        # Menus
        self.srUIInst.deletePivot_action.triggered.connect(self.delete_pivot)
        self.srUIInst.deleteRig_action.triggered.connect(self.delete_rig)
        self.srUIInst.autoBuild_action.triggered.connect(self.auto_rig)
        self.srUIInst.export_action.triggered.connect(self.export_config)
        self.srUIInst.import_action.triggered.connect(self.import_config)
        # Shifter
        self.srUIInst.convertToShifterRig_action.triggered.connect(
            self.shifter_rig
        )
        self.srUIInst.createShifterGuide_action.triggered.connect(
            self.shifter_guide
        )

        # Misc
        self.srUIInst.rootName_lineEdit.textChanged.connect(
            self.rootName_text_changed
        )
        self.srUIInst.createCtl_lineEdit.textChanged.connect(
            self.ctlName_text_changed
        )

    # ==============================================
    # Slots ========================================
    # ==============================================

    def shifter_rig(self):
        convert_to_shifter_rig()

    def shifter_guide(self):
        convert_to_shifter_guide()

    def rootName_text_changed(self):
        name = _validate_name(self.srUIInst.rootName_lineEdit.text())
        self.srUIInst.rootName_lineEdit.setText(name)

    def ctlName_text_changed(self):
        name = _validate_name(self.srUIInst.createCtl_lineEdit.text())
        self.srUIInst.createCtl_lineEdit.setText(name)

    def create_root(self):
        name = self.srUIInst.rootName_lineEdit.text()
        sets_config = self.srUIInst.extraSets_lineEdit.text()
        ctl_wcm = self.srUIInst.worldCenter_checkBox.isChecked()
        fix_radio = self.srUIInst.fixSize_checkBox.isChecked()
        radio_val = self.srUIInst.fixSize_doubleSpinBox.value()
        iconIdx = self.srUIInst.mainCtlShape_comboBox.currentIndex()
        icon = ["square", "circle"][iconIdx]
        w_ctl = self.srUIInst.worldCtl_checkBox.isChecked()
        iconIdx = self.srUIInst.worldCtlShape_comboBox.currentIndex()
        w_icon = ["circle", "sphere"][iconIdx]
        _create_simple_rig_root(
            name,
            sets_config=sets_config,
            ctl_wcm=ctl_wcm,
            fix_radio=fix_radio,
            radio_val=radio_val,
            gl_shape=icon,
            world_ctl=w_ctl,
            w_shape=w_icon,
        )

    def create_ctl(self):
        name = self.srUIInst.createCtl_lineEdit.text()
        if name:
            sideIdx = self.srUIInst.side_comboBox.currentIndex()
            side = ["C", "L", "R"][sideIdx]
            iconIdx = self.srUIInst.shape_comboBox.currentIndex()
            icon = ["circle", "cube"][iconIdx]
            position = self.srUIInst.position_comboBox.currentIndex()
            sets_config = self.srUIInst.extraSets_lineEdit.text()
            _create_custom_pivot(
                name, side, icon, yZero=position, sets_config=sets_config
            )
        else:
            pm.displayWarning("Name is not valid")

    # @utils.one_undo
    def select_affected(self):
        oSel = pm.selected()
        if oSel:
            ctl = oSel[0]
            pm.select(_get_from_driven_attr(ctl))

    # @utils.one_undo
    def parent_pivot(self):
        oSel = pm.selected()
        if oSel and len(oSel) >= 2:
            for c in oSel[:-1]:
                _parent_pivot(c, oSel[-1])

    # @utils.one_undo
    def add_to_ctl(self):
        oSel = pm.selected()
        if oSel and len(oSel) >= 2:
            for e in oSel[:-1]:
                _add_element_to_ctl(oSel[-1], e)

    # @utils.one_undo
    def remove_from_ctl(self):
        oSel = pm.selected()
        if oSel and len(oSel) >= 2:
            for e in oSel[:-1]:
                _remove_element_from_ctl(oSel[-1], e)

    # @utils.one_undo
    def delete_pivot(self):
        for d in pm.selected():
            _delete_pivot(d)

    # @utils.one_undo
    def edit_pivot(self):
        oSel = pm.selected()
        if oSel and len(oSel) == 1:
            _edit_pivot_position(oSel[0])
        else:
            pm.displayWarning("Please select one ctl")

    # @utils.one_undo
    def set_pivot(self):
        oSel = pm.selected()
        if oSel and len(oSel) == 1:
            _consolidate_pivot_position(oSel[0])
        else:
            pm.displayWarning("Please select one ctl")

    # @utils.one_undo
    def delete_rig(self):
        _delete_rig()

    # @utils.one_undo
    @utils.timeFunc
    def auto_rig(self):
        oSel = pm.selected()
        if oSel and len(oSel) == 1:
            suffix = self.srUIInst.autoBuild_lineEdit.text()
            name = self.srUIInst.rootName_lineEdit.text()
            sets_config = self.srUIInst.extraSets_lineEdit.text()
            ctl_wcm = self.srUIInst.worldCenter_checkBox.isChecked()
            fix_radio = self.srUIInst.fixSize_checkBox.isChecked()
            radio_val = self.srUIInst.fixSize_doubleSpinBox.value()
            iconIdx = self.srUIInst.mainCtlShape_comboBox.currentIndex()
            icon = ["square", "circle"][iconIdx]
            w_ctl = self.srUIInst.worldCtl_checkBox.isChecked()
            iconIdx = self.srUIInst.worldCtlShape_comboBox.currentIndex()
            w_icon = ["circle", "sphere"][iconIdx]
            _build_rig_from_model(
                oSel[0],
                name,
                suffix,
                sets_config,
                ctl_wcm=ctl_wcm,
                fix_radio=fix_radio,
                radio_val=radio_val,
                gl_shape=icon,
                world_ctl=w_ctl,
                w_shape=w_icon,
            )
        else:
            pm.displayWarning("Please select root of the model")

    def export_config(self):
        export_configuration()

    def import_config(self):
        import_configuration()


def openSimpleRigUI(*args):
    pyqt.showDialog(simpleRigTool, dockable=True)


####################################


if __name__ == "__main__":

    openSimpleRigUI()
