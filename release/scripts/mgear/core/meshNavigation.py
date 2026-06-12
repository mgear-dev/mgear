"""Functions to help navigate the mesh topology"""

#############################################
# GLOBAL
#############################################
import mgear.pymaya as pm
import mgear.pymaya.datatypes as datatypes
from maya import OpenMaya as om
from . import utils
from maya import cmds


#############################################
# Vertex
#############################################

#NOTE: WIP function for further improvement in the eyerigger 2.1
def get_extreme_vertex_from_vtx_loop(vtx_list=None,
                                     side_range=False,
                                     z_up=False):
    """Get extreme vertices (up, low, in, out) from a vertex loop.

    Inspects a list of mesh vertex components (or mixed components that
    can be converted to vertices) and returns the extreme vertices along
    the lateral axis and the vertical axis.

    Args:
        vtx_list (list or None): List of mesh vertex components. If None,
            uses the current selection (flattened). Any edges/faces will
            be converted to vertices.
        side_range (bool): If True, use Z as the lateral axis. When
            `z_up` is False, this falls back to Y to match your logic.
        z_up (bool): If True, the up axis is Z; otherwise it is Y.

    Returns:
        tuple: (upPos, lowPos, inPos/outPos depending on side_range,
            input_list, vertex_list)

    """
    if not vtx_list:
        vtx_list = cmds.ls(sl=True, fl=True) or []

    verts = _as_vertices_unique(vtx_list)

    max_lat = None
    min_lat = None
    max_up = None
    min_up = None

    up_pos = None
    low_pos = None
    in_pos = None
    out_pos = None

    # Lateral axis: X(0) by default; Z(2) if side_range.
    axis_index = 2 if side_range else 0
    # Up axis: Z(2) if z_up else Y(1).
    up_axis = 2 if z_up else 1
    # Preserve your special case: if Y-up and side_range=True => lateral Y.
    if not z_up and axis_index == 2:
        axis_index = 1

    for v in verts:
        pos = cmds.pointPosition(v, w=True)
        lat = pos[axis_index]
        upv = pos[up_axis]

        if max_lat is None or lat > max_lat:
            max_lat = lat
            out_pos = v
        if min_lat is None or lat < min_lat:
            min_lat = lat
            in_pos = v
        if max_up is None or upv > max_up:
            max_up = upv
            up_pos = v
        if min_up is None or upv < min_up:
            min_up = upv
            low_pos = v

    if side_range:
        return (up_pos, low_pos, out_pos, in_pos, vtx_list, verts)
    else:
        return (up_pos, low_pos, in_pos, out_pos, vtx_list, verts)


def _as_vertices_unique(items):
    """Convert mixed components to a unique, ordered vertex list.

    Args:
        items (list): Mixed mesh components (verts/edges/faces) or strs.

    Returns:
        list: Unique, ordered list of vertex component strings.

    """
    flat = cmds.ls(items, fl=True) or []
    if not flat:
        return []

    verts_all = []
    for comp in flat:
        conv = cmds.polyListComponentConversion(comp, tv=True)
        if not conv:
            continue
        exp = cmds.ls(conv, fl=True) or []
        if exp:
            verts_all.extend(exp)

    seen = set()
    verts = []
    for v in verts_all:
        if v in seen:
            continue
        seen.add(v)
        verts.append(v)
    return verts


def getExtremeVertexFromLoop(edgeList=None, sideRange=False, z_up=False):
    """Get extreme vertex X and  Y

    min and max positions from edge loop

    Arguments:
        edgeList (list): Edge list
        sideRange (bool): If True will calculate the extreme position
            of Z instead of X
    Returns:
        list: upPos, lowPos, inPos, outPos, edgeList, vertexList

    """
    if not edgeList:
        edgeList = [x for x in pm.selected(fl=1)]
    vertexList = []
    for x in edgeList:
        cv = x.connectedVertices()
        for v in cv:
            if v not in vertexList:
                vertexList.append(v)
    maxX = None
    maxY = None

    minX = None
    minY = None

    upPos = None
    lowPos = None
    inPos = None
    outPos = None
    # index for X or Z
    if sideRange:
        axisIndex = 2
    else:
        axisIndex = 0

    if z_up:
        up_axis = 2
    else:
        up_axis = 1
        if axisIndex == 2:
            axisIndex = 1
    for x in vertexList:
        pos = x.getPosition(space="world")
        if maxX is None or pos[axisIndex] > maxX:
            maxX = pos[axisIndex]
            outPos = x
        if maxY is None or pos[up_axis] > maxY:
            maxY = pos[up_axis]
            upPos = x
        if minX is None or pos[axisIndex] < minX:
            minX = pos[axisIndex]
            inPos = x
        if minY is None or pos[up_axis] < minY:
            minY = pos[up_axis]
            lowPos = x
    if sideRange:
        return upPos, lowPos, outPos, inPos, edgeList, vertexList
    else:
        return upPos, lowPos, inPos, outPos, edgeList, vertexList


def getConcentricVertexLoop(loop, nbLoops):
    """Get concentric vertex loops

    Arguments:
        loop (list): Vertex loop list
        nbLoops (int): Number of loops to search

    Returns:
        list: the loop list

    """
    loopList = []
    allLoops = []
    for x in loop:
        allLoops.append(x)
    loopList.append(loop)

    for x in range(nbLoops):
        tempLoopList = []
        for v in loop:
            connected = v.connectedVertices()
            for cv in connected:
                if cv not in loop:
                    if cv not in allLoops:
                        allLoops.append(cv)
                        tempLoopList.append(cv)
        loop = []
        for c in tempLoopList:
            loop.append(c)

        loopList.append(tempLoopList)

    return loopList


def getVertexRowsFromLoops(loopList):
    """Get vertex rows from edge loops

    Arguments:
        loopList (list): Edge loop list

    Returns:
        list: vertex rows

    """
    rows = []
    for x in loopList[0]:
        rows.append([x])

    loopListLength = len(loopList) - 1

    for i in range(loopListLength):
        for e, r in enumerate(rows):
            cvs = r[-1].connectedVertices()
            # little trick to force the expansion in 2 directions
            cvs2 = False
            if len(r) > 2:
                cvs2 = r[-2].connectedVertices()

            if cvs2:
                for cv in cvs2:
                    if cv in loopList[i + 1]:
                        rows[e].append(cv)
                        continue
            for cv in cvs:
                if cv in loopList[i + 1]:
                    rows[e].append(cv)
                    continue
    return rows


#################################################
# EDGE LOOPS and ROWS
#################################################


def edgeRangeInLoopFromMid(edgeList, midPos, endA, endB):
    """Return a range of edges in the same loop from a mid position

    Arguments:
        edgeList (list): selection edge loop
        midPos (vertex): mid vertex
        endA (vertex): endA vertex
        endB (vertex): endB vertex

    Returns:
        list: loop range

    """
    extremeEdges = []

    scanPoint = [midPos]

    scannedPoints = []
    indexcheck = []
    midEdges = []
    count = 0
    stop = False
    while True:
        oldScanPoint = []
        for sp in scanPoint:
            ce = sp.connectedEdges()
            oldScanPoint.append(sp)
            scannedPoints.append(sp)
            for e in ce:
                if e in edgeList:
                    if e not in midEdges:
                        midEdges.append(e)
                    cv = e.connectedVertices()
                    for v in cv:
                        if (
                            v.index() in [endA.index(), endB.index()]
                            and e not in extremeEdges
                        ):
                            # extra check to ensure that the 2 edges
                            # selected are not attach to the same vertex
                            if v.index() not in indexcheck:
                                extremeEdges.append(e)
                                indexcheck.append(v.index())
                                if len(extremeEdges) == 2:
                                    stop = True
        # regenerate the new list for recursive scan
        scanPoint = []
        for sp in oldScanPoint:
            ce = sp.connectedEdges()
            for e in ce:
                if e in edgeList:
                    cv = e.connectedVertices()
                    for v in cv:
                        if v not in scanPoint and v not in scannedPoints:
                            if v.index() not in [endA.index(), endB.index()]:
                                scanPoint.append(v)

        if stop:
            break
        count += 1
        if count > 50:
            break
    # loopRange = set(midEdges + extremeEdges)
    loopRange = midEdges + extremeEdges
    return loopRange


def edgeLoopBetweenVertices(startPos, endPos):
    """Computes edge loop between two vertices.

    Arguments:
        startPos (vertex): Start of edge loop
        endPos (vertex): End of edge loop

    Returns:
        Edge loop, if one exists. Otherwise None.

    """

    oldSelection = pm.selected()
    mesh = startPos.node()
    edgeLoops = []
    for startEdge in startPos.connectedEdges():
        for endEdge in endPos.connectedEdges():
            testEdgeLoop = pm.polySelect(
                mesh, edgeLoopPath=[startEdge.index(), endEdge.index()]
            )
            if testEdgeLoop:
                edgeLoops.append(pm.selected())
    pm.select(oldSelection, r=1)
    if edgeLoops:
        edgeLoops.sort(key=len)
        return edgeLoops[0]
    return None


#################################################
# Bounding box info
#################################################


def bboxCenter(obj, radius=False):
    """Get bounding box center of mesh object

    Arguments:
        obj (dagNode): mesh object
        radius (bool): If True return a list the center + the radius

    Returns:
        list of float: the bounding box center in world space

    >>> center = mnav.bboxCenter(source, radius=False)

    """
    bbx = obj.getBoundingBox(invisible=True, space="world")
    center = [(bbx[0][x] + bbx[1][x]) / 2.0 for x in range(3)]
    if radius:
        r = abs((bbx[0][0] - bbx[1][0]) / 2)
        return center, r
    return datatypes.Vector(center)


def bBoxData(obj=None, yZero=False, *args):
    """Get bounding box data of a mesh object

    Arguments:
        obj (dagNode): Mesh object
        yZero (bool): If True, sets the Y axis value to 0 in world space
        args:

    Returns:
        list: center, radio, bounding box full data

    """
    volCenter = False

    if not obj:
        obj = pm.selected()[0]
    shapes = pm.listRelatives(obj, ad=True, s=True)
    if shapes:
        bb = pm.polyEvaluate(shapes, b=True)
        volCenter = [(axis[0] + axis[1]) / 2 for axis in bb]
        if yZero:
            volCenter[1] = bb[1][0]
        radio = max([bb[0][1] - bb[0][0], bb[2][1] - bb[2][0]]) / 1.7

    return volCenter, radio, bb


#################################################
# CLOSEST LOCATIONS
#################################################


def getClosestPolygonFromTransform(geo, loc):
    """Get closest polygon from transform

    Arguments:
        geo (dagNode): Mesh object
        loc (matrix): location transform

    Returns:
        Closest Polygon

    """
    if isinstance(
        loc, (pm.nodetypes.Transform, pm.nodetypes.Joint, pm.nodetypes.Locator)
    ):
        pos = loc.getTranslation(space="world")
    else:
        pos = datatypes.Vector(loc[0], loc[1], loc[2])

    nodeDagPath = om.MObject()
    try:
        selectionList = om.MSelectionList()
        selectionList.add(geo.name())
        nodeDagPath = om.MDagPath()
        selectionList.getDagPath(0, nodeDagPath)
    except Exception as e:
        raise RuntimeError(
            "om.MDagPath() failed " "on {}. \n {}".format(geo.name(), e)
        )

    mfnMesh = om.MFnMesh(nodeDagPath)

    pointA = om.MPoint(pos.x, pos.y, pos.z)
    pointB = om.MPoint()
    space = om.MSpace.kWorld

    util = om.MScriptUtil()
    util.createFromInt(0)
    idPointer = util.asIntPtr()

    mfnMesh.getClosestPoint(pointA, pointB, space, idPointer)
    idx = om.MScriptUtil(idPointer).asInt()

    return geo.f[idx], pos


def getClosestVertexFromTransform(geo, loc):
    """Get closest vertex from transform

    Arguments:
        geo (dagNode or str): Mesh object
        loc (matrix): location transform

    Returns:
        Closest Vertex

    >>> v = mn.getClosestVertexFromTransform(geometry, joint)

    """
    geo = utils.as_pynode(geo)
    polygon, pos = getClosestPolygonFromTransform(geo, loc)

    faceVerts = [geo.vtx[i] for i in polygon.getVertices()]
    closestVert = None
    minLength = None
    for v in faceVerts:
        thisLength = (pos - v.getPosition(space="world")).length()
        if minLength is None or thisLength < minLength:
            minLength = thisLength
            closestVert = v
    return closestVert


def getClosestNVerticesFromTransform(geo, loc, count=32):
    """Get the N closest vertices to a transform position.

    Uses a flood-fill from the closest polygon to efficiently
    gather nearby vertices sorted by distance.

    Args:
        geo (dagNode or str): Mesh object.
        loc (matrix): Location transform or position.
        count (int, optional): Number of vertices to return.

    Returns:
        list: Of vertex PyNodes sorted by distance to loc.
    """
    geo = utils.as_pynode(geo)
    polygon, pos = getClosestPolygonFromTransform(geo, loc)

    seed_verts = set(polygon.getVertices())
    visited = set(seed_verts)
    frontier = list(seed_verts)
    collected = []

    for vtx_id in frontier:
        v = geo.vtx[vtx_id]
        d = (pos - v.getPosition(space="world")).length()
        collected.append((d, vtx_id, v))

    while len(collected) < count and frontier:
        next_frontier = []
        for vtx_id in frontier:
            v = geo.vtx[vtx_id]
            for neighbor in v.connectedVertices():
                n_id = neighbor.index()
                if n_id not in visited:
                    visited.add(n_id)
                    next_frontier.append(n_id)
                    d = (pos - neighbor.getPosition(space="world")).length()
                    collected.append((d, n_id, neighbor))
        frontier = next_frontier

    collected.sort(key=lambda x: x[0])
    return [item[2] for item in collected[:count]]


def find_mirror_edge(obj, edgeIndx):
    """Return the mirror edge of an edge

    Args:
        obj (PyNode or str): Mesh object to get the mirror edge
        edge (int): Index of the edge to find the mirror

    Returns:
        PyNode: Mirror edge as a pynode
    """
    obj = utils.as_pynode(obj)

    edge = pm.PyNode(obj.name() + ".e[{}]".format(str(edgeIndx)))
    v1 = edge.getPoint(0, space="world")
    v2 = edge.getPoint(1, space="world")

    # mirror vectors in X axis
    mv1 = [v1[0] * -1, v1[1], v1[2]]
    mv2 = [v2[0] * -1, v2[1], v2[2]]

    vtx1 = getClosestVertexFromTransform(obj.getShape(), mv1)
    vtx2 = getClosestVertexFromTransform(obj.getShape(), mv2)
    for ee in vtx1.connectedEdges():
        if ee in vtx2.connectedEdges():
            return ee


def get_closes_edge_index(sourceGeo, targetGeo, edgeIndx):
    """Get the closes edge index from 2 diferent object.

    In some situation even with same topology and vertez index order. The edge
    index may change.

    Args:
        sourceGeo (str): Name of the source object
        targetGeo (str): Name of the target object
        edgeIndx (int): Edge Index

    Returns:
        PyNode: Description
    """
    edge = pm.PyNode("{}.e[{}]".format(sourceGeo, str(edgeIndx)))

    verts = edge.connectedVertices()

    closes_v = []
    for v in verts:
        vv = getClosestVertexFromTransform(
            targetGeo, v.getPosition(space="world")
        )
        closes_v.append(vv)

    v1_edges = closes_v[0].connectedEdges()
    v2_edges = closes_v[1].connectedEdges()
    for e in v1_edges:
        if e in v2_edges:
            return e.index()


def get_selected_mesh():
    """Get the selected mesh dag path.

    Returns:
        seleted mesh: selected mesh dag path

    Raises:
        ValueError: Non selected object

    """
    selection = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(selection)

    if selection.length() == 0:
        raise ValueError("No object selected. Please select a polygon mesh.")

    mesh_dag_path = om.MDagPath()
    selection.getDagPath(0, mesh_dag_path)

    if mesh_dag_path.apiType() == om.MFn.kTransform:
        child_count = mesh_dag_path.childCount()
        for i in range(child_count):
            child = mesh_dag_path.child(i)
            if child.hasFn(om.MFn.kMesh):
                mesh_dag_path.push(child)
                break

    return mesh_dag_path


def get_mesh_dag_path(node):
    """Get the mesh dag path from a given node.

    Args:
        node (str or PyNode): The name of the node or the PyNode itself

    Returns:
        mesh_dag_path: The dag path to the mesh

    Raises:
        ValueError: If the node does not exist or is not a mesh
    """
    # Ensure node is a PyNode
    if isinstance(node, str):
        try:
            node = pm.PyNode(node)
        except pm.MayaNodeError:
            raise ValueError("No such node: {}".format(node))

    selection_list = om.MSelectionList()
    selection_list.add(str(node))

    mesh_dag_path = om.MDagPath()

    selection_list.getDagPath(0, mesh_dag_path)
    if mesh_dag_path.apiType() == om.MFn.kTransform:
        child_count = mesh_dag_path.childCount()
        for i in range(child_count):
            child = mesh_dag_path.child(i)
            if child.apiType() == om.MFn.kMesh:
                mesh_dag_path.push(child)
                break
    elif mesh_dag_path.apiType() != om.MFn.kMesh:
        raise ValueError("Node is not a mesh: {}".format(node))

    return mesh_dag_path


def get_edge_center(mesh_dag_path, edge_indices):
    """Summary

    Args:
        mesh_dag_path (dag paht): mesh dag path
        edge_indices (TYPE): edge index tuple

    Returns:
        vector: position

    Usage example:
        mesh_dag_path = get_selected_mesh()
        edge_indices = [40, 60]  # Replace with your desired edge indices
        center_position = get_edge_center(mesh_dag_path, edge_indices)
    """
    mesh_fn = om.MFnMesh(mesh_dag_path)
    edge_iter = om.MItMeshEdge(mesh_dag_path)

    point_sum = om.MVector()
    point_count = 0

    for edge_index in edge_indices:
        prev_index = om.MScriptUtil().asIntPtr()
        edge_iter.setIndex(edge_index, prev_index)
        vertex_indices = [edge_iter.index(0), edge_iter.index(1)]
        for vertex_index in vertex_indices:
            point = om.MPoint()
            mesh_fn.getPoint(vertex_index, point, om.MSpace.kWorld)
            point_sum += om.MVector(
                point
            )  # Convert MPoint to MVector before adding
            point_count += 1

    return om.MPoint(point_sum / point_count)  # Convert MVector back to MPoint
