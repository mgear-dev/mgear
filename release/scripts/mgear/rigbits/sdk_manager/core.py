__author__ = "Justin Pedersen"
__email__ = "Justin@tcgcape.co.za"

import mgear.pymaya as pm
import mgear.rigbits.sdk_io as sdk_io
import mgear.core.pickWalk as pickWalk

SDK_ANIMCURVES_TYPE = ("animCurveUA", "animCurveUL", "animCurveUU")

# reload(sdk_io)

# ================================================= #
# MATH
# ================================================= #


def next_biggest(target, in_list):
    """
    Returns the next highest number in the in_list.
    If target is greater the the last number in in_list, will return the last
    item in the list.
    """
    next_highest = None
    for item in in_list:
        if item > target:
            next_highest = item
            break

    if next_highest is None:
        next_highest = in_list[-1]
    return next_highest


def next_smallest(target, in_list):
    """
    Returns the next Lowest number in the in_list.
    If target is smaller the the last number in in_list, will return the first
    item in the list.
    """
    next_lowest = None
    for item in in_list[::-1]:
        if item < target:
            next_lowest = item
            break

    if next_lowest is None:
        next_lowest = in_list[0]
    return next_lowest


# ================================================= #
# SELECTION
# ================================================= #


def select_all(mode):
    """
    Select all the Driver Ctls, Anim Ctls
    Joints or SDK Nodes in the scene.

    Arguments:
        mode (str) - drv : Driver Ctls
                   - anim : Anim Ctls
                   - jnts : Joints
                   - nodes : SDK Nodes

    Returns:
        None

    """
    pm.select(clear=True)

    # Driver Ctl and Anim Ctl mode
    if mode == "drv" or mode == "anim":
        # Setting the Attr to look for on nodes.
        attr = "is_SDK" if mode == "drv" else "is_tweak"

        for item in pm.ls("*." + attr):
            if "controlBuffer" not in item.name():
                pm.select(item.split(".")[0], add=True)

    # Joints Mode
    elif mode == "jnts":
        all_joints = []
        for item in pm.ls("*.is_tweak"):
            if "controlBuffer" not in item.name():
                jnt = joint_from_driver_ctl(item.node())
                if jnt not in all_joints:
                    all_joints.append(jnt)
        pm.select(all_joints, replace=True)

    # Node Mode
    elif mode == "nodes":
        str_sdk_nodes = []
        for item in pm.ls("*.is_SDK"):
            if "controlBuffer" not in item.name():
                sdk_info = sdk_io.getAllSDKInfoFromNode(item.node())
                str_sdk_nodes.extend(sdk_info.keys())

        sdk_nodes = sdk_io.getPynodes(str_sdk_nodes)
        pm.select(sdk_nodes, replace=True)


def reset_to_default(mode, clear_sel=False):
    """
    Reset All the Rig Driver Ctls or Anim Ctls to Default

    Arguments:
        mode (str) - all : All Ctl Curves
                   - drv : Driver Ctls
                   - anim : Anim Ctls

    Returns:
        None
    """
    attrs_dict = {
        "tx": 0,
        "ty": 0,
        "tz": 0,
        "rx": 0,
        "ry": 0,
        "rz": 0,
        "sx": 1,
        "sy": 1,
        "sz": 1,
    }

    # All Ctls Mode
    if mode == "all":
        for attrib in pm.ls("*.invTx"):
            node = attrib.node()
            if "controlBuffer" not in node.name():
                for attr, value in attrs_dict.items():
                    # If the Attr is settable, set it
                    if pm.getAttr(node.attr(attr), settable=True):
                        pm.setAttr(node.attr(attr), value)

    # Driver Ctls and Anim Ctls
    elif mode == "drv" or "anim":
        select_all(mode)
        for item in pm.ls(sl=True):
            for attr, value in attrs_dict.items():
                pm.setAttr(item.attr(attr), value)

    if clear_sel:
        pm.select(clear=True)


# ================================================= #
# NAVIGATION
# ================================================= #


def driver_ctl_from_joint(joint):
    """
    Will try find the Driver control given the joint by searching through the
    mGear nodes.

    Arguments:
        joint (PyNode): joint to search connections on

    Returns:
        PyNode : Control
    """
    driver_control = None

    if pm.nodeType(joint) == "joint":
        for connected in pm.listConnections(joint.translateX, source=True):
            if pm.nodeType(connected) == "decomposeMatrix":
                for conB in pm.listConnections(
                    connected.inputMatrix, source=True
                ):
                    if pm.nodeType(conB) == "mgear_mulMatrix":
                        for drvCtl in pm.listConnections(
                            conB.matrixA, source=True
                        ):
                            if pm.nodeType(drvCtl) == "transform":
                                driver_control = drvCtl

    return driver_control


def joint_from_driver_ctl(node):
    """
    Will try find the joint given the Driver control by searching through the
    mGear nodes.

    TO DO:
        Expand this to be more robust. Check all channels / not rely on
        translate connections only.

    Arguments:
        node (PyNode): node to search connections on

    Returns:
        PyNode : joint
    """
    joint = None
    for connected in pm.listConnections(node.worldMatrix[0], destination=True):
        if pm.nodeType(connected) == "mgear_mulMatrix":
            for conA in pm.listConnections(connected.output, destination=True):
                if pm.nodeType(conA) == "decomposeMatrix":
                    for conB in pm.listConnections(
                        conA.outputTranslateX, destination=True
                    ):
                        if pm.nodeType(conB) == "joint":
                            joint = conB

    return joint


def get_info(node):
    """
    Given either the SDK box, or Anim ctl, will find other and return it

    Arguments:
        node (PyNode): either the SDK box or Anim ctl

    Returns:
        list [PyNode(SDK box), PyNode(anim ctl)]
    """
    SDK_node = None
    tweak_node = None

    if pm.attributeQuery("is_SDK", node=node, ex=True):
        SDK_node = node
        for connected in pm.listConnections(node.attr("ctl")):
            if pm.attributeQuery("is_tweak", node=connected, ex=True):
                tweak_node = connected

    if pm.attributeQuery("is_tweak", node=node, ex=True):
        tweak_node = node
        for connected in pm.listConnections(node.attr("sdk")):
            if pm.attributeQuery("is_SDK", node=connected, ex=True):
                SDK_node = connected

    return [SDK_node, tweak_node]


def ctl_from_list(in_list, SDK=False, animTweak=False):
    """
    Returns either the SDK's or animTweaks from the in_list.
    If given a SDK, it will find the animTweak pair and vise versa.
    To qualify as SDK ctl must have "is_SDK" attr, or "is_tweak" attr for
    animTweak

    Arguments:
        in_list (list[PyNode]): List of PyNodes to sort through
        SDK (bool): If you want SDK ctls
        animTweak (bool): If you want animTweak ctls

    Returns:
        list [List of either SDK ctls or animTweaks]
    """
    SDK_ctls = []
    for item in in_list:
        # If its a joint, find the connected control
        if pm.nodeType(item) == "joint":
            item = driver_ctl_from_joint(item)

        SDK_ctl = get_info(item)[0]
        if SDK_ctl:
            if SDK_ctl not in SDK_ctls:
                SDK_ctls.append(SDK_ctl)

    return SDK_ctls


# ================================================= #
# SDK
# ================================================= #
def _filter_out_unitConversion_nodes(nodes_list):
    filtered_nodes = []
    for nod in nodes_list:
        if isinstance(nod, pm.nt.UnitConversion) or \
                nod.type() == "unitConversion":
            out_nodes = pm.listConnections(nod.output, d=True) or []
            if out_nodes:
                nod = out_nodes[0]
        filtered_nodes.append(nod)

    return filtered_nodes


def set_driven_key(
    driverAttr,
    drivenAttr,
    driverVal,
    drivenVal,
    preInfinity=0,
    postInfinity=0,
    inTanType="linear",
    outTanType="linear",
):
    """
    Convinience function to aid in setting driven keys.

    Arguments:
        driverAttr (PyNode.attribute): Driver.attr to drive the SDK
        drivenAttr (PyNode.attribute): Driven.attr to be driven by the SDK
        driverVal (float): Value to use for driver
        drivenVal (float): Value to use for driven
        preInfinity (int): IndexKey - constant[0], linear[1], cycle[2],
                           cycleOffset[3], Oscillate[4]
        postInfinity (int): IndexKey - constant[0], linear[1], cycle[2],
                     cycleOffset[3], Oscillate[4]
        inTanType (str): spline, linear, fast, slow, flat, stepped, step next,
                         fixed, clampedand plateau
        outTanType (str): spline, linear, fast, slow, flat, stepped, step next,
                          fixed, clampedand plateau

    Returns:
        new Anim UU node or the Edited one.

    TO DO:
        fix the return.
    """
    animUU = None

    # Grabbing the Driver connections for comparison later
    driver_con_A = pm.listConnections(driverAttr)

    # setting the Driven key frame
    pm.setDrivenKeyframe(
        drivenAttr,
        cd=driverAttr,
        driverValue=driverVal,
        value=drivenVal,
        inTangentType=inTanType,
        outTangentType=outTanType,
    )

    # Compairing the connections to DriverAtt to find new Anim UU node.
    DriverConB = pm.listConnections(driverAttr)
    DriverConB = _filter_out_unitConversion_nodes(DriverConB)

    for conB in DriverConB:
        if conB not in driver_con_A:
            animUU = conB

    # Setting Attrs
    if animUU:
        animUU.preInfinity.set(preInfinity)
        animUU.postInfinity.set(postInfinity)

    # renaming
    if animUU:
        newName = "{}_{}".format(
            driverAttr.split(".")[0], drivenAttr.split(".")[1]
        )
        pm.rename(animUU, newName)

    return animUU


def get_driven_from_attr(driverAttr, is_SDK=False):
    """
    Returns a list of driven controls given the driver attr

    Arguments:
        driverAttr (PyNode): the driver attr to search
        is_SDK (bool): if True, will check if the is_SDK attr is present before
        adding to driven_ctls list.

    Returns:
        list [List of unicode names]
    """
    driven_ctls = []
    connected_nodes = _filter_out_unitConversion_nodes(pm.listConnections(driverAttr))

    for connected_node in connected_nodes:
        if pm.nodeType(connected_node) in SDK_ANIMCURVES_TYPE:
            drvn_ctl = sdk_io.getSDKDestination(connected_node)[0]
            if is_SDK:
                if not pm.attributeQuery("is_SDK", node=drvn_ctl, ex=True):
                    break
            if drvn_ctl not in driven_ctls:
                driven_ctls.append(drvn_ctl)

    return driven_ctls


def get_driver_from_driven(drivenCtl):
    """
    Finds the Driver controls for a given driven ctl

    Arguments:
        drivenCtl (PyNode): A Driven Node to query.

    Returns:
        list [All found Driver Nodes]

    """
    driver_ctls = []

    retrieved_SDK_nodes = sdk_io.getConnectedSDKs(drivenCtl)
    retrieved_SDK_nodes.extend(sdk_io.getMultiDriverSDKs(drivenCtl))

    for rtv_attrs in retrieved_SDK_nodes:
        for rtv_attr in rtv_attrs:
            if pm.nodeType(rtv_attr) in SDK_ANIMCURVES_TYPE:
                try:
                    SDK_info = sdk_io.getSDKInfo(rtv_attr.node())
                    if SDK_info["driverNode"] not in driver_ctls:
                        driver_ctls.append(SDK_info["driverNode"])
                except:  # noqa: E722
                    pass

    return driver_ctls


def get_driver_keys(
    driverAttr, firstKey=None, prevKey=None, nextKey=None, lastKey=None
):
    """
    Returns a list of Driver key values for the given driverAttr.

    If all optional arguments are None, will return list of all values

    Arguments:
        driverAttr (PyNode.Attribute): Driver Ctl.attr
        firstKey (bool):
        prevKey (bool):
        nextKey (bool):
        lastKey (bool):

    Returns:
        List (If all optional None) - List of driver key values
        float (If one specified) - The float value for the driver on that key.
    """
    dirver_con = pm.listConnections(driverAttr)

    keys_list = []
    if len(dirver_con) > 0:
        for con in dirver_con:
            if pm.nodeType(con) in SDK_ANIMCURVES_TYPE:
                SDK_dict = sdk_io.getSDKInfo(con)
                for key in SDK_dict["keys"]:
                    if key[0] not in keys_list:
                        keys_list.append(key[0])

        if firstKey:
            return keys_list[0]

        if prevKey:
            return next_smallest(driverAttr.get(), keys_list)

        if nextKey:
            return next_biggest(driverAttr.get(), keys_list)

        if lastKey:
            return keys_list[-1]
        else:
            return keys_list


def mirror_SDK(driverCtl):
    """
    Takes in a driver control and extrapolates out all the other
    information needed to mirror it's connected SDK's.

    Arguments:
        driverCtl (PyNode):

    Returns:
        None
    """

    # Getting The Opposite Driver
    t_driver = pickWalk.getMirror(driverCtl)[0]

    # Getting all the SDK Ctls + RHS Counterparts from Driver Ctl Name.
    driven_ctls_dict = {}
    for sdk_attrs in sdk_io.getConnectedSDKs(driverCtl):
        for sdk_attr in sdk_attrs:
            if pm.nodeType(sdk_attr.node()) in SDK_ANIMCURVES_TYPE:
                destination_ctl = sdk_io.getSDKDestination(sdk_attr.node())[0]
                driven_ctls_dict[destination_ctl] = pickWalk.getMirror(
                    pm.PyNode(destination_ctl)
                )[0]

    # Removing any Already Existing SDK's from the target driver.
    for s_driven, t_driven in driven_ctls_dict.items():
        sdk_io.removeSDKs(t_driven, sourceDriverFilter=[t_driver])

    # Looping over the Drivens + Mirroring.
    for s_driven, t_driven in driven_ctls_dict.items():
        sdk_io.copySDKsToNode(
            sourceDriven=s_driven,
            targetDriver=t_driver,
            targetDriven=t_driven,
            sourceDriverFilter=[driverCtl],
        )


def get_current_SDKs():
    """
    If SDK ctls are selected, will return only the SDK nodes
    Attatched to those in the selection. If nothing is
    selected, will get all the SDK nodes in the scene and return them.

    Returns:
        SDKs_to_set (list) - list of SDKs as Pynodes
    """
    SDKs_to_set = []
    all_ctls = []
    user_sel = pm.ls(sl=True)
    # If something selected, Get all SDK ctls in sel.
    if len(user_sel) > 0:
        for item in user_sel:
            if pm.hasAttr(item, "is_SDK"):
                if item not in all_ctls:
                    all_ctls.append(item)
        if len(all_ctls) == 0:
            pm.warning("Please select a SDK ctl")
    else:
        # Get all ctls with is_SDK attr
        for item in pm.ls("*.is_SDK"):
            SDK_ctl = item.node()
            if SDK_ctl not in all_ctls:
                all_ctls.append(pm.PyNode(SDK_ctl))

    if all_ctls:
        # getting all SDKs attatched to Ctls
        for ctl in all_ctls:
            for sdk, sdkInfo in sdk_io.getAllSDKInfoFromNode(ctl).items():
                SDKs_to_set.append(pm.PyNode(sdk))

    return SDKs_to_set


def set_zero_key(
    drivenCtls,
    keyChannels,
    driver,
    driverAtt,
    inTanType="linear",
    outTanType="linear",
):
    """
    Takes a Current "state", Sets a ZERO SDK
    then resets to the "state".

    Arguments:
        drivenCtls (list): List of String names of the Driven Ctls.
        keyChannels (list): List of Channels to Key
        driver (PyNode): Driver Node
        driverAtt (str): Driver Attr given as a string
        inTanType (str / optional): Tangent type, by default is linear.
        outTanType (str / optional): Tangent type, by default is linear.

    Returns:
        n/a

    """
    for dvn_ctl in drivenCtls:
        dvn_ctl = pm.PyNode(dvn_ctl)
        for channel in keyChannels:
            for Ax in ["X", "Y", "Z"]:
                # Getting the Channel value, if it is default, set a Zero Key.
                dvn_val = dvn_ctl.attr(channel + Ax).get()
                default_val = 1.0 if channel == "scale" else 0.0
                # Setting ZERO KEY
                set_driven_key(
                    driverAttr=driver.attr(driverAtt),
                    drivenAttr=dvn_ctl.attr(channel + Ax),
                    driverVal=0,
                    drivenVal=default_val,
                    preInfinity=0,
                    postInfinity=0,
                    inTanType=inTanType,
                    outTanType=outTanType,
                )
                # Setting the Driven Ctl back to its previous value
                dvn_ctl.attr(channel + Ax).set(dvn_val)


def key_at_current_values(
    drivenCtls,
    keyChannels,
    driver,
    driverAtt,
    inTanType="linear",
    outTanType="linear",
    zeroKey=False,
):
    """
    Helper function to set SDK's at Driven nodes current values
    Arguments:
        drivenCtls (list): List of String names of the Driven Ctls.
        keyChannels (list): List of Channels to Key
        driver (PyNode): Driver Node
        driverAtt (str): Driver Attr given as a string
        inTanType (str / optional): Tangent type, by default is linear.
        outTanType (str / optional): Tangent type, by default is linear.
        zeroKey (bool / optional): if True, will set a zero key before
                                   setting the key at current value.

    Returns:
        n/a
    """
    # Setting SDK At Current Values
    for dvn_ctl in drivenCtls:
        dvn_ctl = pm.PyNode(dvn_ctl)
        for channel in keyChannels:
            for Ax in ["X", "Y", "Z"]:
                if zeroKey:
                    # Getting the Channel values default, and setting a
                    # Zero Key.
                    dvn_val = dvn_ctl.attr(channel + Ax).get()
                    # default_val = 1.0 if channel == "scale" else 0.0
                    # Setting ZERO KEY
                    set_driven_key(
                        driverAttr=driver.attr(driverAtt),
                        drivenAttr=dvn_ctl.attr(channel + Ax),
                        driverVal=0,
                        drivenVal=0,
                        preInfinity=0,
                        postInfinity=0,
                        inTanType=inTanType,
                        outTanType=outTanType,
                    )
                    # Setting the Driven Ctl back to its previous value
                    dvn_ctl.attr(channel + Ax).set(dvn_val)

                set_driven_key(
                    driverAttr=driver.attr(driverAtt),
                    drivenAttr=dvn_ctl.attr(channel + Ax),
                    driverVal=driver.attr(driverAtt).get(),
                    drivenVal=dvn_ctl.attr(channel + Ax).get(),
                    preInfinity=0,
                    postInfinity=0,
                    inTanType=inTanType,
                    outTanType=outTanType,
                )


def delete_current_value_keys(current_driver_val, node, sourceDriverFilter):
    """
    Arguments:
        node ():
        sourceDriverFilter ():

    Returns:
        n/a
    """
    sourceSDKInfo = sdk_io.getConnectedSDKs(
        node, sourceDriverFilter=sourceDriverFilter
    )
    sourceSDKInfo.extend(
        sdk_io.getMultiDriverSDKs(node, sourceDriverFilter=sourceDriverFilter)
    )

    for source_sdk_attr, driven_ctl in sourceSDKInfo:
        source_sdk = source_sdk_attr.node()
        keys = sdk_io.getSDKInfo(source_sdk)["keys"]

        for i, key in enumerate(keys):
            if key[0] == current_driver_val:
                pm.cutKey(
                    source_sdk_attr.node(),
                    index=(i, i),
                    option="keys",
                    clear=1,
                )


def prune_DK_nodes(white_list=[]):
    """
    Finds all the driven key nodes that have no
    input or output connected and removes them.
    Nodes with the word profile in are excluded
    so that no guide components are broken.

    Arguments:
        white_list (list / optional): List of nodes to ignore

    Returns:
        list (All the names of the deleted nodes)
    """
    # Getting all the anim nodes in scene
    all_anim_nodes = pm.ls(type=SDK_ANIMCURVES_TYPE)

    # If a node has no connections, store it.
    problem_nodes = []
    for anim_node in all_anim_nodes:
        if not pm.listConnections(anim_node.input):
            if anim_node not in problem_nodes:
                if anim_node not in white_list:
                    if "profile" not in anim_node.nodeName():
                        problem_nodes.append(anim_node)
        if not pm.listConnections(anim_node.output):
            if anim_node not in problem_nodes:
                if anim_node not in white_list:
                    if "profile" not in anim_node.nodeName():
                        problem_nodes.append(anim_node)

    # Deleting the problem nodes
    for node in problem_nodes:
        pm.delete(node)

    # node names
    deleted_nodes = [x.nodeName() for x in problem_nodes]

    if deleted_nodes:
        print("Deleted Nodes:")
        for deleted_node in deleted_nodes:
            print(deleted_node)
    else:
        print("No Nodes found to delete")

    return deleted_nodes


# ================================================= #
# Attributes
# ================================================= #
# Note: This could be moved to another mGear
# module but will leave here for now.


def toggle_limits(axis, controls=None):
    """
    Toggles the controller translate Limits On or Off
    from their current values, both upper and lower.

    Aruments:
        axis (str): x,y,z axis to use.
        controls (list / optional): List of PyNodes to iterate over
                                    If None, use Selection


    """
    # If no controls are provided, use selection
    if not controls:
        controls = pm.ls(sl=True, type="transform")

    # Loop over controls and toggle the limits
    for control in controls:
        if axis == "x":
            current_status = pm.transformLimits(control, q=True, etx=True)
            current_status_inv = [not i for i in current_status]
            pm.transformLimits(control, etx=current_status_inv)

        elif axis == "y":
            current_status = pm.transformLimits(control, q=True, ety=True)
            current_status_inv = [not i for i in current_status]
            pm.transformLimits(control, ety=current_status_inv)

        elif axis == "z":
            current_status = pm.transformLimits(control, q=True, etz=True)
            current_status_inv = [not i for i in current_status]
            pm.transformLimits(control, etz=current_status_inv)


def set_limits_from_current(
    axis, controls=None, upperLimit=False, lowwerLimit=False
):
    """
    Sets either the upper or lowwer limits on
    the provided control and axis

    > get current limits
    > update either the lower or the upper
    > set limits to Enabled.

    There is a lot of duplicate code but its a bit unavoidable
    with how transformLimits flags are set up.


    Aruments:
        axis (str): x,y,z axis to use.
        controls (list): List of PyNodes to iterate over
        upperLimit (bool): If True will set the upper Limit
        lowwerLimit (bool): If True will set the lowwer Limit

    """
    # If no controls are provided, use selection
    if not controls:
        controls = pm.ls(sl=True, type="transform")

    # Loop over controls and toggle the limits
    for control in controls:

        current_val = pm.getAttr(control.attr("translate" + axis.capitalize()))

        # ----------------------------------------------
        # X
        # ----------------------------------------------
        if axis == "x":
            current_limit_vals = pm.transformLimits(control, q=True, tx=True)
            current_limits = pm.transformLimits(control, q=True, etx=True)

            if upperLimit:
                current_limit_vals[1] = current_val
                current_limits[1] = True
                pm.transformLimits(
                    control, tx=current_limit_vals, etx=current_limits
                )

            if lowwerLimit:
                current_limit_vals[0] = current_val
                current_limits[0] = True
                pm.transformLimits(
                    control, tx=current_limit_vals, etx=current_limits
                )

        # ----------------------------------------------
        # Y
        # ----------------------------------------------
        if axis == "y":
            current_limit_vals = pm.transformLimits(control, q=True, ty=True)
            current_limits = pm.transformLimits(control, q=True, ety=True)

            if upperLimit:
                current_limit_vals[1] = current_val
                current_limits[1] = True
                pm.transformLimits(
                    control, ty=current_limit_vals, ety=current_limits
                )

            if lowwerLimit:
                current_limit_vals[0] = current_val
                current_limits[0] = True
                pm.transformLimits(
                    control, ty=current_limit_vals, ety=current_limits
                )

        # ----------------------------------------------
        # Z
        # ----------------------------------------------
        if axis == "z":
            current_limit_vals = pm.transformLimits(control, q=True, tz=True)
            current_limits = pm.transformLimits(control, q=True, etz=True)

            if upperLimit:
                current_limit_vals[1] = current_val
                current_limits[1] = True
                pm.transformLimits(
                    control, tz=current_limit_vals, etz=current_limits
                )

            if lowwerLimit:
                current_limit_vals[0] = current_val
                current_limits[0] = True
                pm.transformLimits(
                    control, tz=current_limit_vals, etz=current_limits
                )
