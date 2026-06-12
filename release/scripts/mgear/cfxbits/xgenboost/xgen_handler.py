import mgear.pymaya as pm
from mgear.core import attribute


def get_connected_curve_guides(xgen_description):
    """return the connectected curve guides from descriptions

    Args:
        xgen_description (TYPE): Description

    Returns:
        list: curve guides list or empty list if none
    """
    curv2spline_node = get_curve_to_spline_node(xgen_description)
    if curv2spline_node:
        return curv2spline_node.inputCurves.listConnections()


def filter_curve_guides(crvs, xgen_description):
    # return only the curves that are part of the description guides
    crv_guides = get_connected_curve_guides(xgen_description)
    filtered_crvs = []
    for crv in crvs:
        if crv in crv_guides:
            filtered_crvs.append(crv)
        else:
            pm.displayWarning(
                "Object {0} is not crv guide for {1} and will be"
                " skipped".format(crv.name(), xgen_description))
    return filtered_crvs


# connect to xgen guide modifier
def connect_curve_to_xgen_guide(crv, xgen_description):
    curv2spline_node = get_curve_to_spline_node(xgen_description)
    if not curv2spline_node:
        curv2spline_node = create_curve_guide_setup(xgen_description)

    if not isinstance(crv, list):
        crv = [crv]
    for c in crv:
        next_idx = attribute.get_next_available_index(
            curv2spline_node.inputCurves)
        pm.connectAttr(
            c.worldSpace,
            curv2spline_node.attr("inputCurves[{}]".format(str(next_idx))))


def create_curve_guide_setup(xgen_description):

    # xgmModifierGuide node
    guide_modifier_node = pm.createNode("xgmModifierGuide")
    in_cnx = xgen_description.inSplineData.listConnections()
    if in_cnx:
        previous_cnx_node = in_cnx[0]
        pm.connectAttr(previous_cnx_node.outSplineData,
                       guide_modifier_node.inSplineData,
                       f=True)
    pm.connectAttr(guide_modifier_node.outSplineData,
                   xgen_description.inSplineData,
                   f=True)

    # xgmSplineDescription node
    spline_desc_node = pm.createNode("xgmSplineDescription")
    pm.connectAttr(spline_desc_node.outSplineData,
                   guide_modifier_node.inGuideData)
    spline_desc_node.visibility.set(0)

    # xgmCurveToSpline
    crv_to_spline_node = pm.createNode("xgmCurveToSpline")
    pm.connectAttr(crv_to_spline_node.outSplineData,
                   spline_desc_node.inSplineData)

    # xgmSplineBase
    spline_base_node = pm.createNode("xgmSplineBase")
    pm.connectAttr(spline_base_node.outSplineData,
                   crv_to_spline_node.inSplineData)
    pm.connectAttr(spline_base_node.outMeshData,
                   crv_to_spline_node.inMeshData)
    scalp = get_scalp(xgen_description)
    pm.connectAttr(scalp.worldMesh,
                   spline_base_node.attr("boundMesh[0]"))

    return crv_to_spline_node

# refresh que guide connection by disconnection and connectiong all curves


def refresh_curve_connections(guide_modifier):
    return


# disconnec curve guide
def disconnect_curve_from_xgen_guide(crv):
    # we asume that the curve is only connected to 1 description
    if not isinstance(crv, list):
        crv = [crv]
    for c in crv:
        cnx = c.worldSpace.listConnections(c=True, p=True)
        if cnx and len(cnx[0]) >= 2:
            pm.disconnectAttr(cnx[0][1])


def get_description_from_selection():
    if pm.selected():
        description = pm.selected()[0].getShape()
        if description.type() == "xgmSplineDescription":
            return description
        else:
            pm.displayWarning(
                "{} is not an xgen IGS description".format(description))
    else:
        pm.displayWarning(
            "Nothing selected. Please select xgen IGS description")


def get_description(name):
    """Get description from string name

    Args:
        name (str): name of the desctription

    Returns:
        PyNode: xgen Description
    """
    description = pm.ls(name)
    if description:
        if description[0].type() == "xgmSplineDescription":
            return pm.PyNode(description[0])
    else:
        pm.displayWarning("No Xgen IGS description selected")


def get_scalp(xgen_description):
    """get the scalp object of the xgen description

    Args:
        xgen_description (PyNode): xgen Description

    Returns:
        PyNode: scalp object
    """

    history = xgen_description.listHistory(type="xgmSplineBase")
    if history:
        base = history[0]
        scalp = base.boundMesh.listConnections()
        if scalp:
            return scalp[0]


def get_curve_to_spline_node(xgen_description):
    """get the curve to spline node of the guide modifier from xgen description

    Args:
        xgen_description (PyNode): xgen Description

    Returns:
        PyNode: xgen guide curve to spline node
    """
    if xgen_description:
        history = xgen_description.listHistory(type="xgmCurveToSpline")
        if history:
            curv2spline = history[0]
            return curv2spline
    else:
        pm.displayWarning("No Xgen IGS description selected")
