"""Rigbits, SDK i/o

exportSDKs(["drivenNodeA", "drivenNodeB"], "path/to/desired/output.json")
importSDKs(path/to/desired/output.json)

# MIRRORING -------
# copy from source, say left, to target, right
copySDKsToNode("jacketFlap_L1_fk0_sdk",
               "neck_C0_0_jnt",
               "jacketFlap_R1_fk0_sdk")

# invert/mirror the attributes necessary for the other side,
# in this case it is the following attributes
mirrorSDKkeys("jacketFlap_R1_fk0_sdk",
              attributes=["rotateZ"],
              invertDriver=True,
              invertDriven=False)

mirrorSDKkeys("jacketFlap_R1_fk0_sdk",
              attributes=["translateX", "translateY"],
              invertDriver=True,
              invertDriven=True)

# in this other instance, it was the same
copySDKsToNode("jacketFlap_L0_fk0_sdk",
               "neck_C0_0_jnt",
               "jacketFlap_R0_fk0_sdk")

Attributes:
    SDK_ANIMCURVES_TYPE (list): sdk anim curves to support
"""
import json
import pprint

import mgear.pymaya as pm
from mgear.pymaya import attr as pm_attr
from mgear.core import attribute

import mgear.core.utils as mUtils
from .six import string_types

SDK_UTILITY_TYPE = ("blendWeighted",)
SDK_ANIMCURVES_TYPE = ("animCurveUA", "animCurveUL", "animCurveUU")


# ==============================================================================
# Data export
# ==============================================================================
def _importData(filePath):
    """Return the contents of a json file. Expecting, but not limited to,
    a dictionary.

    Args:
        filePath (string): path to file

    Returns:
        dict: contents of json file, expected dict
    """
    try:
        with open(filePath, "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(e)


def _exportData(data, filePath):
    """export data, dict, to filepath provided

    Args:
        data (dict): expected dict, not limited to
        filePath (string): path to output json file
    """
    try:
        with open(filePath, "w") as f:
            json.dump(data, f, sort_keys=False, indent=4)
    except Exception as e:
        print(e)


# ==============================================================================
# pymel Convenience
# ==============================================================================


def getPynodes(nodes):
    """Conevenience function to allow uses to pass in strings, but convert to
    pynodes if not already.

    Args:
        nodes (list): string names

    Returns:
        list: of pynodes
    """
    pynodes = []
    for node in nodes:
        if isinstance(node, string_types):
            node = pm.PyNode(node)
        pynodes.append(node)
    return pynodes


# ==============================================================================
# sdk functions
# ==============================================================================


def getSDKDestination(animNodeOutputPlug):
    """Get the final destination of the sdk node, skips blendweighted
    and conversion node to get the transform node.
    TODO: Open this up to provided type destination

    Args:
        animNodeOutputPlug (string): animationNode.output

    Returns:
        list: name of the node, and attr
    """
    connectionTypes = [SDK_UTILITY_TYPE[0], "transform", "blendShape", "shape"]
    targetDrivenAttr = []
    for cType in connectionTypes:
        targetTypeDrivenAttr = pm.listConnections(
            animNodeOutputPlug,
            source=False,
            destination=True,
            plugs=True,
            type=cType,
            scn=True,
        )
        if targetTypeDrivenAttr and cType == "blendShape":
            # NOTE: we assume is only index 0
            # need to resolve the alias attr name before process the SDK
            targetTypeDrivenAttr = [
                pm.PyNode(
                    attribute.resolve_alias_attr(targetTypeDrivenAttr[0])
                )
            ]

        targetDrivenAttr.extend(targetTypeDrivenAttr)
    if (
        targetDrivenAttr
        and pm.nodeType(pm.PyNode(targetDrivenAttr[0]).nodeName())
        == "blendWeighted"
    ):
        blendNodeOutAttr = targetDrivenAttr[0].node().attr("output")
        targetDrivenAttr = pm.listConnections(
            blendNodeOutAttr,
            destination=True,
            plugs=True,
            scn=True,
            shapes=True,
        )
    drivenNode, drivenAttr = targetDrivenAttr[0].split(".")
    return drivenNode, drivenAttr


def getMultiDriverSDKs(driven, sourceDriverFilter=None):
    """get the sdk nodes that are added through a blendweighted node

    Args:
        driven (string): name of the driven node
        sourceDriverFilter (list, pynode): Driver transforms to filter by,
        if the connected SDK is not driven by this node it will not be returned.

    Returns:
        list: of sdk nodes
    """
    sdkDrivers = []
    for sdkUtility in SDK_UTILITY_TYPE:
        blend_NodePair = (
            pm.listConnections(
                driven,
                source=True,
                type=sdkUtility,
                exactType=True,
                plugs=True,
                connections=True,
                sourceFirst=True,
                scn=True,
            )
            or []
        )

        if not blend_NodePair:
            continue
        for pairs in blend_NodePair:
            sdkPairs = getConnectedSDKs(
                pairs[0].nodeName(), sourceDriverFilter=sourceDriverFilter
            )
            for sPair in sdkPairs:
                sdkDrivers.append([sPair[0], pairs[1]])
    return sdkDrivers


def getConnectedSDKs(driven, curvesOfType=[], sourceDriverFilter=None):
    """get all the sdk, animcurve, nodes/plugs connected to the provided node.

    Args:
        node (str, pynode): name of node, or pynode
        curvesOfType (list, optional): animCurve nodes of type if none provided
        will fall back on module defined supported set.
        sourceDriverFilter (list, pynode): Driver transforms to filter by,
        if the connected SDK is not driven by this node it will not be returned.

    Returns:
        list: of sdk nodes, paired with the node/attr they effect
    """
    retrievedSDKNodes = []
    if not curvesOfType:
        curvesOfType = SDK_ANIMCURVES_TYPE
    for animCurve in curvesOfType:
        animCurveNodes = (
            pm.listConnections(
                driven,
                source=True,
                type=animCurve,
                exactType=True,
                plugs=True,
                connections=True,
                sourceFirst=True,
                scn=True,
            )
            or []
        )

        # If the filter is given, filter out only nodes driven by
        # transforms inside sourceDriverFilter
        if sourceDriverFilter and animCurveNodes:
            filteredSDKNodes = []
            for driver_plug, anim_plug in animCurveNodes:
                # Getting the connected Driver Transform nodes
                connectedDrivers = pm.listConnections(
                    driver_plug.node(),
                    source=True,
                    type="transform",
                    exactType=True,
                    scn=True,
                )
                # If any are found, add them to filteredSDKNodes
                # if the node name is in sourceDriverFilter
                if connectedDrivers:
                    for conDriver in connectedDrivers:
                        if conDriver.node() in sourceDriverFilter:
                            filteredSDKNodes.append((driver_plug, anim_plug))

            # Replacing animCurveNodes with the new filtered list.
            animCurveNodes = filteredSDKNodes

        retrievedSDKNodes.extend(animCurveNodes)

    return retrievedSDKNodes


def getSDKInfo(animNode):
    """get all the information from an sdk/animCurve in a dictioanry
    for exporting.

    Args:
        animNode (pynode): name of node, pynode

    Returns:
        dict: dictionary of all the attrs to be exported
    """
    sdkInfo_dict = {}
    sdkKey_Info = []
    numberOfKeys = int(
        len(pm.listAttr("{0}.ktv".format(animNode), multi=True)) / 3
    )
    itt_list = pm.keyTangent(animNode, itt=True, q=True)
    ott_list = pm.keyTangent(animNode, ott=True, q=True)
    # maya doesnt return value if there is only one key frame set.
    if itt_list is None:
        itt_list = ["linear"]
    if ott_list is None:
        ott_list = ["linear"]

    for index in range(0, numberOfKeys):
        value = pm.getAttr("{0}.keyTimeValue[{1}]".format(animNode, index))
        absoluteValue = pm.keyframe(
            animNode, q=True, valueChange=True, index=(index,)
        )[0]
        keyData = [value[0], absoluteValue, itt_list[index], ott_list[index]]
        sdkKey_Info.append(keyData)
    sdkInfo_dict["keys"] = sdkKey_Info
    sdkInfo_dict["type"] = animNode.type()
    sdkInfo_dict["preInfinity"] = animNode.getAttr("preInfinity")
    sdkInfo_dict["postInfinity"] = animNode.getAttr("postInfinity")
    sdkInfo_dict["weightedTangents"] = animNode.getAttr("weightedTangents")
    animNodeInputPlug = "{0}.input".format(animNode.nodeName())
    sourceDriverAttr = pm.listConnections(
        animNodeInputPlug, source=True, plugs=True, scn=True
    )[0]
    driverNode, driverAttr = sourceDriverAttr.split(".")
    sdkInfo_dict["driverNode"] = driverNode
    sdkInfo_dict["driverAttr"] = driverAttr

    animNodeOutputPlug = "{0}.output".format(animNode.nodeName())
    drivenNode, drivenAttr = getSDKDestination(animNodeOutputPlug)
    sdkInfo_dict["drivenNode"] = drivenNode
    sdkInfo_dict["drivenAttr"] = drivenAttr

    return sdkInfo_dict


def getAllSDKInfoFromNode(node):
    """returns a dict for all of the connected sdk/animCurve on
    the provided node

    Args:
        node (pynode): name of node to the be searched

    Returns:
        dict: of all of the sdk nodes
    """
    allSDKInfo_dict = {}
    retrievedSDKNodes = getConnectedSDKs(node)
    retrievedSDKNodes.extend(getMultiDriverSDKs(node))
    for animPlug, targetPlug in retrievedSDKNodes:
        allSDKInfo_dict[animPlug.nodeName()] = getSDKInfo(animPlug.node())
    return allSDKInfo_dict


def removeSDKs(node, attributes=[], sourceDriverFilter=None):
    """Convenience function to remove, delete, all sdk nodes associated with
    the provided node

    Args:
        node (pynode): name of the node
        attributes (list, optional): list of attributes to remove sdks from
        if none provided, assume all
        sourceDriverFilter (list, pynode): Driver transforms to filter by,
        if the connected SDK is not driven by this node it will not be returned.
    """
    toDelete = []
    # if no attrs provided, assume all
    if not attributes:
        attributes = pm.listAttr(node, connectable=True)
    sourceSDKInfo = getConnectedSDKs(
        node, sourceDriverFilter=sourceDriverFilter
    )
    sourceSDKInfo.extend(
        getMultiDriverSDKs(node, sourceDriverFilter=sourceDriverFilter)
    )
    for source, dest in sourceSDKInfo:
        if dest.plugAttr(longName=True) not in attributes:
            continue
        toDelete.append(source.node())
    pm.delete(toDelete)


def copySDKsToNode(
    sourceDriven,
    targetDriver,
    targetDriven,
    sourceAttributes=[],
    sourceDriverFilter=None,
):
    """Duplicates sdk nodes from the source drive, to any designated target
    driver/driven

    Args:
        sourceDriven (pynode): source to copy from
        targetDriver (pynode): to drive the new sdk node
        targetDriven (pynode): node to be driven
        sourceAttributes (list, optional): of attrs to copy, if none provided
        assume all
        sourceDriverFilter (list, pynode): Driver transforms to filter by,
        if the connected SDK is not driven by this node it will not be returned.

    Returns:
        TYPE: n/a
    """
    sourceDriven, targetDriver, targetDriven = getPynodes(
        [sourceDriven, targetDriver, targetDriven]
    )
    if sourceDriven == targetDriven:
        pm.warning("You cannot copy SDKs to the same name.")
        return
    # if no attrs provided, assume all
    if not sourceAttributes:
        sourceAttributes = pm.listAttr(sourceDriven, connectable=True)
        sourceAttributesNames = [a.longName() for a in sourceAttributes if isinstance(a, pm_attr.Attribute)]
    # sourceDriverFilter = None
    sourceSDKInfo = getConnectedSDKs(sourceDriven, sourceDriverFilter=None)
    sourceSDKInfo.extend(getMultiDriverSDKs(sourceDriven, sourceDriverFilter))

    for source, dest in sourceSDKInfo:
        if dest.plugAttr(longName=True) not in sourceAttributesNames:
            continue

        sourceDriverAttr = pm.listConnections(
            "{0}.input".format(source.nodeName()),
            source=True,
            plugs=True,
            scn=True,
        )[0]

        duplicateCurve = pm.duplicate(
            source,
            name="{0}_{1}".format(
                targetDriven.name(), dest.attrName(longName=True)
            ),
        )[0]

        pm.connectAttr(
            "{0}.{1}".format(
                targetDriver, sourceDriverAttr.attrName(longName=True)
            ),
            "{0}.input".format(duplicateCurve),
        )

        # drivenNode, drivenAttr = getSDKDestination(duplicateCurve.output)
        drivenAttrPlug = "{0}.{1}".format(
            targetDriven, dest.longName()
        )
        if pm.listConnections(drivenAttrPlug):
            targetAttrPlug = getBlendNodes(drivenAttrPlug)
        else:
            targetAttrPlug = drivenAttrPlug

        try:
            pm.connectAttr(duplicateCurve.output, targetAttrPlug)
        except RuntimeError:
            # error when trying to connect to a plug that is already connected.
            # trying next avalible plug.
            targetAttrPlug = targetAttrPlug.replace("[1]", "[0]")
            pm.connectAttr(duplicateCurve.output, targetAttrPlug)


def stripKeys(animNode):
    """remove animation keys from the provided sdk node

    Args:
        animNode (pynode): sdk/anim node
    """
    numKeys = len(pm.listAttr(animNode + ".ktv", multi=True)) // 3
    for x in range(0, numKeys):
        animNode.remove(0)


def invertKeyValues(newKeyNode, invertDriver=True, invertDriven=True):
    """Mirror keyframe node procedure, in case you need to flip your SDK's.

    Args:
        newKeyNode (PyNode): sdk node to invert values on
        invertDriver (bool, optional): should the drivers values be inverted
        invertDriven (bool, optional): should the drivens values be inverted
    """
    sdkInfo_dict = getSDKInfo(newKeyNode)
    stripKeys(newKeyNode)
    animKeys = sdkInfo_dict["keys"]
    for index in range(0, len(animKeys)):
        frameValue = animKeys[index]
        if invertDriver and invertDriven:
            timeValue = frameValue[0] * -1
            value = frameValue[1] * -1
        elif invertDriver and not invertDriven:
            timeValue = frameValue[0] * -1
            value = frameValue[1]
        elif not invertDriver and invertDriven:
            timeValue = frameValue[0]
            value = frameValue[1] * -1
        else:
            timeValue = frameValue[0]
            value = frameValue[1]

        pm.setKeyframe(
            newKeyNode,
            float=timeValue,
            value=value,
            itt=frameValue[2],
            ott=frameValue[3],
        )


def mirrorSDKkeys(node, attributes=[], invertDriver=True, invertDriven=True):
    """mirror/invert the values on the specified node and attrs, get the sdks
    and invert those values

    Args:
        node (pynode): node being driven to have its sdk values inverted
        attributes (list, optional): attrs to be inverted
        invertDriver (bool, optional): should the driver, "time" values
        be inverted
        invertDriven (bool, optional): should the driven, "value" values
        be inverted
    """
    sourceSDKInfo = getConnectedSDKs(node)
    sourceSDKInfo.extend(getMultiDriverSDKs(node))
    if not attributes:
        attributes = pm.listAttr(node, connectable=True)
    for source, dest in sourceSDKInfo:
        if dest.plugAttr(longName=True) not in attributes:
            continue
        animCurve = source.node()
        invertKeyValues(
            animCurve, invertDriver=invertDriver, invertDriven=invertDriven
        )


def getBlendNodes(attrPlug):
    """Check the attrPlug (node.attr) provided for any existing connections
    if blendWeighted exists, return the appropriate input[#], if sdk, create
    a blendweighted and connect sdk, return input[#]

    Args:
        attrPlug (string): node.attr

    Returns:
        string: node.attr of the blendweighted node that was just created or
        existing
    """
    # check what the connection type is
    blendNode = pm.listConnections(attrPlug, scn=True)
    if pm.nodeType(blendNode[0]) in SDK_ANIMCURVES_TYPE:
        existingAnimNode = blendNode[0]
        blendNodeName = "{0}_bwn".format(attrPlug.replace(".", "_"))
        blendNode = [pm.createNode("blendWeighted", n=blendNodeName)]
        pm.connectAttr(blendNode[0].attr("output"), attrPlug, f=True)
        destPlug = "{0}.input[0]".format(blendNode[0].name())
        pm.connectAttr(existingAnimNode.attr("output"), destPlug, f=True)
    if pm.nodeType(blendNode[0]) in SDK_UTILITY_TYPE:
        blendNode = blendNode[0]
    if isinstance(blendNode, list):
        blendNode = blendNode[0]
    numOfInputs = len(blendNode.getAttr("input"))
    destPlug = "{0}.input[{1}]".format(blendNode.name(), numOfInputs)
    return destPlug


def createSDKFromDict(sdkInfo_dict):
    """Create a sdk node from the provided info dict

    Args:
        sdkInfo_dict (dict): dict of node information to create

    Returns:
        PyNode: created sdk node
    """
    # resolve the alias name just in case is a blendshape
    sdkAttrName = "{0}.{1}".format(
        sdkInfo_dict["drivenNode"],
        sdkInfo_dict["drivenAttr"],
    )
    sdkAttrAliasName = attribute.get_alias_for_attr(sdkAttrName).split(".")[1]

    sdkName = "{0}_{1}".format(
        sdkInfo_dict["drivenNode"],
        sdkAttrAliasName,
    )
    sdkNode = pm.createNode(sdkInfo_dict["type"], name=sdkName, ss=True)
    pm.connectAttr(
        "{0}.{1}".format(
            sdkInfo_dict["driverNode"], sdkInfo_dict["driverAttr"]
        ),
        "{0}.input".format(sdkNode),
        f=True,
    )

    drivenAttrPlug = "{0}.{1}".format(
        sdkInfo_dict["drivenNode"], sdkInfo_dict["drivenAttr"]
    )

    if pm.listConnections(drivenAttrPlug):
        targetAttrPlug = getBlendNodes(drivenAttrPlug)
    else:
        targetAttrPlug = drivenAttrPlug

    pm.connectAttr(sdkNode.output, targetAttrPlug, f=True)

    animKeys = sdkInfo_dict["keys"]
    for index in range(0, len(animKeys)):
        frameValue = animKeys[index]
        # Note: fixed is not supported by setKeyframe. we swap it to linear
        pm.displayWarning(
            "SDK fixed interpolation is not supported by setKeyframe."
            " We swap it to linear"
        )
        it = "linear" if frameValue[2] == "fixed" else frameValue[2]
        ot = "linear" if frameValue[3] == "fixed" else frameValue[3]
        pm.setKeyframe(
            sdkNode, float=frameValue[0], value=frameValue[1], itt=it, ott=ot
        )

    sdkNode.setAttr("preInfinity", sdkInfo_dict["preInfinity"])
    sdkNode.setAttr("postInfinity", sdkInfo_dict["postInfinity"])
    pm.keyTangent(sdkNode)
    pm.keyTangent(
        sdkNode, edit=True, weightedTangents=sdkInfo_dict["weightedTangents"]
    )

    return sdkNode


def exportSDKs(nodes, filePath):
    """exports the sdk information based on the provided nodes to a json file

    Args:
        nodes (list): of nodes to export
        filePath (string): full filepath to export jsons to
    """
    sdksToExport_dict = {}

    for node in nodes:
        node = getPynodes([node])[0]
        sdksToExport_dict.update(getAllSDKInfoFromNode(node))
    _exportData(sdksToExport_dict, filePath)
    return sdksToExport_dict


@mUtils.one_undo
def importSDKs(filePath):
    """create sdk nodes from json file, connected to drivers and driven

    Args:
        filePath (string): path to json file
    """
    allSDKInfo_dict = _importData(filePath)
    createdNodes = []
    failedNodes = []
    for sdkName, sdkInfo_dict in allSDKInfo_dict.items():
        try:
            createdNodes.append(createSDKFromDict(sdkInfo_dict))
        except Exception as e:
            failedNodes.append(sdkName)
            print("{0}:{1}".format(sdkName, e))
    print("Nodes created ---------------------------------")
    pprint.pprint(createdNodes)

    print("Nodes failed  ---------------------------------")
    pprint.pprint(failedNodes)
