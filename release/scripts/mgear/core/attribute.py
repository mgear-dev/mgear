"""Attribute creation functions"""

#############################################
# GLOBAL
#############################################
import collections
import mgear
import mgear.pymaya as pm
import maya.cmds as cmds
import mgear.pymaya.datatypes as datatypes
from maya.api import OpenMaya
from .six import string_types

#############################################
# NODE
#############################################


def addAttribute(
    node,
    longName,
    attributeType,
    value=None,
    niceName=None,
    shortName=None,
    minValue=None,
    maxValue=None,
    keyable=True,
    readable=True,
    storable=True,
    writable=True,
    channelBox=False,
    softMinValue=None,
    softMaxValue=None,
):
    """Add attribute to a node

    Arguments:
        node (dagNode): The object to add the new attribute.
        longName (str): The attribute name.
        attributeType (str): The Attribute Type. Exp: 'string', 'bool',
            'long', etc..
        value (float or int): The default value.
        niceName (str): The attribute nice name. (optional)
        shortName (str): The attribute short name. (optional)
        minValue (float or int): minimum value. (optional)
        maxValue (float or int): maximum value. (optional)
        keyable (bool): Set if the attribute is keyable or not. (optional)
        readable (bool): Set if the attribute is readable or not. (optional)
        storable (bool): Set if the attribute is storable or not. (optional)
        writable (bool): Set if the attribute is writable or not. (optional)
        channelBox (bool): Set if the attribute is in the channelBox or not,
            when the attribute is not keyable. (optional)

    Returns:
        pm.Attribute: A pymaya ``Attribute`` wrapper of the new attribute.
    """
    if isinstance(node, str):
        try:
            node = pm.PyNode(node)
        except pm.MayaNodeError:
            pm.displayError("{} doesn't exist or is not unique".format(node))
    if node.hasAttr(longName):
        mgear.log("Attribute already exists", mgear.sev_error)
        return

    data = {}

    if shortName is not None:
        data["shortName"] = shortName
    if niceName is not None:
        data["niceName"] = niceName
    if attributeType == "string":
        data["dataType"] = attributeType
    else:
        data["attributeType"] = attributeType

    if minValue is not None and minValue is not False:
        data["minValue"] = minValue
    if maxValue is not None and maxValue is not False:
        data["maxValue"] = maxValue

    if softMinValue is not None and softMinValue is not False:
        data["softMinValue"] = softMinValue
    if softMaxValue is not None and softMaxValue is not False:
        data["softMaxValue"] = softMaxValue

    data["keyable"] = keyable
    data["readable"] = readable
    data["storable"] = storable
    data["writable"] = writable

    if value is not None and attributeType not in ["string"]:
        data["defaultValue"] = value

    node.addAttr(longName, **data)

    if value is not None:
        node.setAttr(longName, value)

    if channelBox:
        node.attr(longName).set(channelBox=True)
    return node.attr(longName)


def addVector3Attribute(
    node,
    longName,
    value=False,
    keyable=True,
    readable=True,
    storable=True,
    writable=True,
    niceName=None,
    shortName=None,
    childLabels=["X", "Y", "Z"],
    usedAsColor=False,
    attributeType="float3",
):
    """
    Add a vector3 attribute to a node

    Arguments:
        node (dagNode): The object to add the new attribute.
        longName (str): The attribute name.
        value (list of flotat): The default value in a list for RGB.
            exp [1.0, 0.99, 0.13].
        keyable (bool): Set if the attribute is keyable or not. (optional)
        readable (bool): Set if the attribute is readable or not. (optional)
        storable (bool): Set if the attribute is storable or not. (optional)
        writable (bool): Set if the attribute is writable or not. (optional)
        niceName (str): The attribute nice name. (optional)
        shortName (str): The attribute short name. (optional)

    Returns:
        str: The long name of the new attribute

    """
    if node.hasAttr(longName):
        mgear.log("Attribute already exists", mgear.sev_error)
        return

    data = {}

    data["attributeType"] = attributeType
    if shortName is not None:
        data["shortName"] = shortName
    if niceName is not None:
        data["niceName"] = niceName

    data["usedAsColor"] = usedAsColor
    data["keyable"] = keyable
    data["readable"] = readable
    data["storable"] = storable
    data["writable"] = writable

    # child nested attr
    dataChild = {}
    dataChild["attributeType"] = "float"
    dataChild["parent"] = longName

    node.addAttr(longName, **data)
    node.addAttr(longName + childLabels[0], **dataChild)
    node.addAttr(longName + childLabels[1], **dataChild)
    node.addAttr(longName + childLabels[2], **dataChild)

    if value:
        node.setAttr(longName + childLabels[0], value[0])
        node.setAttr(longName + childLabels[1], value[1])
        node.setAttr(longName + childLabels[2], value[2])

    return node.attr(longName)


def addColorAttribute(
    node,
    longName,
    value=False,
    keyable=True,
    readable=True,
    storable=True,
    writable=True,
    niceName=None,
    shortName=None,
):
    """
    Add a color attribute to a node

    Arguments:
        node (dagNode): The object to add the new attribute.
        longName (str): The attribute name.
        value (list of flotat): The default value in a list for RGB.
            exp [1.0, 0.99, 0.13].
        keyable (bool): Set if the attribute is keyable or not. (optional)
        readable (bool): Set if the attribute is readable or not. (optional)
        storable (bool): Set if the attribute is storable or not. (optional)
        writable (bool): Set if the attribute is writable or not. (optional)
        niceName (str): The attribute nice name. (optional)
        shortName (str): The attribute short name. (optional)

    Returns:
        str: The long name of the new attribute

    """
    return addVector3Attribute(
        node,
        longName,
        value=value,
        keyable=keyable,
        readable=readable,
        storable=storable,
        writable=writable,
        niceName=niceName,
        shortName=shortName,
        childLabels=["_r", "_g", "_b"],
        usedAsColor=True,
    )


def addEnumAttribute(
    node,
    longName,
    value,
    enum,
    niceName=None,
    shortName=None,
    keyable=True,
    readable=True,
    storable=True,
    writable=True,
):
    """
    Add an enumerate attribute to a node

    Arguments:
        node (dagNode): The object to add the new attribute.
        longName (str): The attribute name.
        value (int): The default value.
        enum (list of str): The list of elements in the enumerate control
        niceName (str): The attribute nice name. (optional)
        shortName (str): The attribute short name. (optional)
        keyable (bool): Set if the attribute is keyable or not. (optional)
        readable (bool): Set if the attribute is readable or not. (optional)
        storable (bool): Set if the attribute is storable or not. (optional)
        writable (bool): Set if the attribute is writable or not. (optional)

    Returns:
        pm.Attribute: A pymaya ``Attribute`` wrapper of the new attribute.
    """

    if node.hasAttr(longName):
        mgear.log(
            "Attribute '" + longName + "' already exists", mgear.sev_warning
        )
        return

    data = {}

    if shortName is not None:
        data["shortName"] = shortName
    if niceName is not None:
        data["niceName"] = niceName

    data["attributeType"] = "enum"
    data["en"] = ":".join(enum)

    data["keyable"] = keyable
    data["readable"] = readable
    data["storable"] = storable
    data["writable"] = writable

    node.addAttr(longName, **data)
    node.setAttr(longName, value)

    return node.attr(longName)


def addProxyAttribute(sourceAttrs, targets, duplicatedPolicy=None):
    """Add proxy paramenter to a list of target dagNode
    Duplicated channel policy, stablish the rule in case the channel already
    exist on the target.

    Duplicate policy options

    ================    =======================================================
    index               This policy will add an index to avoid clashing channel
                        names
    fullName            This policy will add the name of the source object to
                        the channel
    merge               This policy will merge the channels
    ================    =======================================================

    Arguments:
        sourceAttrs (attr or list of attr): The parameters to be connected as
            proxy
        targets (dagNode or list of dagNode): The list of dagNode to add the
            proxy paramenter
        duplicatedPolicy (string, optional): Set the duplicated channel policy
    """
    if not isinstance(targets, list):
        targets = [targets]
    if not isinstance(sourceAttrs, list):
        sourceAttrs = [sourceAttrs]
    for sourceAttr in sourceAttrs:
        for target in targets:
            base_name = sourceAttr.longName()
            attrName = base_name
            if target.hasAttr(base_name):
                if duplicatedPolicy == "index":
                    # Cache existing attrs for faster lookup
                    target_name = target.name() if hasattr(target, 'name') else str(target)
                    existing_attrs = set(cmds.listAttr(target_name) or [])
                    i = 0
                    while f"{base_name}{i}" in existing_attrs:
                        i += 1
                    attrName = f"{base_name}{i}"
                elif duplicatedPolicy == "fullName":
                    attrName = f"{sourceAttr.nodeName()}_{base_name}"

            if not target.hasAttr(attrName):
                target.addAttr(attrName, pxy=sourceAttr)
            else:
                pm.displayWarning(
                    "The proxy channel %s already exist on: %s."
                    % (sourceAttr.longName(), target.name())
                )


def moveChannel(
    attr, sourceNode, targetNode, duplicatedPolicy=None, forceFullName=False
):
    """Move channels  keeping the output connections.
    Duplicated channel policy, stablish the rule in case the channel already
    exist on the target.

    NOTE: For the moment move channel only supports type double and enum

    Duplicate policy options

    ================    =======================================================
    index               This policy will add an index to avoid clashing channel
                        names
    fullName            This policy will add the name of the source object to
                        the channel
    merge               This policy will merge the channels
    ================    =======================================================

    Arguments:
        attr (str): Name of the channel to move
        sourceNode (PyNoe or str): The source node with the channel
        targetNode (PyNoe or str): The target node for the channel
        duplicatedPolicy (None, str): Set the duplicated channel policy
    """
    if isinstance(sourceNode, str) or isinstance(sourceNode, string_types):
        sourceNode = pm.PyNode(sourceNode)
    if isinstance(targetNode, str) or isinstance(targetNode, string_types):
        targetNode = pm.PyNode(targetNode)

    try:
        at = sourceNode.attr(attr)
        if pm.addAttr(at, q=True, usedAsProxy=True):
            pm.displayWarning(
                "{} is a proxy channel and move operation is "
                "not yet supported.".format(attr)
            )
            return
    except Exception:
        pm.displayWarning(
            "Looks like the {} is not in the"
            " source: {}".format(attr, sourceNode.name())
        )
        return
    atType = at.type()
    if atType in ["double", "float", "enum", "bool"]:

        newAtt = None
        attrName = attr
        nName = pm.attributeQuery(
            at.shortName(), node=at.node(), niceName=True
        )
        # define duplicated attribute policy
        if sourceNode.name() != targetNode.name():
            # this policy doesn't apply for rearrange channels
            if pm.attributeQuery(attr, node=targetNode, exists=True):
                if duplicatedPolicy == "index":
                    # Cache existing attrs for faster lookup
                    target_name = targetNode.name() if hasattr(targetNode, 'name') else str(targetNode)
                    existing_attrs = set(cmds.listAttr(target_name) or [])
                    i = 0
                    while f"{attr}{i}" in existing_attrs:
                        i += 1
                    attrName = f"{attr}{i}"
                elif duplicatedPolicy == "fullName":
                    attrName = f"{sourceNode.name()}_{attr}"

                elif duplicatedPolicy == "merge":
                    newAtt = pm.PyNode(".".join([targetNode.name(), attr]))

                else:
                    pm.displayWarning(
                        "Duplicated channel policy, is not "
                        "defined. Move channel operation will "
                        "fail if the channel already exist on "
                        "the target."
                    )
                    return False

        if forceFullName:
            attrName = "{}_{}".format(sourceNode.name(), attr)
            nName = "{}_{}".format(sourceNode.name(), nName)

        outcnx = at.listConnections(p=True)
        if not newAtt:
            # get the attr data
            value = at.get()
            if atType in ["double", "float"]:
                kwargs = {}
                min = at.getMin()
                if min:
                    kwargs["min"] = min
                max = at.getMax()
                if max:
                    kwargs["max"] = max
            elif atType == "enum":
                en = at.getEnums()
                oEn = collections.OrderedDict(
                    sorted(en.items(), key=lambda t: t[1])
                )
                enStr = ":".join([n for n in oEn])

            # delete old attr
            pm.deleteAttr(at)

            # rebuild the attr
            if atType in ["double", "float"]:
                pm.addAttr(
                    targetNode,
                    ln=attrName,
                    niceName=nName,
                    at=atType,
                    dv=value,
                    k=True,
                    **kwargs
                )
            elif atType == "enum":
                pm.addAttr(
                    targetNode,
                    ln=attrName,
                    niceName=nName,
                    at="enum",
                    en=enStr,
                    dv=value,
                    k=True,
                )
            elif atType == "bool":
                pm.addAttr(
                    targetNode,
                    longName=attrName,
                    niceName=nName,
                    attributeType="bool",
                    defaultValue=value,
                    keyable=True,
                )

            newAtt = pm.PyNode(".".join([targetNode.name(), attrName]))
        else:
            pm.deleteAttr(at)

        for cnx in outcnx:
            try:
                pm.connectAttr(newAtt, cnx, f=True)
                return newAtt
            except RuntimeError:
                pm.displayError(
                    "There is a problem connecting the "
                    "channel %s  maybe is already move? Please "
                    "check your configuration" % newAtt.name()
                )

    else:
        pm.displayWarning(
            "MoveChannel function can't handle an attribute "
            "of type: %s. Only supported 'double' adn 'enum' "
            "types." % atType
        )


def lockAttribute(
    node,
    attributes=["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"],
):
    """Lock attributes of a node.

    By defaul will lock the rotation, scale and translation.

    Arguments:
        node(dagNode): The node with the attributes to lock.
        attributes (list of str): The list of the attributes to lock.

    Example:
        >>> att.lockAttribute(self.root_ctl, ["sx", "sy", "sz", "v"])

    """
    _lockUnlockAttribute(node, attributes, lock=True, keyable=False)


def unlockAttribute(
    node,
    attributes=["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "v"],
):
    """Unlock attributes of a node.

    By defaul will unlock the rotation, scale and translation.

    Arguments:
        node(dagNode): The node with the attributes to unlock.
        attributes (list of str): The list of the attributes to unlock.

    Example:
        >>> att.unlockAttribute(self.root_ctl, ["sx", "sy", "sz", "v"])

    """
    _lockUnlockAttribute(node, attributes, lock=False, keyable=True)


def _lockUnlockAttribute(node, attributes, lock, keyable):
    """Lock or unlock attributes of a node.

    Arguments:
        node(dagNode): The node with the attributes to lock/unlock.
        attributes (list of str): The list of the attributes to lock/unlock.

    """
    if not isinstance(attributes, list):
        attributes = [attributes]

    for attr_name in attributes:
        node.setAttr(attr_name, lock=lock, keyable=keyable)


def setKeyableAttributes(
    nodes, params=["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"]
):
    """Set keyable attributes of a node.

    By defaul will set keyable the rotation, scale and translation.

    Arguments:
        node(dagNode): The node with the attributes to set keyable.
        attributes (list of str): The list of the attributes to set keyable.
            Attrs not in the list will be locked
            if None, ["tx", "ty", "tz", "rorder", "rx", "ry", "rz", "sx", "sy",
                "sz"] is used

    """

    localParams = {"tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz", "v"}

    if not isinstance(nodes, list):
        nodes = [nodes]

    # Convert params to set for O(1) lookup
    params_set = set(params)
    # Pre-compute which attrs to lock (those in localParams but not in params)
    attrs_to_lock = localParams - params_set

    # Use cmds for faster attribute setting
    for node in nodes:
        node_name = node.name() if hasattr(node, "name") else str(node)
        for attr_name in params:
            cmds.setAttr(f"{node_name}.{attr_name}", lock=False, keyable=True)
        for attr_name in attrs_to_lock:
            cmds.setAttr(f"{node_name}.{attr_name}", lock=True, keyable=False)


def setNotKeyableAttributes(
    nodes,
    attributes=[
        "tx",
        "ty",
        "tz",
        "ro",
        "rx",
        "ry",
        "rz",
        "sx",
        "sy",
        "sz",
        "v",
    ],
):
    """Set not keyable attributes of a node.

    By defaul will set not keyable the rotation, scale and translation.

    Arguments:
        node(dagNode): The node with the attributes to set keyable.
        attributes (list of str): The list of the attributes to set not keyable
    """

    if not isinstance(nodes, list):
        nodes = [nodes]

    # Use cmds for faster attribute setting
    for node in nodes:
        node_name = node.name() if hasattr(node, 'name') else str(node)
        for attr_name in attributes:
            cmds.setAttr(f"{node_name}.{attr_name}", lock=False, keyable=False, cb=True)


# Rotation order lookup dictionary for O(1) access
_ROT_ORDER_MAP = {
    "XYZ": OpenMaya.MEulerRotation.kXYZ,
    "YZX": OpenMaya.MEulerRotation.kYZX,
    "ZXY": OpenMaya.MEulerRotation.kZXY,
    "XZY": OpenMaya.MEulerRotation.kXZY,
    "YXZ": OpenMaya.MEulerRotation.kYXZ,
    "ZYX": OpenMaya.MEulerRotation.kZYX,
}


def _to_rot_od(ordstr):
    return _ROT_ORDER_MAP.get(ordstr, OpenMaya.MEulerRotation.kXYZ)


def setRotOrder(node, s="XYZ"):
    """Set the rotorder of the object.

    Arguments:
        node (dagNode): The object to set the rot order on.
        s (str): Value of the rotorder.
            Possible values : ("XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX")
    """

    a = ["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"]

    if s not in a:
        mgear.log("Invalid Rotorder : " + s, mgear.sev_error)
        return False

    # Unless Softimage there is no event on the rotorder parameter to
    # automatically adapt the angle values
    # So let's do it manually using the EulerRotation class

    er = datatypes.EulerRotation(
        [
            OpenMaya.MAngle(
                pm.getAttr(node + ".rx"), OpenMaya.MAngle.kDegrees
            ).asRadians(),
            OpenMaya.MAngle(
                pm.getAttr(node + ".ry"), OpenMaya.MAngle.kDegrees
            ).asRadians(),
            OpenMaya.MAngle(
                pm.getAttr(node + ".rz"), OpenMaya.MAngle.kDegrees
            ).asRadians(),
        ],
        _to_rot_od(a[node.getAttr("ro")]),
    )
    er.reorderIt(_to_rot_od(s))

    if node.hasAttr("rotate_order"):
        change_default_value(node.rotate_order, a.index(s))

    node.setAttr("ro", a.index(s))
    node.setAttr(
        "rotate",
        OpenMaya.MAngle(er.x).asDegrees(),
        OpenMaya.MAngle(er.y).asDegrees(),
        OpenMaya.MAngle(er.z).asDegrees(),
    )


def setInvertMirror(node, invList=None):
    """Set invert mirror pose values

    Arguments:
        node (dagNode): The object to set invert mirror Values
        invList (list, optional): list of axis to invert ["tx", "tz"]

    i.e: attribute.setInvertMirror(ctl_pyNode, invList=["tx", "tz"] )


    """

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

    for axis in invList:
        if axis not in aDic:
            mgear.log("Invalid Invert Axis : " + axis, mgear.sev_error)
            return False

        node.setAttr(aDic[axis], True)


def addFCurve(node, name="fcurve", keys=[]):
    """FCurve attribute

    Just a animCurveUU node connected to an attribute

    Warning:
        This Method is deprecated.

    Arguments:
        node (dagNode): The object to add the new fcurve attribute
        name (str): The attribute name
        key (list): list of keyframes and values

    Returns:
        Fcurve and attribute name

    """
    attr_name = addAttribute(node, name, "double", 0)
    attrDummy_name = addAttribute(node, name + "_dummy", "double", 0)

    for key in keys:
        # we use setDrivenKeyframe, because is the only workaround that I found
        # to create an animCurveUU with keyframes
        pm.setDrivenKeyframe(
            attr_name,
            cd=attrDummy_name,
            dv=key[0],
            v=key[1],
            itt=key[2],
            ott=key[2],
        )

    # clean dummy attr
    pm.deleteAttr(attrDummy_name)

    fCurve = pm.PyNode(attr_name).listConnections(type="animCurveUU")[0]

    return fCurve, attr_name


def connect_add_dynamic_pivot(pivots, driven):
    """connect dynamic pivot with option to add offset channels on XYZ

    Args:
        pivot (dagNode list): pivot translation
        driven (dagNode list): Driven object
    """
    if not isinstance(pivots, list):
        pivots = [pivots]
    node = pm.createNode("plusMinusAverage")
    node.attr("operation").set(1)
    for i, p in enumerate(pivots):
        pm.connectAttr(p.t, node + ".input3D[%s]" % str(i))
    if not isinstance(driven, list):
        driven = [driven]
    for d in driven:
        pm.connectAttr(node + ".output3D", d.rotatePivot)
        pm.connectAttr(node + ".output3D", d.scalePivot)


def connect_dynamic_pivot(pivot, driven):
    """connects translation of pivot dagNode to rotatePivot and scalePivot
    of the driven transform

    Args:
        pivot (dagNode): pivot translation
        driven (dagNode): Driven object
    """
    pivot.t >> driven.rotatePivot
    pivot.t >> driven.scalePivot


def move_input_connections(source, target, type_filter=None):
    """Move the input connections from source node to target node.
    The connections can be filtered by type of the incoming node

     exp: attribute.move_input_connections(
                        cns_obj, cns_off, type_filter="parentConstraint"
                    )

    Args:
        source (PyNode): node with input connection
        target (PyNode): target to receive the input connections
        type_filter (None, str): node type to filter connections list
    """
    kwargs = dict(c=True, p=True, d=False)
    if type_filter:
        kwargs["type"] = type_filter

    inputs = source.listConnections(**kwargs)
    for i in inputs:
        at_name = i[0].shortName()
        pm.disconnectAttr(i[0])
        pm.setAttr(i[0], lock=False, keyable=True)
        pm.connectAttr(i[1], target.attr(at_name))


def move_output_connections(source, target, type_filter=None):
    """Move the output connections from source node to target node.
    The connections can be filtered by type of the outgoing node

     exp: attribute.move_output_connections(
                        cns_obj, cns_off, type_filter="parentConstraint"
                    )

    Args:
        source (PyNode): node with output connection
        target (PyNode): target to receive the input connections
        type_filter (None, str): node type to filter connections list
    """
    kwargs = dict(c=True, p=True, s=False)
    if type_filter:
        kwargs["type"] = type_filter

    outputs = source.listConnections(**kwargs)
    for i in outputs:
        at_name = i[0].shortName()
        pm.disconnectAttr(i[0])
        pm.connectAttr(target.attr(at_name), i[1])


def get_attr_info(node, attr):
    """
    Returns default, min, and max values of an attribute.

    Args:
        node (str): Node name, e.g. "control_C1_ctl"
        attr (str): Attribute name, e.g. "arm_slide"

    Returns:
        dict: { "default": value or None,
                "min": value or None,
                "max": value or None }
    """
    info = {"default": None, "min": None, "max": None}

    # Default
    default = cmds.attributeQuery(attr, node=node, listDefault=True)
    if default:
        info["default"] = default[0]

    # Min
    minimum = cmds.attributeQuery(attr, node=node, minimum=True)
    if minimum:
        info["min"] = minimum[0]

    # Max
    maximum = cmds.attributeQuery(attr, node=node, maximum=True)
    if maximum:
        info["max"] = maximum[0]

    return info


##########################################################
# PARAMETER DEFINITION
##########################################################


class ParamDef(object):
    """ParamDef (read as Parameter Definition)

    Encapsulate the attribute creation arguments in a handy object.
    Also include a creation method.

    Example:
        This can be use later to create attr or export the description to xml
        or json file

     Arguments:
        scriptName (str): Attribute fullName
        paranDef (dic): The stored param definition

    """

    def __init__(self, scriptName):

        self.scriptName = scriptName
        self.value = None
        self.valueType = None
        self.param_dict = {}

    def create(self, node):
        """Add a parameter to property using the parameter definition.

        Arguments:
            node (dagNode): The node to add the attribute
        """
        attr_name = addAttribute(
            node,
            self.scriptName,
            self.valueType,
            self.value,
            self.niceName,
            self.shortName,
            self.minimum,
            self.maximum,
            self.keyable,
            self.readable,
            self.storable,
            self.writable,
        )

        return node, attr_name

    def get_as_dict(self):

        self.param_dict["scriptName"] = self.scriptName
        self.param_dict["valueType"] = self.valueType
        self.param_dict["value"] = self.value
        self.param_dict["niceName"] = self.niceName
        self.param_dict["shortName"] = self.shortName
        self.param_dict["minimum"] = self.minimum
        self.param_dict["maximum"] = self.maximum
        self.param_dict["keyable"] = self.keyable
        self.param_dict["readable"] = self.readable
        self.param_dict["storable"] = self.storable
        self.param_dict["writable"] = self.writable

        return self.param_dict

    def set_from_dict(self, param_dict):

        self.scriptName = param_dict["scriptName"]
        self.valueType = param_dict["valueType"]
        self.value = param_dict["value"]
        self.niceName = param_dict["niceName"]
        self.shortName = param_dict["shortName"]
        self.minimum = param_dict["minimum"]
        self.maximum = param_dict["maximum"]
        self.keyable = param_dict["keyable"]
        self.readable = param_dict["readable"]
        self.storable = param_dict["storable"]
        self.writable = param_dict["writable"]


class ParamDef2(ParamDef):
    """ParamDef2 inherit from ParamDef

    Arguments:
        scriptName (str): Parameter scriptname.
        valueType (str): The Attribute Type. Exp: 'string', 'bool',
            'long', etc..
        value (float or int): Default parameter value.
        niceName (str): Parameter niceName.
        shortName (str): Parameter shortName.
        minimum (float or int): mininum value.
        maximum (float or int): maximum value.
        keyable (boo): If true is keyable
        readable (boo): If true is readable
        storable (boo): If true is storable
        writable (boo): If true is writable

    Returns:
        ParamDef: The stored parameter definition.

    """

    def __init__(
        self,
        scriptName,
        valueType,
        value,
        niceName=None,
        shortName=None,
        minimum=None,
        maximum=None,
        keyable=True,
        readable=True,
        storable=True,
        writable=True,
    ):

        self.scriptName = scriptName
        self.niceName = niceName
        self.shortName = shortName
        self.valueType = valueType
        self.value = value
        self.minimum = minimum
        self.maximum = maximum
        self.keyable = keyable
        self.readable = readable
        self.storable = storable
        self.writable = writable
        self.param_dict = {}


class FCurveParamDef(ParamDef):
    """Create an Fcurve parameter definition.

    Arguments:
        scriptName (str): Attribute fullName.
        keys (list): The keyframes to define the function curve.
        interpolation (int): the curve interpolation.
        extrapolation (int): the curve extrapolation.

    """

    def __init__(
        self, scriptName, keys=None, interpolation=0, extrapolation=0
    ):

        self.scriptName = scriptName
        self.keys = keys
        self.interpolation = interpolation
        self.extrapolation = extrapolation
        self.value = None
        self.valueType = None
        self.param_dict = {}

    def create(self, node):
        """Add a parameter to property using the parameter definition.

        Arguments:
            node (dagNode): The node to add the attribute

        """
        attr_name = addAttribute(node, self.scriptName, "double", 0)

        attrDummy_name = addAttribute(
            node, self.scriptName + "_dummy", "double", 0
        )

        for key in self.keys:
            pm.setDrivenKeyframe(
                attr_name, cd=attrDummy_name, dv=key[0], v=key[1]
            )

        # clean dummy attr
        pm.deleteAttr(attrDummy_name)

        return node, attr_name

    def get_as_dict(self):

        self.param_dict["scriptName"] = self.scriptName
        self.param_dict["keys"] = self.keys
        self.param_dict["interpolation"] = self.interpolation
        self.param_dict["extrapolation"] = self.extrapolation
        self.param_dict["value"] = self.value
        self.param_dict["valueType"] = self.valueType

        return self.param_dict

    def set_from_dict(self, param_dict):

        self.scriptName = param_dict["scriptName"]
        self.keys = param_dict["keys"]
        self.interpolation = param_dict["interpolation"]
        self.extrapolation = param_dict["extrapolation"]
        self.value = param_dict["value"]
        self.valueType = param_dict["valueType"]


class colorParamDef(ParamDef):
    """Create a Color parameter definition.

    Arguments:
        scriptName (str): Attribute fullName
        value (list of float): The default value in a list for RGB.
            exp [1.0, 0.99, 0.13].

    """

    def __init__(self, scriptName, value=False):

        self.scriptName = scriptName
        self.value = value
        self.valueType = None
        self.param_dict = {}

    def create(self, node):
        """Add a parameter to property using the parameter definition.

        Arguments:
            node (dagNode): The node to add the attribute

        """
        attr_name = addColorAttribute(node, self.scriptName, value=self.value)

        return node, attr_name

    def get_as_dict(self):

        self.param_dict["scriptName"] = self.scriptName
        if isinstance(self.value, OpenMaya.MVector):
            self.value = [self.value.x, self.value.y, self.value.z]
        self.param_dict["value"] = self.value

        return self.param_dict

    def set_from_dict(self, param_dict):

        self.scriptName = param_dict["scriptName"]
        self.value = param_dict["value"]


class enumParamDef(ParamDef):
    """Create an enumarator parameter definition.

    Arguments:
        scriptName (str): Attribute fullName
        enum (list of str): The list of elements in the enumerate control.
        value (int): The default value.

    """

    def __init__(self, scriptName, enum, value=False):

        self.scriptName = scriptName
        self.value = value
        self.enum = enum
        self.valueType = None
        self.param_dict = {}

    def create(self, node):
        """Add a parameter to property using the parameter definition.

        Arguments:
            node (dagNode): The node to add the attribute

        """
        attr_name = addEnumAttribute(
            node, self.scriptName, enum=self.enum, value=self.value
        )

        return node, attr_name

    def get_as_dict(self):

        self.param_dict["scriptName"] = self.scriptName
        self.param_dict["value"] = self.value
        self.param_dict["enum"] = self.enum
        self.param_dict["valueType"] = self.valueType

        return self.param_dict

    def set_from_dict(self, param_dict):

        self.scriptName = param_dict["scriptName"]
        self.value = param_dict["value"]
        self.enum = param_dict["enum"]
        self.valueType = param_dict["valueType"]


##########################################################
# Default Values functions
##########################################################


def get_default_value(node, attribute):
    """Get the default attribute value

    Args:
        node (str, PyNode): The object with the attribute
        attribute (str): The attribute to get the value

    Returns:
        variant: The attribute value
    """
    return pm.attributeQuery(attribute, node=node, listDefault=True)[0]


def set_default_value(node, attribute):
    """Set the default value to the attribute

    Args:
        node (str, PyNode): The object with the attribute to reset
        attribute (str): The attribute to reset
    """
    if isinstance(node, string_types):
        node = pm.PyNode(node)

    defVal = get_default_value(node, attribute)
    try:
        if attribute in ["ro", "rotateOrder"]:
            # custom metadata rot order attr
            rotOrder = "rotate_order"
            if pm.attributeQuery(rotOrder, node=node, exists=True):
                # print(
                #     "Resetting rotate Order for {} using custom metadata".format(
                #         node
                #     )
                # )
                intNum = pm.getAttr("{}.{}".format(node, rotOrder))
                if not pm.getAttr("{}.rotateOrder".format(node), lock=True):
                    pm.setAttr("{}.rotateOrder".format(node), intNum)
            else:
                pm.displayInfo(
                    "No custom rotate order metadata found in {}. XYZ rotate order NOT reset".format(
                        node
                    )
                )
                # node.attr(attribute).set(defVal)
        else:
            node.attr(attribute).set(defVal)
    except (RuntimeError, pm.MayaAttributeError):
        # print("Failed to reset: {}".format(attribute))
        pass


def change_default_value(attributes, defaultValue):
    """Change the default value of the attr

    Args:
        attributes (list or str or pynode): attributes to change the default val
        defaultValue (numeric value): defaul value. Only numeric values are valid
    """
    if not isinstance(attributes, list):
        attributes = [attributes]
    for at in attributes:
        pm.addAttr(at, e=True, defaultValue=defaultValue)
        pm.setAttr(at, defaultValue)


def reset_selected_channels_value(objects=None, attributes=None):
    """Reset the the selected channels if not attribute is provided

    Args:
        objects (None, optional): The objects to reset the channels
        attribute (list, optional): The attribute to reset
    """
    if not objects:
        objects = cmds.ls(selection=True)
    if not attributes:
        attributes = getSelectedChannels()

    for obj in objects:
        for attr in attributes:
            set_default_value(obj, attr)


def reset_SRT(
    objects=None,
    attributes=[
        "tx",
        "ty",
        "tz",
        "rx",
        "ry",
        "rz",
        "sx",
        "sy",
        "sz",
        "v",
        "ro",
    ],
):
    """Reset Scale Rotation and translation attributes to default value

    Args:
        objects (None, optional): The objects to reset the channels
        attribute (list): The attribute to reset
    """
    reset_selected_channels_value(objects, attributes)


def smart_reset(*args):
    """Reset the SRT or the selected channels

    Checks first if we have channels selected. If not, will try to reset SRT

    Args:
        *args: Dummy
    """
    attributes = getSelectedChannels()
    if attributes:
        reset_selected_channels_value(objects=None, attributes=attributes)
    else:
        reset_SRT()


##########################################################
# GETTERS
##########################################################


def get_channelBox():
    """Get the channel box

    Returns:
        str: channel box path
    """
    mel_str = "global string $gChannelBoxName; $temp=$gChannelBoxName;"
    channelBox = pm.mel.eval(mel_str)
    return channelBox


def collect_attrs(node, attrs, attrs_list, shapes=False):
    """Collect the channel full path in a list.

    Checks that the channel is not repeated.

    Args:
        node (PyNode): Node that owns the channels
        attrs (str): the list to add the channels full path
        attrs_list (list): the list of channels names
        shapes (bool, optional): If True will search the attr only in shapes
    """
    if attrs_list:
        for at in attrs_list:
            if shapes:
                try:
                    shapes_nodes = node.getShapes()
                except AttributeError:
                    pm.displayWarning(
                        "Something whent wrong. Looks like {} "
                        "don,t have shapes. Please clear "
                        "selection and try "
                        "again".format(node.name())
                    )
                    return
                for sh in shapes_nodes:
                    if sh.hasAttr(at):
                        full_attr_path = "{0}.{1}".format(sh, at)

                        # if multiple shapes have same att will add all
                        if full_attr_path not in attrs:
                            attrs.append(full_attr_path)

            elif node.hasAttr(at):
                full_attr_path = "{0}.{1}".format(node, at)

                if full_attr_path not in attrs:
                    attrs.append(full_attr_path)


def get_selected_channels_full_path():
    """Get the selected channels full path from channel box
    This function will collect channels from any area of the channel box. This
    include, Main, shape, input and output

    Returns:
        list: list of channels full path
    """
    attrs = []
    node = pm.ls(sl=True)
    if node:
        node = node[0]

        collect_attrs(
            node, attrs, pm.channelBox(get_channelBox(), q=True, sma=True)
        )

        # if the attr is from shape node, we need to search in all shapes
        collect_attrs(
            node,
            attrs,
            pm.channelBox(get_channelBox(), q=True, ssa=True),
            shapes=True,
        )

        collect_attrs(
            node, attrs, pm.channelBox(get_channelBox(), q=True, sha=True)
        )
        collect_attrs(
            node, attrs, pm.channelBox(get_channelBox(), q=True, soa=True)
        )

    return attrs


def getSelectedChannels(userDefine=False):
    """Get the selected channels on the channel box

    Arguments:
        userDefine (bool, optional): If True, will return only the user
            defined channels. Other channels will be skipped.

    Returns:
        list: The list of selected channels names

    """
    # fetch core's main channelbox
    attrs = pm.channelBox(get_channelBox(), q=True, sma=True) or []
    if userDefine:
        oSel = pm.selected()[0]
        uda = oSel.listAttr(ud=True)
        if attrs:
            attrs = [x for x in attrs if oSel.attr(x) in uda]
        else:
            return []

    return attrs


def getSelectedObjectChannels(oSel=None, userDefine=False, animatable=False):
    """Get the selected object channels.

    Arguments:
        oSel (None, optional): The  pynode with channels to get
        userDefine (bool, optional): If True, will return only the user
            defined channels. Other channels will be skipped.
        animatable (bool, optional): If True, only animatable parameters
            will be return

    Returns:
        list: The list of the selected object channels names
    """
    if not oSel:
        oSel = pm.selected()[0]

    channels = [
        x.name().rsplit(".", 1)[1]
        for x in oSel.listAttr(ud=userDefine, k=animatable)
    ]

    return channels


def has_in_connections(
    node,
    attributes=[
        "translate",
        "tx",
        "ty",
        "tz",
        "rotate",
        "rx",
        "ry",
        "rz",
        "scale",
        "sx",
        "sy",
        "sz",
    ],
):
    """
    Checks if the provided node has any input connections on the specified attributes.

    Args:
        node (PyNode): The PyNode object for which to check connections.
        attributes (list, optional): A list of attributes to check for connections.
                    Defaults to checking all translation,
        rotation, and scale attributes in all directions.

    Returns:
        bool: True if any connections are found, False otherwise.

    Examples:
        >>> jnt = pm.PyNode('myJoint')
        >>> has_connections(jnt)
        Found some connections.
        >>> has_connections(jnt, ['visibility'])
        No connections found.
    """

    for attr in attributes:
        if node.attr(attr).listConnections(d=False):
            return True
    return False


def disconnect_inputs(
    node,
    attributes=[
        "scale",
        "sx",
        "sy",
        "sz",
        "translate",
        "tx",
        "ty",
        "tz",
        "rotate",
        "rx",
        "ry",
        "rz",
    ],
):
    """
    Disconnects only the input connections of the specified attributes of
    the provided node.

    Args:
        node (PyNode): The PyNode object for which to disconnect input
        connections.
        attributes (list, optional): A list of attributes to disconnect
        input connections from. Defaults to disconnecting all translation,
        rotation, and scale attributes in all directions.
    """
    for attr in attributes:
        connections = node.attr(attr).listConnections(d=False, plugs=True)
        for conn in connections:
            pm.disconnectAttr(conn, node.attr(attr))


def disconnect_outputs(
    node,
    attributes=[
        "scale",
        "sx",
        "sy",
        "sz",
        "translate",
        "tx",
        "ty",
        "tz",
        "rotate",
        "rx",
        "ry",
        "rz",
    ],
):
    """
    Disconnects only the output connections of the specified attributes of
    the provided node.

    Args:
        node (PyNode): The PyNode object for which to disconnect output
        connections.
        attributes (list, optional): A list of attributes to disconnect
        output connections from. Defaults to disconnecting all translation,
        rotation, and scale attributes in all directions.
    """

    for attr in attributes:
        connections = node.attr(attr).listConnections(plugs=True)
        for conn in connections:
            pm.disconnectAttr(node.attr(attr), conn)


##########################################################
# UTIL
##########################################################


def connectSet(source, target, testInstance):
    """Connect or set attributes

    Connects or set attributes depending if is instance of a instance check

    Args:
        source (str or Attr): Striname of the attribute or PyNode attribute
        target (str or Attr): Striname of the attribute or PyNode attribute
        testInstance (tuple): Tuple of types to check
    """
    if not isinstance(testInstance, tuple):
        testInstance = tuple(testInstance)

    if isinstance(source, testInstance):
        pm.connectAttr(source, target)
    else:
        pm.setAttr(target, source)


def get_next_available_index(attr):
    """get the next available index from a multi attr
    This function is a workaround because the connect attr flag next available
    is not working.

    The connectAttr to the children attribute is giving error
        i.e: pm.connectAttr(ctt.attr("parent"),
                             tpTagNode.attr("children"), na=True)
        if using the next available option flag
        I was expecting to use ctt.setParent(tagParent) but doest't work as
        expected.
        After reading the documentation this method looks prety
        useless.
        Looks like is boolean and works based on selection :(

    Args:
        attr (attr): Attr multi

    Returns:
        int: index
    """

    ne = attr.getNumElements()
    if ne == attr.numConnectedElements():
        return ne
    else:
        for e in range(ne):
            if not attr.attr(attr.elements()[e]).listConnections():
                return e


def find_next_available_index(node, attribute):
    """Find the next available index for a multi-attribute on a given node.
    This function ins similar to get_next_available_index but with 2 args

    Args:
        node (PyNode): Node with multi-attribute.
        attribute (str): Multi-attribute name.

    Returns:
        int: Next available index.
    """
    idx = 0
    while node.attr(attribute)[idx].isConnected():
        idx += 1
    return idx


def connect_message(source, attr):
    """
    Connects the 'message' attribute of one or more source nodes to a
    destination attribute.

    Args:
        source (str, pm.PyNode, list): The source node(s) with a 'message'
                                       attribute.
        attr (str, pm.PyNode): The destination attribute to connect to.

    Raises:
        TypeError: If the destination attribute is not a message attribute.
    """
    if not isinstance(source, list):
        source = [source]

    for src in source:
        idx = get_next_available_index(attr)
        attr_name = "{}[{}]".format(attr, idx)

        src_str = src if isinstance(src, str) else str(src)
        attr_str = attr if isinstance(attr, str) else str(attr)

        source_attr_type = pm.attributeQuery(
            "message", node=src_str.split(".")[0], attributeType=True
        )
        dest_attr_type = pm.attributeQuery(
            attr_str.split("[")[0].split(".")[-1],
            node=attr_str.split(".")[0],
            attributeType=True,
        )

        if source_attr_type != "message":
            raise TypeError("Source attribute is not a message attribute.")

        if dest_attr_type != "message":
            raise TypeError(
                "Destination attribute is not a message attribute."
            )

        pm.connectAttr("{}.message".format(src_str), attr_name)


def resolve_alias_attr(full_attr_name):
    """
    Resolves the real name of an attribute if it is an alias.

    Args:
        full_attr_name (str): The fully qualified alias attribute name (e.g., "blendShape1.pCube1").

    Returns:
        str: The real attribute name if it's an alias, or the original name if not.
    """
    # Split the full attribute into node and alias attribute
    if "." not in full_attr_name:
        raise ValueError(
            "Input must be a fully qualified attribute (e.g., 'node.attr')"
        )

    node, alias_attr = full_attr_name.split(".", 1)

    # Get all aliases for the node
    aliases = cmds.aliasAttr(node, query=True) or []

    # aliases is a flat list: [alias1, realAttr1, alias2, realAttr2, ...]
    alias_dict = dict(zip(aliases[::2], aliases[1::2]))

    # Check if the alias_attr is in the alias list
    if alias_attr in alias_dict:
        real_attr = "{}.{}".format(node, alias_dict[alias_attr])
        return real_attr  # Return the fully qualified real attribute name
    else:
        return full_attr_name  # Not an alias, return as is


def get_alias_for_attr(full_attr_name):
    """
    Gets the alias name for a real attribute, if it exists.

    Args:
        full_attr_name (str): The fully qualified real attribute name
            (e.g., "blendShape1.weight[0]").

    Returns:
        str: The alias name if it exists, or the original name if no alias exists.
    """
    # Split the full attribute into node and real attribute
    if "." not in full_attr_name:
        raise ValueError(
            "Input must be a fully qualified attribute (e.g., 'node.attr')"
        )

    node, real_attr = full_attr_name.split(".", 1)

    # Get all aliases for the node
    aliases = cmds.aliasAttr(node, query=True) or []

    # aliases is a flat list: [alias1, realAttr1, alias2, realAttr2, ...]
    alias_dict = dict(zip(aliases[1::2], aliases[::2]))  # Reverse mapping

    # Check if the real_attr is in the alias dictionary
    if real_attr in alias_dict:
        alias_attr = "{}.{}".format(node, alias_dict[real_attr])
        return alias_attr  # Return the fully qualified alias name
    else:
        return full_attr_name  # No alias exists, return as is


##########################################################
# Utility Channels
##########################################################


def add_mirror_config_channels(ctl, conf=(0, 0, 0, 0, 0, 0, 0, 0, 0)):
    """Add channels to configure the mirror posing

    Args:
     ctl (dagNode): Control Object
    """
    addAttribute(
        ctl,
        "invTx",
        "bool",
        conf[0],
        keyable=False,
        niceName="Invert Mirror TX",
    )
    addAttribute(
        ctl,
        "invTy",
        "bool",
        conf[1],
        keyable=False,
        niceName="Invert Mirror TY",
    )
    addAttribute(
        ctl,
        "invTz",
        "bool",
        conf[2],
        keyable=False,
        niceName="Invert Mirror TZ",
    )
    addAttribute(
        ctl,
        "invRx",
        "bool",
        conf[3],
        keyable=False,
        niceName="Invert Mirror RX",
    )
    addAttribute(
        ctl,
        "invRy",
        "bool",
        conf[4],
        keyable=False,
        niceName="Invert Mirror RY",
    )
    addAttribute(
        ctl,
        "invRz",
        "bool",
        conf[5],
        keyable=False,
        niceName="Invert Mirror RZ",
    )
    addAttribute(
        ctl,
        "invSx",
        "bool",
        conf[6],
        keyable=False,
        niceName="Invert Mirror SX",
    )
    addAttribute(
        ctl,
        "invSy",
        "bool",
        conf[7],
        keyable=False,
        niceName="Invert Mirror SY",
    )
    addAttribute(
        ctl,
        "invSz",
        "bool",
        conf[8],
        keyable=False,
        niceName="Invert Mirror SZ",
    )


def toggle_bool_attr(attr):
    if attr.get():
        attr.set(False)
    else:
        attr.set(True)
