#!/usr/bin/env python
"""rbf node to normalize the calls across any number of supported
rbf node types. First supported "weightDriver"/ingo clemens/Brave Rabit

Attributes:
    CTL_SUFFIX (str): name of the control suffixe
    DRIVEN_SUFFIX (str): suffix to be applied to driven group
    DRIVER_CTL_ATTR_NAME (str): name of the attribute to store driver control
    DRIVER_POSEINPUT_ATTR (str): name of attr to store control driver(holder)
    DRIVER_POSES_INFO_ATTR (str): name of attr to store control
    GENERIC_SUFFIX (str): generic suffix if one not provided by support module
    RBF_SCALE_ATTR (str): name of attr applied to driven control
    RBF_SETUP_ATTR (str): name of attr to store setup name for group of rbf
    ROTATE_ATTRS (list): convenience list of transform attrs
    SCALE_ATTRS (list): convenience list of transform attrs
    SUPPORTED_RBF_NODES (tuple): currently supported rbf node types
    TRANSFORM_SUFFIX (str): suffix of transform nodes for rbf nodes
    TRANSLATE_ATTRS (list): convenience list of transform attrs

Notes - refactor as more supported rbf node types are added

__author__ = "Rafael Villar"
__email__ = "rav@ravrigs.com"

"""
# python
import ast
import math

# core
import maya.cmds as mc
import mgear.pymaya as pm
import maya.api.OpenMaya as om

# mgear
from mgear.core import transform, attribute
from mgear.core import anim_utils
from .six import PY2

# =============================================================================
# constants
# =============================================================================

DRIVEN_SUFFIX = "_driven"
DRIVEN_PAR_SUFFIX = "_drivenPar"
RBF_LOCATOR_SUFFIX = "_rbfLoc"
CTL_SUFFIX = "_ctl"
TRANSFORM_SUFFIX = "_trfm"

RBF_SETUP_ATTR = "rbf_setup_name"

TRANSLATE_ATTRS = ["translateX", "translateY", "translateZ"]

ROTATE_ATTRS = ["rotateX", "rotateY", "rotateZ"]

SCALE_ATTRS = ["scaleX", "scaleY", "scaleZ"]

# available_SHAPES_WD = mc.pluginInfo("weightDriver", q=True, loaded=True)
# if available_SHAPES_WD:

#     SUPPORTED_RBF_NODES = ("mGearWeightDriver", "weightDriver")
# else:
SUPPORTED_RBF_NODES = ("mGearWeightDriver",)

GENERIC_SUFFIX = "_RBF"

DRIVER_CTL_ATTR_NAME = "driverControlName"
DRIVER_POSES_INFO_ATTR = "driverPosesInfo"
# DRIVER_POSEINPUT_ATTR = "poseInput"

RBF_SCALE_ATTR = "RBF_Multiplier"


# =============================================================================
# general functions
# =============================================================================
def getMultipleAttrs(node, attributes):
    """get multiple attrs and their values in a list, in order

    Args:
        node (str): name of node
        attributes (list): of attrs to query

    Returns:
        list: of values
    """
    valuesToReturn = []
    for attr in attributes:
        valuesToReturn.append(mc.getAttr("{}.{}".format(node, attr)))
    return valuesToReturn


def copyInverseMirrorAttrs(srcNode, dstNode):
    """within mGear the concept of inverseAttrs, so that transforms can be
    accurately mirrored, exists and this copys the relavent attrs from src
    to dest

    Args:
        srcNode (str, pynode): source node
        dstNode (str, pynode): destination to copy attrs to
    """
    srcNode = pm.PyNode(srcNode)
    dstNode = pm.PyNode(dstNode)
    attrsToInv = anim_utils.listAttrForMirror(srcNode)
    for attr in attrsToInv:
        inAttr = anim_utils.getInvertCheckButtonAttrName(attr)
        try:
            val = mc.getAttr("{}.{}".format(srcNode, inAttr))
            mc.setAttr("{}.{}".format(dstNode, inAttr), val)
        except ValueError:
            continue


def get_driven_group_name(node):
    """get the name of the driven group that would be created for the
    provided node

    Args:
        node (str): name of node

    Returns:
        str: name of the driven group node
    """
    node = pm.PyNode(node)
    if node.endswith(CTL_SUFFIX):
        drivenName = node.replace(CTL_SUFFIX, DRIVEN_SUFFIX)
    else:
        drivenName = "{}{}".format(node, DRIVEN_SUFFIX)
    return drivenName


def addDrivenGroup(node, drivenName=None):
    """add driven group, pad, above the provided node for direct connection

    Args:
        node (str): name of node to add group above

    Returns:
        str: of node created
    """
    node = pm.PyNode(node)
    parentOfTarget = pm.listRelatives(node, p=True) or None
    if parentOfTarget:
        parentOfTarget = parentOfTarget[0]

    drivenName = drivenName or get_driven_group_name(node)

    if parentOfTarget is None:
        parentOfTarget = pm.group(
            name=drivenName.replace(DRIVEN_SUFFIX, DRIVEN_PAR_SUFFIX),
            w=True,
            em=True,
        )

    else:
        parentOfTarget = pm.group(
            name=drivenName.replace(DRIVEN_SUFFIX, DRIVEN_PAR_SUFFIX),
            p=parentOfTarget,
            em=True,
        )
    parentOfTarget.setMatrix(node.getMatrix(worldSpace=True), worldSpace=True)
    drivenName = pm.group(name=drivenName, p=parentOfTarget, em=True)

    attribute.add_mirror_config_channels(pm.PyNode(drivenName))

    if node.endswith(CTL_SUFFIX):
        copyInverseMirrorAttrs(node, drivenName)
    pm.parent(node, drivenName)
    return drivenName.name()


def removeDrivenGroup(node):
    """remove driven group above desired node

    Args:
        node (str): name of node to check
    """
    drivePar = parentOfTarget = mc.listRelatives(node, p=True) or None
    if parentOfTarget and parentOfTarget[0].endswith(DRIVEN_PAR_SUFFIX):
        parentOfTarget = mc.listRelatives(parentOfTarget, p=True) or None
    childrenNode = mc.listRelatives(node, type="transform") or []

    for child in childrenNode:
        if parentOfTarget is None:
            mc.parent(child, w=True)
        else:
            mc.parent(child, parentOfTarget[0])
    if node.endswith(DRIVEN_SUFFIX):
        mc.delete(node)
        if drivePar and drivePar[0].endswith(DRIVEN_PAR_SUFFIX):
            mc.delete(drivePar)


def compensateLocator(node):
    """Create a locator that parents under desired node, to manipulated
    directly connected nodes.
    Functionality that is disable, but for future use.

    Args:
        node (str): desired node

    Returns:
        str: name of the created locator
    """
    mc.select(cl=True)
    cLoc = mc.spaceLocator(n="{}{}".format(node, RBF_LOCATOR_SUFFIX))
    mc.parent(cLoc, node, r=True)
    return cLoc


def removeCompensateLocator(node):
    """remove the locator under the desired node if exists

    Args:
        node (str): name of the ndoe to look under.
    """
    mc.select(cl=True)
    cmpLoc = "{}{}".format(node, RBF_LOCATOR_SUFFIX)
    if mc.objExists(cmpLoc):
        cmpLoc_par = mc.listRelatives(cmpLoc, p=True)
        if cmpLoc_par and cmpLoc_par[0] == node:
            mc.delete(cmpLoc)


def decompMatrix(node, matrix):
    """
    Decomposes an MMatrix using the new maya.api.OpenMaya API.
    Returns a list of translation, rotation, and scale in world space.

    Args:
        node (str): Name of the node to query the rotation order from.
        matrix (om.MMatrix): MMatrix to decompose.

    Returns:
        list: A list containing the translation (x, y, z), rotation (x, y, z
        in degrees), and scale (x, y, z) in world space.
    """
    # Retrieve the rotation order of the node
    rot_order = mc.getAttr("{}.rotateOrder".format(node))

    # Convert the MMatrix to an MTransformationMatrix
    m_transform_mtx = om.MTransformationMatrix(matrix)

    # Get translation values in world space
    translation = m_transform_mtx.translation(om.MSpace.kWorld)

    # Get Euler rotation values in radians
    euler_rot = m_transform_mtx.rotation()

    # Reorder rotation to match the node's rotation order
    euler_rot.reorder(rot_order)

    # Convert rotations from radians to degrees
    rotations = [
        math.degrees(euler_rot.x),
        math.degrees(euler_rot.y),
        math.degrees(euler_rot.z),
    ]

    # Get scale values in world space
    scale = m_transform_mtx.scale(om.MSpace.kWorld)

    # Return translation, rotation, and scale values
    return [translation.x, translation.y, translation.z], rotations, scale


def resetDrivenNodes(node):
    """use mgear convenience function to reset all available transform nodes

    Args:
        node (str): node to reset
    """
    children = mc.listRelatives(node, type="transform")
    controlNode = node.replace(DRIVEN_SUFFIX, CTL_SUFFIX)
    otherNode = node.replace(DRIVEN_SUFFIX, "")
    if mc.objExists(controlNode) and children and controlNode in children:
        transform.resetTransform(pm.PyNode(controlNode))
    elif mc.objExists("{}{}".format(node, RBF_LOCATOR_SUFFIX)):
        compoensateLoc = pm.PyNode("{}{}".format(node, RBF_LOCATOR_SUFFIX))
        transform.resetTransform(compoensateLoc)
    elif mc.objExists(otherNode):
        otherNode = pm.PyNode(otherNode)
        transform.resetTransform(otherNode)
    transform.resetTransform(pm.PyNode(node))


def __getResultingMatrix(drivenNode, parentNode, absoluteWorld=True):
    """convenience function, wrap. given two nodes, one parented under the
    other

    Args:
        drivenNode (str): name of the drivenNode
        parentNode (str): name of the parent node
        absoluteWorld (bool, optional): calculate in world or check for local
        differences

    Returns:
        mmaatrix: resulting matrix of driven and parent
    """
    drivenNode = pm.PyNode(drivenNode)
    nodeInverParMat = parentNode.getAttr("parentInverseMatrix")
    drivenMat = drivenNode.getMatrix(worldSpace=True)
    drivenMat_local = drivenNode.getMatrix(objectSpace=True)
    defaultMat = om.MMatrix()

    if defaultMat.isEquivalent(drivenMat_local) and not absoluteWorld:
        totalMatrix = defaultMat
        print("Pose recorded in local.")
    else:
        totalMatrix = drivenMat * nodeInverParMat
    return totalMatrix


def getDrivenMatrix(node, absoluteWorld=True):
    """check if there is a control node for the provided node(driven)
    if so, collect the matrix information for both

    Args:
        node (pynode): driven group/driven node
        absoluteWorld (bool, optional): get the world matrix or defaulted mat
        if the control is zeroed out.

    Returns:
        MMatrix: of total position including the control
    """
    children = mc.listRelatives(node, type="transform") or []
    node = pm.PyNode(node)
    controlNode = node.replace(DRIVEN_SUFFIX, CTL_SUFFIX)
    otherNode = node.replace(DRIVEN_SUFFIX, "")
    if mc.objExists(controlNode) and controlNode in children:
        totalMatrix = __getResultingMatrix(
            controlNode, node, absoluteWorld=absoluteWorld
        )
    elif mc.objExists(otherNode) and otherNode in children:
        totalMatrix = __getResultingMatrix(
            otherNode, node, absoluteWorld=absoluteWorld
        )
    elif mc.objExists("{}{}".format(node, RBF_LOCATOR_SUFFIX)):
        compoensateLoc = pm.PyNode("{}{}".format(node, RBF_LOCATOR_SUFFIX))
        nodeInverParMat = node.getAttr("parentInverseMatrix")
        controlMat = compoensateLoc.getMatrix(worldSpace=True)
        totalMatrix = controlMat * nodeInverParMat
    else:
        totalMatrix = node.getMatrix(worldSpace=False)

    return totalMatrix


def createRBFToggleAttr(node):
    """creates a node to toggle the rbf pose that drives the node

    Args:
        node (str): desired node to be tagged with attr
    """
    try:
        mc.addAttr(
            node, ln=RBF_SCALE_ATTR, at="float", dv=1, min=0, max=1, k=True
        )
    except RuntimeError:
        pass


def connectRBFToggleAttr(node, rbfNode, rbfEnableAttr):
    """connect the "envelope" attr with its corresponding rbfNode

    Args:
        node (str): node with attr
        rbfNode (str): rbf node with receiving attr
        rbfEnableAttr (str): targeted rbf node for disabling node
    """
    nodeAttr = "{}.{}".format(node, RBF_SCALE_ATTR)
    rbfAttr = "{}.{}".format(rbfNode, rbfEnableAttr)
    mc.connectAttr(nodeAttr, rbfAttr, f=True)


def deleteRBFToggleAttr(node):
    """remove the toggle attribute from the node

    Args:
        node (str): node to remove toggle attr from
    """
    mc.setAttr("{}.{}".format(node, RBF_SCALE_ATTR), edit=True, lock=False)
    try:
        mc.deleteAttr("{}.{}".format(node, RBF_SCALE_ATTR))
    except RuntimeError:
        pass


def getConnectedRBFToggleNode(node, toggleAttr):
    """get the node connected to the rbf(node)

    Args:
        node (str): rbf node
        toggleAttr (str): envelope attr to check

    Returns:
        str: connected node
    """
    rbfAttr = "{}.{}".format(node, toggleAttr)
    driverControl = mc.listConnections(rbfAttr)
    if driverControl:
        return driverControl[0]
    return driverControl


def setToggleRBFAttr(node, value, toggleAttr):
    """Toggle rbfattr on or off (any value provided)

    Args:
        node (str): name of node with the attr to toggle rbf on/off
        value (int, bool): on/off
        toggleAttr (str): name of the attr to set
    """
    attrPlug = "{}.{}".format(node, toggleAttr)
    mc.setAttr(attrPlug, value)


def createDriverControlPoseAttr(node):
    """ensure the driverControlPoseAttr exists on the (RBF)node provided

    Args:
        node (str): name of the supported RBFNode
    """
    try:
        mc.addAttr(node, ln=DRIVER_POSES_INFO_ATTR, dt="string")
    except RuntimeError:
        pass


def setDriverControlPoseAttr(node, poseInfo):
    """set the driverControlPoseAttr with the poseInfo provided, as string

    Args:
        node (str): name of rbf node to set it on
        poseInfo (dict): of pose information
    """
    if not mc.attributeQuery(DRIVER_POSES_INFO_ATTR, n=node, ex=True):
        createDriverControlPoseAttr(node)
    mc.setAttr(
        "{}.{}".format(node, DRIVER_POSES_INFO_ATTR),
        str(poseInfo),
        type="string",
    )


def getDriverControlPoseAttr(node):
    """record the dict, stored as a str, holding driver control
    pose information.

    Args:
        node (str): name of the RBFNode supported node to query

    Returns:
        dict: of attr:[value at index]
    """
    try:
        poseInfo = mc.getAttr("{}.{}".format(node, DRIVER_POSES_INFO_ATTR))
        return ast.literal_eval(poseInfo)
    except ValueError:
        return {}


def updateDriverControlPoseAttr(node, driverControl, poseIndex):
    """get the ControlPoseDict add any additionally recorded values to and set

    Args:
        node (str): name of the RBFNode supported node
        driverControl (str): name of the control to queary attr info from
        poseIndex (int): to add the collected pose information to
    """
    # TODO future recording of all attrs goes here
    poseInfo = getDriverControlPoseAttr(node)
    attrsToUpdate = TRANSLATE_ATTRS + ROTATE_ATTRS + SCALE_ATTRS
    attrsToUpdate = list(set(attrsToUpdate + list(poseInfo.keys())))
    for attr in attrsToUpdate:
        attrPoseIndices = poseInfo.get(attr, [])
        lengthOfList = len(attrPoseIndices) - 1
        newVal = mc.getAttr("{}.{}".format(driverControl, attr))
        if not attrPoseIndices or lengthOfList < poseIndex:
            attrPoseIndices.insert(poseIndex, newVal)
        elif lengthOfList >= poseIndex:
            attrPoseIndices[poseIndex] = newVal

        poseInfo[attr] = attrPoseIndices
    setDriverControlPoseAttr(node, poseInfo)


def recallDriverControlPose(driverControl, poseInfo, index):
    """set the driverControl to the index requested. Set as many attrs as is
    provided in the poseInfo

    Args:
        driverControl (str): control to set poseAttr infomation on
        poseInfo (dict): of poses
        index (int): poseInfo[attrName]:[index]
    """
    failed_attrs = []
    for attr, values in poseInfo.items():
        try:
            # not to be bothered with locked, hidden, connected attrs
            mc.setAttr("{}.{}".format(driverControl, attr), values[index])
        except Exception:
            failed_attrs.append(attr)
    if failed_attrs:
        failed_attrs.insert(0, driverControl)
        msg = (
            "Pose cannot be applied to the following attributes: \n{}".format(
                failed_attrs
            )
        )
        print(msg)


def createDriverControlAttr(node):
    """create the string attr where information will be stored for query
    associated driver anim control

    Args:
        node (str): rbf node to tag with information
    """
    try:
        mc.addAttr(node, ln=DRIVER_CTL_ATTR_NAME, dt="string")
    except RuntimeError:
        pass


def getDriverControlAttr(node):
    """get the stored information from control attr

    Args:
        node (str): name of rbfNode

    Returns:
        str: contents of attr, animControl
    """
    try:
        return mc.getAttr("{}.{}".format(node, DRIVER_CTL_ATTR_NAME))
    except ValueError:
        return ""


def setDriverControlAttr(node, controlName):
    """create and set attr with the driver animControl string

    Args:
        node (str): name of rbfnode
        controlName (str): name of animControl(usually)
    """
    if not mc.attributeQuery(DRIVER_CTL_ATTR_NAME, n=node, ex=True):
        createDriverControlAttr(node)
    mc.setAttr(
        "{}.{}".format(node, DRIVER_CTL_ATTR_NAME), controlName, type="string"
    )


def getSceneRBFNodes():
    """get all rbf nodes in the scene of supported type

    Returns:
        list: of rbf nodes, see supported types
    """
    return mc.ls(type=SUPPORTED_RBF_NODES) or []


def getSceneSetupNodes():
    """get rbf nodes with setups attributes

    Returns:
        list: of rbf nodes with setup information
    """
    global SUPPORTED_RBF_NODES

    # Dynamically add "weightDriver" if the plugin is loaded
    if mc.pluginInfo("weightDriver", q=True, loaded=True):
        SUPPORTED_RBF_NODES = (
            "mGearWeightDriver",
            "weightDriver"
        )

    nodes = set()

    for node_type in SUPPORTED_RBF_NODES:
        if node_type in mc.ls(nodeTypes=True):
            nodes.update(mc.ls(type=node_type))

    return [
        rbf for rbf in nodes
        if mc.attributeQuery(RBF_SETUP_ATTR, n=rbf, ex=True)
    ]


def getRbfSceneSetupsInfo(includeEmpty=True):
    """gather scene rbf nodes with setups in dict

    Args:
        includeEmpty (bool, optional): should rbf nodes with empty setup names
        be included

    Returns:
        dict: setupName(str):list associated rbf nodes
    """
    setups_dict = {"empty": []}
    for rbfNode in getSceneSetupNodes():
        setupName = mc.getAttr("{}.{}".format(rbfNode, RBF_SETUP_ATTR))
        if setupName == "":
            setups_dict["empty"].append(rbfNode)
            continue
        if setupName in setups_dict:
            setups_dict[setupName].append(rbfNode)
        else:
            setups_dict[setupName] = [rbfNode]
    if not includeEmpty:
        setups_dict.pop("empty")
    return setups_dict


def setSetupName(node, setupName):
    """set setup name on the specified node

    Args:
        node (str): name of rbf node to set
        setupName (str): name of setup
    """
    if not mc.attributeQuery(RBF_SETUP_ATTR, n=node, ex=True):
        mc.addAttr(node, ln=RBF_SETUP_ATTR, dt="string")
    mc.setAttr("{}.{}".format(node, RBF_SETUP_ATTR), setupName, type="string")


def getSetupName(node):
    """get setup name from specified rbf node

    Args:
        node (str): name of rbf node

    Returns:
        str: name of setup associated with node
    """
    if not mc.attributeQuery(RBF_SETUP_ATTR, n=node, ex=True):
        return None
    return mc.getAttr("{}.{}".format(node, RBF_SETUP_ATTR))


class RBFNode(object):
    """A class to normalize the function between different types of rbf nodes
    that essentially perform the same task. Look to weightNode_io for examples
    of normalized function calls to specific nodeType information with this
    class.

    Attributes:
        name (str): name of the node that either exists or to be created
        rbfType (str): nodeType to create node of supported type
        transformNode (str): name of transform node
    """

    def __init__(self, name):
        self.name = name
        self.transformNode = None
        if mc.objExists(name) and mc.nodeType(name) in SUPPORTED_RBF_NODES:
            self.rbfType = mc.nodeType(name)
            self.transformNode = self.getTransformParent()
            self.lengthenCompoundAttrs()
        else:
            self.create()
            createDriverControlAttr(self.name)

    def __repr__(self):
        """overwritten so that the RBFNode instance can be treated as a pymal
        node. Convenience

        Returns:
            str: name of rbfNode node correctly formated
        """
        return self.name

    def __unicode__(self):
        """overwritten so that the RBFNode instance can be treated as a pymal
        node. Convenience

        Returns:
            str: name of rbfNode node correctly formated
        """
        if PY2:
            return unicode(self.name).encode("utf-8")
        return str(self.name).encode("utf-8")

    def __str__(self):
        """overwritten so that the RBFNode instance can be treated as a pymal
        node. Convenience

        Returns:
            str: name of rbfNode node correctly formated
        """
        return str(self.name)

    @staticmethod
    def nodeType_suffix():
        """optional override with a module/node specific suffix for naming"""
        return GENERIC_SUFFIX

    @staticmethod
    def formatName(name, suffix):
        """standardized the naming of all rbf nodes for consistency

        Returns:
            str: name of all supported rbf nodes
        """
        return "{}{}".format(name, suffix)

    def create(self):
        """create an RBF node of type, defined by the subclassed module

        Raises:
            NotImplementedError: Description
        """
        raise NotImplementedError()

    def getPoseInfo(self):
        """get poseInfo dict

        Raises:
            NotImplementedError: each rbf node is unique, adhere here for
            rbf manager ui support
        """
        raise NotImplementedError()

    def getNodeInfo(self):
        """get all the info for for the node in the form of a dict

        Raises:
            NotImplementedError: NotImplementedError: each rbf node is unique,
            adhere here for rbf manager ui support
        """
        raise NotImplementedError()

    def lengthenCompoundAttrs(self):
        """convenience function, sanity check for zero'd compound attrs"""
        pass

    def addPose(self, poseInput, poseValue, posesIndex=None):
        """add pose to the weightDriver node provided. Also used for editing
        an existing pose, since you can specify the index. If non provided
        assume new

        Args:
            node (str): weightedDriver
            poseInput (list): list of the poseInput values
            poseValue (list): of poseValue values
            posesIndex (int, optional): at desired index, if none assume
            latest/new
        """
        if posesIndex is None:
            posesIndex = len(self.getPoseInfo()["poseInput"])
        self.updateDriverControlPoseAttr(posesIndex)
        raise NotImplementedError()

    def deletePose(self, indexToPop):
        """gather information on node, remove desired index and reapply

        Args:
            node (str): weightDriver
            indexToPop (int): pose index to remove
        """
        raise NotImplementedError()

    def getDriverNode(self):
        """get nodes that are driving weightDriver node

        Returns:
            list: of driver nodes
        """
        raise NotImplementedError()

    def getDriverNodeAttributes(self):
        """get the connected attributes of the provided compound attr in order
        of index - Sanity check

        Returns:
            list: of connected attrs in order
        """
        raise NotImplementedError()

    def getDrivenNode(self):
        """get driven nodes connected to weightDriver

        Returns:
            list: of driven nodes
        """
        raise NotImplementedError()

    def getDrivenNodeAttributes(self):
        """get the connected attributes of the provided compound attr in order
        of index - Sanity check

        Returns:
            list: of connected attrs in order
        """
        raise NotImplementedError()

    def getSetupName(self):
        """get the name of the setup that the RBFNode belongs to

        Returns:
            str: skirt_L0, shoulder_R0
        """
        return getSetupName(self.name)

    def setSetupName(self, setupName):
        """set the name of the setup for the RBFNode

        Args:
            setupName (str): desired name
        """
        setSetupName(str(self.name), setupName)

    def setDriverNode(self, driverNode, driverAttrs):
        """set the node that will be driving the evaluation on our poses

        Args:
            node (str): name of weightDriver node
            driverNode (str): name of driver node
            driverAttrs (list): of attributes used to perform evaluations
        """
        raise NotImplementedError()

    def setDrivenNode(self, drivenNode, drivenAttrs, parent=True):
        """set the node to be driven by the weightDriver

        Args:
            node (str): weightDriver node
            drivenNode (str): name of node to be driven
            drivenAttrs (list): of attributes to be driven by weightDriver
        """
        raise NotImplementedError()

    def getTransformParent(self):
        """get a dict of all the information to be serialized to/from json

        Returns:
            dict: information to be recreated on import
        """
        NotImplementedError()

    def copyPoses(self, nodeB, emptyPoseValues=True):
        """Copy poses from nodeA to nodeB with the option to be blank or node
        for syncing nodes

        Args:
            nodeB (str): name of weightedNode
            emptyPoseValues (bool, optional): should the copy just be the same
            number of poses but blank output value

        Returns:
            n/a: n/a
        """
        NotImplementedError()

    def setDriverControlPoseAttr(self, poseInfo):
        """set the poseInfo as a string to the DriverControlPoseAttr

        Args:
            poseInfo (dict): of pose information to set, as a str
        """
        setDriverControlPoseAttr(self.name, poseInfo)

    def getDriverControlPoseAttr(self):
        """retrieve poseInfo from the driverControlPoseAttr as a dict

        Returns:
            dict: of pose information
        """
        driverPoseInfoAttr = getDriverControlPoseAttr(self.name)
        return driverPoseInfoAttr

    def updateDriverControlPoseAttr(self, posesIndex):
        """update the driverControlPoseAttr at the specified index

        Args:
            posesIndex (int): update the pose information at the index
        """
        driverControl = self.getDriverControlAttr()
        updateDriverControlPoseAttr(self.name, driverControl, posesIndex)

    def setDriverControlAttr(self, controlName):
        """create and set attr with the driver animControl string

        Args:
            controlName (str): name of animControl(usually)
        """
        setDriverControlAttr(self.name, controlName)

    def getDriverControlAttr(self):
        """get the driverControlAttr

        Returns:
            str: the name of the control set within the attr
        """
        driverControl = getDriverControlAttr(self.name)
        if driverControl == "":
            driverControl = self.getDriverNode()[0]
        return driverControl

    def recallDriverPose(self, poseIndex):
        """recall the pose on the controlDriver with information at the
        specified index

        Args:
            poseIndex (int): desired index, matches pose index on rbfNode
        """
        driverControl = self.getDriverControlAttr()
        poseInfo = getDriverControlPoseAttr(self.name)
        recallDriverControlPose(driverControl, poseInfo, poseIndex)

    def getPoseValues(self, resetDriven=True, absoluteWorld=True):
        """get all pose values from rbf node

        Args:
            resetDriven (bool, optional): reset driven animControl

        Returns:
            list: of poseValues
        """
        attributeValue_dict = {}
        drivenNode = self.getDrivenNode()[0]
        drivenAttrs = self.getDrivenNodeAttributes()
        if mc.attributeQuery(
            "matrix", n=drivenNode, ex=True
        ) and mc.attributeQuery("worldMatrix", n=drivenNode, ex=True):
            (trans, rotate, scale) = decompMatrix(
                drivenNode,
                getDrivenMatrix(drivenNode, absoluteWorld=absoluteWorld),
            )
        for attr in drivenAttrs:
            if attr in TRANSLATE_ATTRS:
                index = TRANSLATE_ATTRS.index(attr)
                attributeValue_dict[attr] = trans[index]
            elif attr in ROTATE_ATTRS:
                index = ROTATE_ATTRS.index(attr)
                attributeValue_dict[attr] = rotate[index]
            elif attr in SCALE_ATTRS:
                index = SCALE_ATTRS.index(attr)
                attributeValue_dict[attr] = scale[index]
            else:
                nodePlug = "{}.{}".format(drivenNode, attr)
                attributeValue_dict[attr] = mc.getAttr(nodePlug)
        if resetDriven:
            resetDrivenNodes(drivenNode)
        poseValues = [attributeValue_dict[attr] for attr in drivenAttrs]
        return poseValues

    def forceEvaluation(self):
        """convenience function to force re evaluation on the rbf nodes
        most nodes support this
        """
        NotImplementedError()

    def getRBFToggleAttr(self):
        """get the specific to the type, "envelope" attr for rbf node"""
        NotImplementedError()
        # return "scale"

    def deleteRBFToggleAttr(self):
        """convenience function to delete the connected "enevelope" from the
        anim control node

        Returns:
            TYPE: Description
        """
        driverControl = self.getConnectedRBFToggleNode()
        if not driverControl:
            return
        deleteRBFToggleAttr(driverControl)

    def setToggleRBFAttr(self, value):
        """Toggle rbfattr on or off (any value provided)

        Args:
            value (TYPE): Description
        """
        driverControl = self.getConnectedRBFToggleNode()
        setToggleRBFAttr(driverControl, value, RBF_SCALE_ATTR)

    def getConnectedRBFToggleNode(self):
        """return the node connected to the RBFNodes toggle attr

        Returns:
            str: name of node
        """
        return getConnectedRBFToggleNode(self.name, self.getRBFToggleAttr())

    def syncPoseIndices(self, srcNode):
        raise NotImplementedError()

    def applyDefaultPose(self, posesIndex=0):
        """apply default pose, WARNING. Applying default on more than one index
        will result in rbf decomp error.

        Args:
            posesIndex (int, optional): index to default values
        """
        driverNode = self.getDriverNode()[0]
        driverAttrs = self.getDriverNodeAttributes()
        poseInputs = getMultipleAttrs(driverNode, driverAttrs)
        drivenAttrs = self.getDrivenNodeAttributes()
        newPoseValues = []
        for attr in drivenAttrs:
            if attr in SCALE_ATTRS:
                newPoseValues.append(1.0)
            else:
                newPoseValues.append(0.0)
        self.addPose(
            poseInput=poseInputs,
            poseValue=newPoseValues,
            posesIndex=posesIndex,
        )

    def compensateForDirectConnect(self):
        drivenNode = self.getDrivenNode()[0]
        if (
            mc.nodeType(drivenNode) not in ["transform", "joint"]
            or mc.objExists("{}{}".format(drivenNode, RBF_LOCATOR_SUFFIX))
            or drivenNode.endswith(DRIVEN_SUFFIX)
        ):
            return
        transformAttrs = set(TRANSLATE_ATTRS + ROTATE_ATTRS + SCALE_ATTRS)
        drivenAttrs = set(self.getDrivenNodeAttributes())
        if not drivenAttrs.intersection(transformAttrs):
            return
        cmpLoc = compensateLocator(drivenNode)
