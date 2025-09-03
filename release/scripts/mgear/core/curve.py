"""NurbsCurve creation functions"""

# TODO: Finish documentation

#############################################
# GLOBAL
#############################################
from functools import wraps
import mgear.pymaya as pm
import maya.cmds as cmds
from mgear.pymaya import datatypes
import json
import maya.mel as mel

import maya.OpenMaya as om
import maya.api.OpenMaya as om2

from mgear.core import applyop
from mgear.core import utils
from mgear.core import transform

from .six import string_types

#############################################
# CURVE
#############################################


def addCnsCurve(parent, name, centers, degree=1):
    """Create a curve attached to given centers. One point per center

    Arguments:
        parent (dagNode): Parent object.
        name (str): Name
        centers (list of dagNode): Object that will drive the curve.
        degree (int): 1 for linear curve, 3 for Cubic.

    Returns:
        dagNode: The newly created curve.
    """
    # rebuild list to avoid input list modification
    centers = centers[:]
    if degree == 3:
        if len(centers) == 2:
            centers.insert(0, centers[0])
            centers.append(centers[-1])
        elif len(centers) == 3:
            centers.append(centers[-1])

    points = [datatypes.Vector() for center in centers]

    node = addCurve(parent, name, points, False, degree)

    applyop.gear_curvecns_op(node, centers)

    return node


def addCurve(
    parent, name, points, close=False, degree=3, m=datatypes.Matrix(), op=False
):
    """Create a NurbsCurve with a single subcurve.

    Arguments:
        parent (dagNode): Parent object.
        name (str): Name
        points (list of float | list of datatypes.Vector | list of om2.MPoint):
            points of the curve in a one dimension array
            [point0X, point0Y, point0Z, 1, point1X, point1Y, point1Z, 1, ...].
        close (bool): True to close the curve.
        degree (int): 1 for linear curve, 3 for Cubic.
        m (matrix): Global transform.
        op (bool, optional): If True will add a curve that pass over the points
                            This is equivalent of using"editPoint " flag

    No Longer Returned:
        dagNode: The newly created curve.
    """
    # Check and convert only if the item is an MPoint
    points = [
        [point.x, point.y, point.z] if isinstance(point, om2.MPoint) else point
        for point in points
    ]

    kwargs = {"name": name, "d": degree}
    if close:
        points.extend(points[:degree])
        knots = range(len(points) + degree - 1)
        # node = pm.curve(n=name, d=degree, p=points, per=close, k=knots)
        kwargs["per"] = close
        kwargs["k"] = knots
    if op:
        # kwargs["ep"] = points
        kwargs["ep"] = [datatypes.Vector(p) for p in points]
    else:
        kwargs["p"] = points
    node = pm.curve(**kwargs)

    if m is not None:
        node.setTransformation(m)

    if parent is not None:
        parent.addChild(node)

    return node


def createCurveFromOrderedEdges(
    edgeLoop, startVertex, name, parent=None, degree=3
):
    """Create a curve for a edgeloop ordering the list from starting vertex

    Arguments:
        edgeLoop (list ): List of edges
        startVertex (vertex): Starting vertex
        name (str): Name of the new curve.
        parent (dagNode): Parent of the new curve.
        degree (int): Degree of the new curve.

    Returns:
        dagNode: The newly created curve.
    """
    orderedEdges = []
    for e in edgeLoop:
        if startVertex in e.connectedVertices():
            orderedEdges.append(e)
            next = e
            break
    count = 0
    while True:
        for e in edgeLoop:
            if e in next.connectedEdges() and e not in orderedEdges:
                orderedEdges.append(e)
                next = e
                pass
        if len(orderedEdges) == len(edgeLoop):
            break
        count += 1
        if count > 100:
            break

    # return orderedEdges
    orderedVertex = [startVertex]
    orderedVertexPos = [startVertex.getPosition(space="world")]
    for e in orderedEdges:

        for v in e.connectedVertices():
            if v not in orderedVertex:
                orderedVertex.append(v)
                orderedVertexPos.append(v.getPosition(space="world"))

    crv = addCurve(parent, name, orderedVertexPos, degree=degree)
    return crv


def createCuveFromEdges(
    edgeList, name, parent=None, degree=3, sortingAxis="x"
):
    """Create curve from a edge list.

    Arguments:
        edgeList (list): List of edges.
        name (str): Name of the new curve.
        parent (dagNode): Parent of the new curve.
        degree (int): Degree of the new curve.
        sortingAxis (str): Sorting axis x, y or z

    Returns:
        dagNode: The newly created curve.

    """
    if sortingAxis == "x":
        axis = 0
    elif sortingAxis == "y":
        axis = 1
    else:
        axis = 2
    # conver MesEdge object to str
    string_edge_list = [
        str(edge) if not isinstance(edge, str) else edge for edge in edgeList
    ]
    vList = cmds.polyListComponentConversion(string_edge_list, fe=True, tv=True)
    vList = cmds.ls(vList, flatten=True)

    centers = []
    centersOrdered = []
    xOrder = []
    xReOrder = []
    for x in vList:
        vtx = pm.PyNode(x)
        for v in vtx:
            centers.append(v.getPosition(space="world"))
            # we use index [0] to order in X axis
            xOrder.append(v.getPosition(space="world")[axis])
            xReOrder.append(v.getPosition(space="world")[axis])
    for x in sorted(xReOrder):
        i = xOrder.index(x)
        centersOrdered.append(centers[i])

    crv = addCurve(parent, name, centersOrdered, degree=degree)
    return crv


def get_uniform_world_positions_on_curve(curve, num_positions):
    """
    Get a specified number of uniformly distributed world positions along a
    NURBS curve.

    Args:
        curve (str or PyNode): The name or PyNode of the NURBS curve.
        num_positions (int): The number of uniformly distributed positions
            to return.

    Returns:
        tuple: A list of tuples, where each tuple represents a world
            position (x, y, z).
    """
    # Get the MDagPath of the curve
    sel_list = om.MSelectionList()
    sel_list.add(curve)
    curve_dag_path = om.MDagPath()
    sel_list.getDagPath(0, curve_dag_path)

    # Create an MFnNurbsCurve function set to work with the curve
    curve_fn = om.MFnNurbsCurve(curve_dag_path)

    # Calculate the arc length of the curve
    arc_length = curve_fn.length()

    # Calculate the interval length between positions
    interval_length = arc_length / float(num_positions - 1)

    positions = []

    # Loop through the number of positions to calculate U parameter and world
    # position
    for i in range(num_positions):
        # Calculate the desired length for the current position
        desired_length = interval_length * i

        # Get the corresponding U parameter for the desired length
        u_param = curve_fn.findParamFromLength(desired_length)

        # Create a point in 3D space to store the world position
        world_pos = om.MPoint()

        # Get the world position at the given U parameter
        curve_fn.getPointAtParam(u_param, world_pos, om.MSpace.kWorld)

        # Append the world position as a tuple (x, y, z) to the positions list
        positions.append(
            datatypes.Point(world_pos.x, world_pos.y, world_pos.z)
        )

    # Return the positions as a tuple of tuples
    return positions


def getParamPositionsOnCurve(srcCrv, nbPoints):
    """get param position on curve

    Arguments:
        srcCrv (curve): The source curve.
        nbPoints (int): Number of points to return.

    Returns:
        tuple: world positions.
    """
    if isinstance(srcCrv, str) or isinstance(srcCrv, str):
        srcCrv = pm.PyNode(srcCrv)
    length = srcCrv.length()
    parL = srcCrv.findParamFromLength(length)
    param = []
    increment = parL / (nbPoints - 1)
    p = 0.0
    for x in range(nbPoints):
        # we need to check that the param value never exceed the parL
        if p > parL:
            p = parL
        pos = srcCrv.getPointAtParam(p, space="world")

        param.append(pos)
        p += increment

    return param


def createCurveFromCurve(srcCrv, name, nbPoints, parent=None):
    """Create a curve from a curve

    Arguments:
        srcCrv (curve): The source curve.
        name (str): The new curve name.
        nbPoints (int): Number of control points for the new curve.
        parent (dagNode): Parent of the new curve.

    Returns:
        dagNode: The newly created curve.
    """
    param = getParamPositionsOnCurve(srcCrv, nbPoints)

    crv = addCurve(parent, name, param, close=False, degree=3)
    return crv


def getCurveParamAtPosition(crv, position):
    """Get curve parameter from a position

    Arguments:
        position (list of float): Represents the position in worldSpace
            exp: [1.4, 3.55, 42.6]
        crv (curve): The  source curve to get the parameter.

    Returns:
        list: paramenter and curve length
    """
    point = om.MPoint(position[0], position[1], position[2])

    dag = om.MDagPath()
    obj = om.MObject()
    oList = om.MSelectionList()
    oList.add(crv.name())
    oList.getDagPath(0, dag, obj)

    curveFn = om.MFnNurbsCurve(dag)
    length = curveFn.length()
    crv.findParamFromLength(length)

    paramUtill = om.MScriptUtil()
    paramPtr = paramUtill.asDoublePtr()

    point = curveFn.closestPoint(point, paramPtr, 0.001, om.MSpace.kObject)
    curveFn.getParamAtPoint(point, paramPtr, 0.001, om.MSpace.kObject)

    param = paramUtill.getDouble(paramPtr)

    return param, length


def findLenghtFromParam(crv, param):
    """
    Find lengtht from a curve parameter

    Arguments:
        param (float): The parameter to get the legth
        crv (curve): The source curve.

    Returns:
        float: Curve uLength

    Example:
        .. code-block:: python

            oParam, oLength = cur.getCurveParamAtPosition(upRope, cv)
            uLength = cur.findLenghtFromParam(upRope, oParam)
            u = uLength / oLength

    """
    node = pm.createNode("arcLengthDimension")
    pm.connectAttr(
        crv.getShape().attr("worldSpace[0]"), node.attr("nurbsGeometry")
    )
    node.attr("uParamValue").set(param)
    uLength = node.attr("arcLength").get()
    pm.delete(node.getParent())
    return uLength


# ========================================


def get_color(node):
    """Get the color from shape node

    Args:
        node (TYPE): shape

    Returns:
        TYPE: Description
    """
    shp = node.getShape()
    if shp:
        if shp.overrideRGBColors.get():
            color = shp.overrideColorRGB.get()
            color = [color.x, color.y, color.z]
        else:
            color = shp.overrideColor.get()

        return color


@utils.one_undo
def set_color(node, color):
    """Set the color in the Icons.

    Arguments:
        node(dagNode): The object
        color (int or list of float): The color in index base or RGB.


    """
    # on Maya version.
    # version = mgear.core.getMayaver()

    if isinstance(color, int):

        for shp in node.listRelatives(shapes=True):
            shp.setAttr("overrideEnabled", True)
            shp.setAttr("overrideColor", color)
    else:
        for shp in node.listRelatives(shapes=True):
            shp.overrideEnabled.set(1)
            shp.overrideRGBColors.set(1)
            shp.overrideColorRGB.set(color[0], color[1], color[2])


# ========================================
# Curves IO ==============================
# ========================================


def collect_curve_shapes(crv, rplStr=["", ""]):
    """Collect curve shapes data

    Args:
        crv (dagNode): Curve object to collect the curve shapes data
        rplStr (list, optional): String to replace in names. This allow to
            change the curve names before store it.
            [old Name to replace, new name to set]

    Returns:
        dict, list: Curve shapes dictionary and curve shapes names
    """
    shapes_names = []
    shapesDict = {}
    for shape in crv.getShapes():
        shapes_names.append(shape.name().replace(rplStr[0], rplStr[1]))
        c_form = shape.form()
        degree = shape.degree()
        knots = list(shape.getKnots())
        form = c_form.key
        form_id = c_form.index
        pnts = [[cv.x, cv.y, cv.z] for cv in shape.getCVs(space="object")]
        lineWidth = shape.lineWidth.get()
        shapesDict[shape.name()] = {
            "points": pnts,
            "degree": degree,
            "form": form,
            "form_id": form_id,
            "knots": knots,
            "line_width": lineWidth,
        }

    return shapesDict, shapes_names


def collect_selected_curve_data(objs=None, rplStr=["", ""]):
    """Generate a dictionary descriving the curve data from selected objs

    Args:
        objs (None, optional): Optionally a list of object can be provided
    """
    if not objs:
        objs = pm.selected()

    return collect_curve_data(objs, rplStr=rplStr)


def collect_curve_data(objs, rplStr=["", ""]):
    """Generate a dictionary descriving the curve data

    Suport multiple objects

    Args:
        objs (dagNode): Curve object to store
        collect_trans (bool, optional): if false will skip the transformation
            matrix
        rplStr (list, optional): String to replace in names. This allow to
            change the curve names before store it.
            [old Name to replace, new name to set]

    Returns:
        dict: Curves data
    """

    # return if an empty list or None objects are pass
    if not objs:
        return

    if not isinstance(objs, list):
        objs = [objs]

    crvDict = {}
    crvDict["curves_names"] = []

    for x in objs:
        crvName = x.name().replace(rplStr[0], rplStr[1])
        crvParent = x.getParent()
        crvMatrix = x.getMatrix(worldSpace=True)
        crvTransform = crvMatrix.get()
        crvInfo, shapesName = collect_curve_shapes(x, rplStr)

        if crvParent:
            crvParent = crvParent.name()
            crvParent.replace(rplStr[0], rplStr[1])
        else:
            crvParent = None

        crvDict["curves_names"].append(crvName)
        curveDict = {
            "shapes_names": shapesName,
            "crv_parent": crvParent,
            "crv_transform": crvTransform,
            "crv_color": get_color(x),
            "shapes": crvInfo,
        }

        crvDict[crvName] = curveDict
    return crvDict


def crv_parenting(data, crv, rplStr=["", ""], model=None):
    """Parent the new created curves

    Args:
        data (dict): serialized curve data
        crv (str): name of the curve to parent
        rplStr (list, optional): String to replace in names. This allow to
            change the curve names before store it.
            [old Name to replace, new name to set]
        model (dagNode, optional): Model top node to help find the correct
            parent, if  several objects with the same name
    """
    crv_dict = data[crv]
    crv_parent = crv_dict["crv_parent"]
    crv_p = None
    crv = crv.replace(rplStr[0], rplStr[1])
    parents = pm.ls(crv_parent)
    # this will try to find the correct parent by checking the top node
    # in situations where the name is reapet in many places under same
    # hierarchy this method will fail.
    if len(parents) > 1 and model:
        for p in parents:
            if model.name() in p.name():
                crv_p = p
                break
    elif len(parents) == 1:
        crv_p = parents[0]
    else:
        pm.displayWarning(
            "More than one parent with the same name found for"
            " {}, or not top model root provided.".format(crv)
        )
        pm.displayWarning(
            "This curve"
            "  can't be parented. Please do it manually or"
            " review the scene"
        )
    if crv_p:
        # we need to ensure that we parent is the new curve.
        crvs = pm.ls(crv)
        if len(crvs) > 1:
            for c in crvs:
                if not c.getParent():  # if not parent means is the new
                    crv = c
                    break
        elif len(crvs) == 1:
            crv = crvs[0]
        pm.parent(crv, crv_p)


def create_curve_from_data_by_name(
    crv,
    data,
    replaceShape=False,
    rebuildHierarchy=False,
    rplStr=["", ""],
    model=None,
):
    """Build one curve from a given curve data dict

    Args:
        crv (str): name of the crv to create
        data (dict): serialized curve data
        replaceShape (bool, optional): If True, will replace the shape on
            existing objects
        rebuildHierarchy (bool, optional): If True, will regenerate the
            hierarchy
        rplStr (list, optional): String to replace in names. This allow to
            change the curve names before store it.
            [old Name to replace, new name to set]
        model (dagNode, optional): Model top node to help find the correct
            parent, if  several objects with the same name
    """
    crv_dict = data[crv]

    crv_transform = crv_dict["crv_transform"]
    shp_dict = crv_dict["shapes"]
    color = crv_dict["crv_color"]
    if replaceShape:
        first_shape = pm.ls(crv.replace(rplStr[0], rplStr[1]))
        if first_shape and model and model == first_shape[0].getParent(-1):
            pass
        else:
            first_shape = None
    else:
        first_shape = None

    if first_shape:
        first_shape = first_shape[0]
        # clean old shapes
        pm.delete(first_shape.listRelatives(shapes=True))
    for sh in crv_dict["shapes_names"]:
        points = shp_dict[sh]["points"]
        form = shp_dict[sh]["form"]
        degree = shp_dict[sh]["degree"]
        if "knots" in shp_dict[sh]:
            knots = shp_dict[sh]["knots"]
        else:
            knots = list(range(len(points) + degree - 1))
        if form != "open":
            close = True
        else:
            close = False

        # we dont use replace in order to support multiple shapes
        nsh = crv.replace(rplStr[0], rplStr[1])
        obj = pm.curve(
            name=nsh.replace("Shape", ""),
            point=points,
            periodic=close,
            degree=degree,
            knot=knots,
        )
        set_color(obj, color)
        # check for backwards compatibility
        if "line_width" in shp_dict[sh].keys():
            lineWidth = shp_dict[sh]["line_width"]
            set_thickness(obj, lineWidth)

        # handle multiple shapes in the same transform
        if not first_shape:
            first_shape = obj
            first_shape.setTransformation(crv_transform)
        else:
            for extra_shp in obj.listRelatives(shapes=True):
                first_shape.addChild(extra_shp, add=True, shape=True)
                pm.delete(obj)

    if rebuildHierarchy:
        crv_parenting(data, crv, rplStr, model)


def create_curve_from_data(
    data,
    replaceShape=False,
    rebuildHierarchy=False,
    rplStr=["", ""],
    model=None,
):
    """Build the curves from a given curve data dict

    Hierarchy rebuild after all curves are build to avoid lost parents

    Args:
        data (dict): serialized curve data
        replaceShape (bool, optional): If True, will replace the shape on
            existing objects
        rebuildHierarchy (bool, optional): If True, will regenerate the
            hierarchy
    """

    for crv in data["curves_names"]:
        create_curve_from_data_by_name(
            crv, data, replaceShape, rebuildHierarchy=False, rplStr=rplStr
        )

    # parenting
    if rebuildHierarchy:
        for crv in data["curves_names"]:
            crv_parenting(data, crv, rplStr, model)


def update_curve_from_data(data, rplStr=["", ""]):
    """update the curves from a given curve data dict

    Args:
        data (dict): serialized curve data
    """

    for crv in data["curves_names"]:
        crv_dict = data[crv]

        shp_dict = crv_dict["shapes"]
        color = crv_dict["crv_color"]
        first_shape = pm.ls(crv.replace(rplStr[0], rplStr[1]))
        if not first_shape:
            pm.displayWarning(
                "Couldn't find: {}. Shape will be "
                "skipped, since there is nothing to "
                "replace".format(crv.replace(rplStr[0], rplStr[1]))
            )
            continue

        if first_shape:
            first_shape = first_shape[0]
            # Because we don know if the number of shapes will match between
            # the old and new shapes. We only take care of the connections
            # of the first shape. Later will be apply to all the new shapes

            # store shapes connections
            shapes = first_shape.listRelatives(shapes=True)
            if shapes:
                cnx = shapes[0].listConnections(plugs=True, c=True)
                cnx = [[c[1], c[0].shortName()] for c in cnx]
                # Disconnect the conexion before delete the old shapes
                for s in shapes:
                    for c in s.listConnections(plugs=True, c=True):
                        pm.disconnectAttr(c[0])
                # clean old shapes
                pm.delete(shapes)

        for sh in crv_dict["shapes_names"]:
            points = shp_dict[sh]["points"]
            form = shp_dict[sh]["form"]
            degree = shp_dict[sh]["degree"]
            knots = list(range(len(points) + degree - 1))
            if form != "open":
                close = True
            else:
                close = False
            # we dont use replace in order to support multiple shapes
            obj = pm.curve(
                replace=False,
                name=sh.replace(rplStr[0], rplStr[1]),
                point=points,
                periodic=close,
                degree=degree,
                knot=knots,
            )
            set_color(obj, color)
            # check for backwards compatibility
            if "line_width" in shp_dict[sh].keys():
                lineWidth = shp_dict[sh]["line_width"]
                set_thickness(obj, lineWidth)

            for extra_shp in obj.listRelatives(shapes=True):
                # Restore shapes connections
                for c in cnx:
                    pm.connectAttr(c[0], extra_shp.attr(c[1]))
                first_shape.addChild(extra_shp, add=True, shape=True)
                pm.delete(obj)

        # clean up shapes names
        for sh in first_shape.getShapes():
            pm.rename(sh, sh.name().replace("ShapeShape", "Shape"))


def export_curve(filePath=None, objs=None, rplStr=["", ""]):
    """Export the curve data to a json file

    Args:
        filePath (None, optional): Description
        objs (None, optional): Description

    Returns:
        TYPE: Description
    """

    if not filePath:
        startDir = pm.workspace(q=True, rootDirectory=True)
        filePath = pm.fileDialog2(
            dialogStyle=2,
            fileMode=0,
            startingDirectory=startDir,
            fileFilter="NURBS Curves .crv (*%s)" % ".crv",
        )
        if not filePath:
            pm.displayWarning("Invalid file path")
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

    data = collect_selected_curve_data(objs, rplStr=rplStr)
    data_string = json.dumps(data, indent=4, sort_keys=True)
    f = open(filePath, "w")
    f.write(data_string)
    f.close()


def _curve_from_file(filePath=None):
    if not filePath:
        startDir = pm.workspace(q=True, rootDirectory=True)
        filePath = pm.fileDialog2(
            dialogStyle=2,
            fileMode=1,
            startingDirectory=startDir,
            fileFilter="NURBS Curves .crv (*%s)" % ".crv",
        )

    if not filePath:
        pm.displayWarning("Invalid file path")
        return
    if not isinstance(filePath, string_types):
        filePath = filePath[0]
    configDict = json.load(open(filePath))

    return configDict


def import_curve(
    filePath=None, replaceShape=False, rebuildHierarchy=False, rplStr=["", ""]
):
    create_curve_from_data(
        _curve_from_file(filePath), replaceShape, rebuildHierarchy, rplStr
    )


def update_curve_from_file(filePath=None, rplStr=["", ""]):
    # update a curve data from json file
    update_curve_from_data(_curve_from_file(filePath), rplStr)


# -----------------------------------------------------------------------------
# Curve Decorators
# -----------------------------------------------------------------------------


def keep_lock_length_state(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        crvs = args[0]
        state = {}
        for crv in crvs:
            if crv.getShape().hasAttr("lockLength"):
                attr = crv.getShape().lockLength
                state[crv.name()] = attr.get()
                attr.set(False)
            else:
                state[crv.name()] = None

        try:
            return func(*args, **kwargs)

        except Exception as e:
            raise e

        finally:
            for crv in crvs:
                current_state = state[crv.name()]
                if current_state:
                    crv.getShape().lockLength.set(current_state)

    return wrap


def keep_point_0_cnx_state(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        crvs = args[0]
        cnx_dict = {}
        for crv in crvs:
            cnxs = crv.controlPoints[0].listConnections(p=True)
            if cnxs:
                cnx_dict[crv.name()] = cnxs[0]
                pm.disconnectAttr(crv.controlPoints[0])
            else:
                cnx_dict[crv.name()] = None

        try:
            return func(*args, **kwargs)

        except Exception as e:
            raise e

        finally:
            for crv in crvs:
                src_attr = cnx_dict[crv.name()]
                if src_attr:
                    pm.connectAttr(src_attr, crv.controlPoints[0])

    return wrap


# -----------------------------------------------------------------------------

# add lock lenght attr


def lock_length(crv, lock=True):
    crv_shape = crv.getShape()
    if not crv_shape.hasAttr("lockLength"):
        crv_shape.addAttr("lockLength", at="bool")
    crv_shape.lockLength.set(lock)
    return crv_shape.lockLength


# average curve shape
def average_curve(
    crv, shapes, average=2, avg_shape=False, avg_scl=False, avg_rot=False
):
    """Average the shape, rotation and scale of the curve
    bettwen n number of curves

    Args:
        crv (dagNode): curve to average shape
        shapes ([dagNode]]): imput curves to average the shapes
        average (int, optional): Number of curves to use on the average
        avg_shape (bool, optional): if True will interpolate curve shape
        avg_scl (bool, optional): if True will interpolate curve scale
        avg_rot (bool, optional): if True will interpolate curve rotation

    """
    if shapes and len(shapes) >= average:
        shapes_by_distance = transform.get_closes_transform(crv, shapes)
        bst = []
        bst_filtered = []
        bst_temp = []
        weights = []
        blends = []
        # calculate the average value based on distance
        total_val = 0.0
        for x in range(average):
            total_val += shapes_by_distance[x][1][1]
        # setup the blendshape
        for x in range(average):
            blend = 1 - (shapes_by_distance[x][1][1] / total_val)
            bst.append(shapes_by_distance[x][1][0])
            weights.append((x, blend))
            blends.append(blend)

        if avg_rot:
            transform.interpolate_rotation(crv, bst, blends)
        if avg_scl:
            transform.interpolate_scale(crv, bst, blends)
        if avg_shape:
            # check the number of of points and rebuild to match number in
            # order of make the blendshape
            crv_len = len(crv.getCVs())
            for c in bst:
                if len(c.getCVs()) == crv_len:
                    bst_filtered.append(c)
                else:
                    t_c = pm.duplicate(c)[0]
                    bst_temp.append(t_c)
            if bst_temp:
                rebuild_curve(bst_temp, crv_len - 2)
                bst_filtered = bst_filtered + bst_temp
            # the blendshape is done with curves of the same number
            pm.blendShape(
                bst_filtered,
                crv,
                name="_".join([crv.name(), "blendShape"]),
                foc=True,
                w=weights,
            )
            pm.delete(crv, ch=True)
            pm.delete(bst_temp)

            # need to lock the first point after delete history
            lock_first_point(crv)
    else:
        pm.displayWarning(
            "Can average the curve with more" " curves than exist"
        )


# rebuild curve
@utils.one_undo
@utils.filter_nurbs_curve_selection
def rebuild_curve(crvs, spans):
    for crv in crvs:
        name = crv.name()
        pm.rebuildCurve(
            crv,
            ch=False,
            rpo=True,
            rt=0,
            end=1,
            kr=0,
            kcp=0,
            kep=1,
            kt=0,
            s=spans,
            d=2,
            tol=0.01,
            name=name,
        )


# smooth curve.
# Lockt lenght needs to be off for smooth correctly
@utils.one_undo
@keep_lock_length_state
@keep_point_0_cnx_state
def smooth_curve(crvs, smooth_factor=1):

    mel.eval("modifySelectedCurves smooth {} 0;".format(str(smooth_factor)))


# straight curve.
# Need to unlock/diconect first point to work.
# also no length lock


@utils.one_undo
@keep_lock_length_state
@keep_point_0_cnx_state
def straighten_curve(crvs, straighteness=0.1, keep_lenght=1):

    mel.eval(
        "modifySelectedCurves straighten {0} {1};".format(str(straighteness)),
        str(keep_lenght),
    )


# Curl curve.
# Need to unlock/diconect first point to work.
# also no length lock


def curl_curve(crvs, amount=0.3, frequency=10):

    mel.eval(
        "modifySelectedCurves curl {0} {1};".format(str(amount)),
        str(frequency),
    )


# ========================================


def set_thickness(crv, thickness=-1):
    crv.getShape().lineWidth.set(thickness)


def lock_first_point(crv):
    # lock first point in the curve
    mul_mtrx = pm.createNode("multMatrix")
    dm_node = pm.createNode("decomposeMatrix")
    pm.connectAttr(crv.worldMatrix[0], mul_mtrx.matrixIn[0])
    pm.connectAttr(crv.worldInverseMatrix[0], mul_mtrx.matrixIn[1])
    pm.connectAttr(mul_mtrx.matrixSum, dm_node.inputMatrix)
    pm.connectAttr(dm_node.outputTranslate, crv.getShape().controlPoints[0])


# ========================================


def evaluate_cubic_nurbs(control_points, percentage, knots=None, weights=None):
    """
    Evaluate a cubic NURBS curve at a given percentage.

    Args:
        control_points (list): List of control points, each as [x, y, z].
        percentage (float): Curve position as a percentage (0 to 100).
        knots (list, optional): Knot vector.
        weights (list, optional): List of weights corresponding to control
                                  points.

    Returns:
        list: Evaluated point as [x, y, z].
    """
    n = len(control_points) - 1
    p = 3  # Degree for cubic curve
    d = len(control_points[0])  # Dimension of each point

    if knots is None:
        knots = (
            [0] * (p + 1)
            + [i for i in range(1, n - p + 2)]
            + [n - p + 2] * (p + 1)
        )

    if weights is None:
        weights = [1.0] * (n + 1)

    # Normalize the u parameter to fit within the knot vector range
    u = knots[p] + (knots[-(p + 1)] - knots[p]) * (percentage / 100.0)

    # Slightly reduce u if percentage is 100 to avoid division by zero
    if percentage == 100:
        u -= 1e-5

    C = [0.0 for _ in range(d)]
    W = 0.0

    for i in range(n + 1):
        N = cox_de_boor(u, i, p, knots)
        for j in range(d):
            C[j] += N * weights[i] * control_points[i][j]
        W += N * weights[i]

    for j in range(d):
        C[j] /= W

    return C


def cox_de_boor(u, i, p, knots):
    """
    Cox-De Boor algorithm to evaluate B-Spline basis function.

    Args:
        u (float): Parameter value.
        i (int): Index of control point.
        p (int): Degree of the curve.
        knots (list): Knot vector.

    Returns:
        float: Evaluated B-Spline basis function value.
    """
    if p == 0:
        return 1.0 if knots[i] <= u < knots[i + 1] else 0.0

    N1 = 0
    if knots[i] != knots[i + p]:
        N1 = ((u - knots[i]) / (knots[i + p] - knots[i])) * cox_de_boor(
            u, i, p - 1, knots
        )

    N2 = 0
    if knots[i + 1] != knots[i + p + 1]:
        N2 = (
            (knots[i + p + 1] - u) / (knots[i + p + 1] - knots[i + 1])
        ) * cox_de_boor(u, i + 1, p - 1, knots)

    return N1 + N2


def create_locator_at_curve_point(object_names, percentage):
    """
    Create a locator at a point on a cubic NURBS curve in Maya.

    Args:
        object_names (list): The names of the objects representing control
                             points in Maya.
        percentage (float): Curve position as a percentage (0 to 100).

    Example usage in Maya
    Select objects representing control points in Maya before running the script

            object_names = cmds.ls(selection=True)
            create_locator_at_curve_point(object_names, 100)
    """
    control_points = []
    for obj_name in object_names:
        pos = cmds.xform(
            obj_name, query=True, translation=True, worldSpace=True
        )
        control_points.append(pos)

    point_on_curve = evaluate_cubic_nurbs(control_points, percentage)

    locator_name = cmds.spaceLocator()[0]
    cmds.setAttr(locator_name + ".translateX", point_on_curve[0])
    cmds.setAttr(locator_name + ".translateY", point_on_curve[1])
    cmds.setAttr(locator_name + ".translateZ", point_on_curve[2])


def add_linear_skinning_to_curve(curve_name, joint_list):
    """
    Adds a skinCluster to a curve and sets the skinning weights linearly
    among the list of joints based on the number of control points.

    Args:
        curve_name (str): The name of the curve to add the skinCluster to.
        joint_list (list): A list of joint names to be included in the skinCluster.

    Returns:
        PyNode: The name of the created skinCluster.
    """
    # Ensure the curve and joints exist
    if not pm.objExists(curve_name) or not all(
        pm.objExists(j) for j in joint_list
    ):
        raise RuntimeError("Curve or joints do not exist.")

    # Create skinCluster
    skin_cluster = pm.skinCluster(joint_list, curve_name, tsb=True)

    # Find the number of control points in the curve
    curve_shape = pm.listRelatives(curve_name, shapes=True)[0]
    num_cvs = len(curve_shape.getCVs())

    num_joints = len(joint_list)

    # Calculate the weight distribution
    for i in range(num_cvs):
        for j in range(num_joints):
            lower_bound = float(j) / (num_joints - 1)
            upper_bound = float(j + 1) / (num_joints - 1)

            normalized_i = float(i) / (num_cvs - 1)

            if lower_bound <= normalized_i <= upper_bound:
                weight = 1 - abs(normalized_i - lower_bound) * (num_joints - 1)
            else:
                weight = 0

            pm.skinPercent(
                skin_cluster,
                "{}.cv[{}]".format(curve_name, i),
                transformValue=[(joint_list[j], weight)],
            )

    return skin_cluster
