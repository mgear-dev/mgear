"""
Functions to work with skinCluster data.

This module is derivated from Chad Vernon's Skin IO.

`Chad Vernon's github \n
<https://github.com/chadmv/cmt/tree/master/scripts/cmt/deform>`_
"""

#############################################
# GLOBAL
#############################################
import os
import json
import pickle as pickle

import mgear.pymaya as pm
from maya import cmds
import maya.OpenMaya as OpenMaya
import maya.OpenMayaAnim as OpenMayaAnim
from .six import string_types
from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui
from mgear.core import pyqt
from mgear.core import utils
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

FILE_EXT = ".gSkin"
FILE_JSON_EXT = ".jSkin"
PACK_EXT = ".gSkinPack"

######################################
# Skin getters
######################################


def get_skin_cluster_fn(skin_cluster_name):
    """Retrieve the MFnSkinCluster from a skin cluster name.

    Args:
        skin_cluster_name (str): The name of the skin cluster.

    Returns:
        OpenMaya.MFnSkinCluster: The function set for the skin cluster.
    """
    selection = OpenMaya.MSelectionList()
    selection.add(
        skin_cluster_name
    )  # Add the skin cluster to the selection list
    mobject = OpenMaya.MObject()
    selection.getDependNode(
        0, mobject
    )  # Retrieve the MObject for the skin cluster

    # Create the function set for the skin cluster
    return OpenMayaAnim.MFnSkinCluster(mobject)


def getSkinCluster(obj, first_SC=False):
    """Get the skincluster of a given object

    Arguments:
        obj (dagNode): The object to get skincluster
        first_SC (bool, optional): If True, it will  return the first SkinCluster found

    Returns:
        pyNode: The skin cluster pynode object

    """
    skinCluster = None

    if isinstance(obj, string_types):
        obj = pm.PyNode(obj)
    try:
        if pm.nodeType(obj.getShape()) in [
            "mesh",
            "nurbsSurface",
            "nurbsCurve",
        ]:

            for shape in obj.getShapes():
                try:
                    for skC in pm.listHistory(shape, type="skinCluster"):
                        try:
                            if skC.getGeometry()[0] == shape:
                                skinCluster = skC
                                if first_SC:
                                    return skinCluster
                        except Exception:
                            pass
                except Exception:
                    pass
    except Exception:
        pm.displayWarning("%s: is not supported." % obj.name())

    return skinCluster


def get_mesh_components_from_tag_expression(skinCls, tag="*"):
    """Get the mesh components from the  component tag expression

    Thanks to Roy Nieterau a.k.a BigRoyNL from colorBleed for the snippet

    Args:
        skinCls (PyNode): Skin cluster node
        tag (str, optional): Component tag expression

    Returns:
        dagPath, MObject: The dagpath tho the shpe and the MObject components
    """
    geo_types = ["mesh", "nurbsSurface", "nurbsCurve"]
    for t in geo_types:
        obj = skinCls.listConnections(et=True, t=t)
        if obj:
            geo = obj[0].getShape().name()

    # Get the geo out attribute for the shape
    out_attr = cmds.deformableShape(geo, localShapeOutAttr=True)[0]

    # Get the output geometry data as MObject
    sel = OpenMaya.MSelectionList()
    sel.add(geo)
    dep = OpenMaya.MObject()
    sel.getDependNode(0, dep)
    fn_dep = OpenMaya.MFnDependencyNode(dep)
    plug = fn_dep.findPlug(out_attr, True)
    obj = plug.asMObject()

    # Use the MFnGeometryData class to query the components for a tag
    # expression
    fn_geodata = OpenMaya.MFnGeometryData(obj)

    # Components MObject
    components = fn_geodata.resolveComponentTagExpression(tag)

    dagPath = OpenMaya.MDagPath.getAPathTo(dep)
    return dagPath, components


# @utils.timeFunc
def getGeometryComponents(skinCls):
    """Get the geometry components from skincluster

    Arguments:
        skinCls (PyNode): The skincluster node

    Returns:
        dagPath: The dagpath for the components
        componets: The skincluster componets
    """
    # Brute force to try the old method using deformerSet. If fail will try
    # to use Maya 2022 compoent tag expression
    try:
        fnSet = OpenMaya.MFnSet(
            get_skin_cluster_fn(skinCls.name()).deformerSet()
        )
        members = OpenMaya.MSelectionList()
        fnSet.getMembers(members, False)
        dagPath = OpenMaya.MDagPath()
        components = OpenMaya.MObject()
        members.getDagPath(0, dagPath, components)
        return dagPath, components
    except:
        return get_mesh_components_from_tag_expression(skinCls)


def getCurrentWeights(skinCls, dagPath, components):
    """Get the skincluster weights

    Arguments:
        skinCls (PyNode): The skincluster node
        dagPath (MDagPath): The skincluster dagpath
        components (MObject): The skincluster components

    Returns:
        MDoubleArray: The skincluster weights

    """
    weights = OpenMaya.MDoubleArray()
    util = OpenMaya.MScriptUtil()
    util.createFromInt(0)
    pUInt = util.asUintPtr()
    get_skin_cluster_fn(skinCls.name()).getWeights(
        dagPath, components, weights, pUInt
    )
    return weights


def getCompleteWeights(mesh, skinCluster=None):
    """Get complete skin weights for all vertices organized by vertex index.

    This function efficiently retrieves all skin weights using OpenMaya API
    in a single batch call, then organizes them by vertex index with
    influence (joint) names as keys.

    Args:
        mesh (str): Name of the mesh.
        skinCluster (str, optional): Skin cluster name. If None, will
            auto-detect from mesh history.

    Returns:
        dict: Dictionary mapping vertex index to joint weights.
            Format: {vertex_idx: {joint_name: weight, ...}, ...}
            Only includes vertices with non-zero weights.

    Example:
        >>> weights = getCompleteWeights("pSphere1")
        >>> print(weights[0])  # Weights for vertex 0
        {'joint1': 0.5, 'joint2': 0.5}
    """
    # Auto-detect skin cluster if not provided
    if skinCluster is None:
        skinCls = getSkinCluster(mesh)
        if not skinCls:
            return {}
    else:
        if not cmds.objExists(skinCluster):
            return {}
        skinCls = pm.PyNode(skinCluster)

    # Get geometry components using existing utility
    dagPath, components = getGeometryComponents(skinCls)

    # Get all weights in one batch call (fast!)
    weightsArray = getCurrentWeights(skinCls, dagPath, components)

    # Get influence names
    influencePaths = OpenMaya.MDagPathArray()
    skinFn = get_skin_cluster_fn(skinCls.name())
    numInfluences = skinFn.influenceObjects(influencePaths)

    influenceNames = [
        OpenMaya.MFnDependencyNode(influencePaths[i].node()).name()
        for i in range(influencePaths.length())
    ]

    # Calculate number of vertices
    numVerts = int(weightsArray.length() / numInfluences)

    # Convert flat weight array to per-vertex dictionary
    weights = {}
    for vIdx in range(numVerts):
        vertWeights = {}
        for infIdx, infName in enumerate(influenceNames):
            w = weightsArray[vIdx * numInfluences + infIdx]
            if w > 0.0001:
                vertWeights[infName] = w

        if vertWeights:
            weights[vIdx] = vertWeights

    return weights


def getVertexPositions(geo):
    """Get world space positions for all vertices/CVs of a geometry.

    Supports meshes, NURBS surfaces, and NURBS curves.

    Args:
        geo (str or PyNode): Geometry object (mesh, nurbsSurface, or nurbsCurve).

    Returns:
        tuple: (positions_dict, geometry_type)
            - positions_dict: {vertex_index: [x, y, z], ...}
            - geometry_type: "mesh", "nurbsSurface", or "nurbsCurve"

    Example:
        >>> positions, geoType = getVertexPositions("pSphere1")
        >>> print(positions[0])
        [0.0, 1.0, 0.0]
    """
    if isinstance(geo, string_types):
        geo = pm.PyNode(geo)

    shape = geo.getShape()
    if shape is None:
        return {}, "unknown"

    positions = {}

    if isinstance(shape, pm.nodetypes.Mesh):
        # Use OpenMaya for efficient batch retrieval on meshes
        selList = OpenMaya.MSelectionList()
        selList.add(shape.name())
        dagPath = OpenMaya.MDagPath()
        selList.getDagPath(0, dagPath)

        meshFn = OpenMaya.MFnMesh(dagPath)
        points = OpenMaya.MPointArray()
        meshFn.getPoints(points, OpenMaya.MSpace.kWorld)

        for i in range(points.length()):
            positions[i] = [
                round(points[i].x, 6),
                round(points[i].y, 6),
                round(points[i].z, 6),
            ]
        return positions, "mesh"

    elif isinstance(shape, pm.nodetypes.NurbsSurface):
        # For NURBS surfaces, iterate CVs
        shapeName = shape.name()
        spansU = cmds.getAttr(shapeName + ".spansU")
        spansV = cmds.getAttr(shapeName + ".spansV")
        degreeU = cmds.getAttr(shapeName + ".degreeU")
        degreeV = cmds.getAttr(shapeName + ".degreeV")
        numCVsU = spansU + degreeU
        numCVsV = spansV + degreeV
        idx = 0
        for u in range(numCVsU):
            for v in range(numCVsV):
                pos = cmds.pointPosition(
                    "{}.cv[{}][{}]".format(shapeName, u, v), world=True
                )
                positions[idx] = [round(pos[0], 6), round(pos[1], 6), round(pos[2], 6)]
                idx += 1
        return positions, "nurbsSurface"

    elif isinstance(shape, pm.nodetypes.NurbsCurve):
        # For NURBS curves, iterate CVs
        shapeName = shape.name()
        spans = cmds.getAttr(shapeName + ".spans")
        degree = cmds.getAttr(shapeName + ".degree")
        numCVs = spans + degree
        for i in range(numCVs):
            pos = cmds.pointPosition("{}.cv[{}]".format(shapeName, i), world=True)
            positions[i] = [round(pos[0], 6), round(pos[1], 6), round(pos[2], 6)]
        return positions, "nurbsCurve"

    return {}, "unknown"


######################################
# Skin Collectors
######################################


def collectInfluenceWeights(skinCls, dagPath, components, dataDic):
    weights = getCurrentWeights(skinCls, dagPath, components)

    influencePaths = OpenMaya.MDagPathArray()
    numInfluences = get_skin_cluster_fn(skinCls.name()).influenceObjects(
        influencePaths
    )
    # cast to float to avoid rounding errors when dividing integers?
    dataDic["vertexCount"] = int(weights.length() / float(numInfluences))

    numComponentsPerInfluence = int(weights.length() / numInfluences)
    for ii in range(influencePaths.length()):
        influenceName = influencePaths[ii].partialPathName()
        influenceWithoutNamespace = pm.PyNode(influenceName).stripNamespace()
        # build a dictionary of {vtx: weight}. Skip 0.0 weights.
        inf_w = {
            jj: weights[jj * numInfluences + ii]
            for jj in range(numComponentsPerInfluence)
            if weights[jj * numInfluences + ii] != 0.0
        }

        # cast influenceWithoutNamespace as string otherwise it can end up
        # as DependNodeName(u'jointName') in the data.
        dataDic["weights"][str(influenceWithoutNamespace)] = inf_w


def collectBlendWeights(skinCls, dagPath, components, dataDic):
    weights = OpenMaya.MDoubleArray()
    get_skin_cluster_fn(skinCls.name()).getBlendWeights(
        dagPath, components, weights
    )
    # round the weights down. This should be safe on Dual Quat blends
    # because it is not normalized. And 6 should be more than accurate enough.
    dataDic["blendWeights"] = {
        i: round(weights[i], 6)
        for i in range(weights.length())
        if round(weights[i], 6) != 0.0
    }


def collectData(skinCls, dataDic):
    dagPath, components = getGeometryComponents(skinCls)
    collectInfluenceWeights(skinCls, dagPath, components, dataDic)
    collectBlendWeights(skinCls, dagPath, components, dataDic)

    for attr in ["skinningMethod", "normalizeWeights"]:
        dataDic[attr] = skinCls.attr(attr).get()

    dataDic["skinClsName"] = skinCls.name()


def _collectVertexPositions(obj, dataDic):
    """Collect vertex world positions and add to data dictionary.

    Stores ALL vertex positions for accurate volume-based reconstruction.
    This is necessary because the temp geometry needs exact vertex positions
    for closest-point matching to work correctly.

    Args:
        obj (PyNode): The geometry object being exported.
        dataDic (dict): Data dictionary to update with positions.
    """
    positions, geoType = getVertexPositions(obj)

    if not positions:
        return

    # Store ALL positions for accurate volume reconstruction
    dataDic["vertexPositions"] = positions
    dataDic["geometryType"] = geoType


######################################
# Skin export
######################################


def exportSkin(filePath=None, objs=None, storePositions=False, *args):
    """Export skinCluster data to file.

    Args:
        filePath (str, optional): File path for export. If None, opens dialog.
        objs (list, optional): Objects to export. If None, uses selection.
        storePositions (bool): If True, stores vertex world positions for
            volume-based import fallback when vertex counts don't match.
            Increases file size. Default False for backward compatibility.

    Returns:
        bool: True if export successful, False otherwise.
    """
    if not objs:
        if pm.selected():
            objs = pm.selected()
        else:
            pm.displayWarning("Please Select One or more objects")
            return False

    packDic = {"objs": [], "objDDic": [], "bypassObj": []}

    if not filePath:

        f2 = "jSkin ASCII  (*{});;gSkin Binary (*{})".format(
            FILE_JSON_EXT, FILE_EXT
        )
        f3 = ";;All Files (*.*)"
        fileFilters = f2 + f3
        filePath = pm.fileDialog2(fileMode=0, fileFilter=fileFilters)
        if filePath:
            filePath = filePath[0]

        else:
            return False

    if not filePath.endswith(FILE_EXT) and not filePath.endswith(
        FILE_JSON_EXT
    ):
        # filePath += file_ext
        pm.displayWarning("Not valid file extension for: {}".format(filePath))
        return

    _, file_ext = os.path.splitext(filePath)
    # object parsing
    for obj in objs:
        skinCls = getSkinCluster(obj)
        if not skinCls:
            pm.displayWarning(
                obj.name() + ": Skipped because don't have Skin Cluster"
            )
            pass
        else:
            # start by pruning by a tiny amount. Enough to not make  noticeable
            # change to the skin, but it will remove infinitely small weights.
            # Otherwise, compressing will do almost nothing!
            # if isinstance(obj.getShape(), pm.nodetypes.Mesh):
                # TODO: Implement pruning on nurbs. Less straight-forward
                # pm.skinPercent(skinCls, obj, pruneWeights=0.0001)

            dataDic = {
                "weights": {},
                "blendWeights": [],
                "skinClsName": "",
                "objName": "",
                "nameSpace": "",
                "vertexCount": 0,
                "skinDataFormat": "compressed",
            }

            dataDic["objName"] = obj.name()
            dataDic["nameSpace"] = obj.namespace()

            collectData(skinCls, dataDic)

            # Store vertex positions for volume-based import if requested
            if storePositions:
                _collectVertexPositions(obj, dataDic)

            packDic["objs"].append(obj.name())
            packDic["objDDic"].append(dataDic)
            exportMsg = "Exported skinCluster {} ({} influences, {} points) {}"
            pm.displayInfo(
                exportMsg.format(
                    skinCls.name(),
                    len(dataDic["weights"].keys()),
                    len(dataDic["blendWeights"]),
                    obj.name(),
                )
            )

    if packDic["objs"]:
        if filePath.endswith(FILE_EXT):
            with open(filePath, "wb") as fp:
                pickle.dump(packDic, fp, pickle.HIGHEST_PROTOCOL)
        else:
            with open(filePath, "w") as fp:
                json.dump(packDic, fp, indent=4, sort_keys=True)

        return True


@utils.timeFunc
def exportSkinPack(packPath=None, objs=None, use_json=False, storePositions=False, *args):
    """Export multiple skinClusters to a skin pack.

    Args:
        packPath (str, optional): Pack file path. If None, opens dialog.
        objs (list, optional): Objects to export. If None, uses selection.
        use_json (bool): If True, use JSON format. Default False (binary).
        storePositions (bool): If True, stores vertex world positions for
            volume-based import fallback. Default False.
    """
    if use_json:
        file_ext = FILE_JSON_EXT
    else:
        file_ext = FILE_EXT

    if not objs:
        if pm.selected():
            objs = pm.selected()
        else:
            pm.displayWarning("Please Select Some Objects")
            return

    packDic = {"packFiles": [], "rootPath": []}

    if packPath is None:
        packPath = pm.fileDialog2(
            fileMode=0, fileFilter="mGear skinPack (*%s)" % PACK_EXT
        )
        if not packPath:
            return
        packPath = packPath[0]
        if not packPath.endswith(PACK_EXT):
            packPath += PACK_EXT

    if not packPath.endswith(PACK_EXT):
        pm.displayWarning("Not valid file extension for: {}".format(packPath))
        return

    packDic["rootPath"], packName = os.path.split(packPath)

    for obj in objs:
        fileName = obj.stripNamespace() + file_ext
        filePath = os.path.join(packDic["rootPath"], fileName)
        if exportSkin(filePath, [obj], storePositions=storePositions):
            packDic["packFiles"].append(fileName)
            pm.displayInfo(filePath)
        else:
            pm.displayWarning(
                obj.name() + ": Skipped because don't have Skin Cluster"
            )

    if packDic["packFiles"]:
        data_string = json.dumps(packDic, indent=4, sort_keys=True)
        with open(packPath, "w") as f:
            f.write(data_string + "\n")
        pm.displayInfo("Skin Pack exported: " + packPath)
    else:
        pm.displayWarning(
            "Any of the selected objects have Skin Cluster. "
            "Skin Pack export aborted."
        )


def exportJsonSkinPack(packPath=None, objs=None, storePositions=False, *args):
    """Export multiple skinClusters to a JSON skin pack.

    Args:
        packPath (str, optional): Pack file path. If None, opens dialog.
        objs (list, optional): Objects to export. If None, uses selection.
        storePositions (bool): If True, stores vertex world positions for
            volume-based import fallback. Default False.
    """
    exportSkinPack(packPath, objs, use_json=True, storePositions=storePositions)


def exportJsonSkinPackWithPositions(packPath=None, objs=None, *args):
    """Export multiple skinClusters to JSON with vertex positions.

    This is a convenience wrapper that enables storePositions for
    volume-based import support when vertex counts don't match.

    Args:
        packPath (str, optional): Pack file path. If None, opens dialog.
        objs (list, optional): Objects to export. If None, uses selection.
    """
    exportJsonSkinPack(packPath, objs, storePositions=True)


######################################
# Skin setters
######################################


# @utils.timeFunc
def setInfluenceWeights(skinCls, dagPath, components, dataDic, compressed):
    """Sets influence weights for a given skin cluster.

    Args:
        skinCls (PyNode): The skin cluster node.
        dagPath (MDagPath): The DAG path of the mesh.
        components (MObject): The component selection (e.g., vertices).
        dataDic (dict): A dictionary containing influence weights.
        compressed (bool): Whether to use compressed weight format.
    """
    unusedImports = []
    weights = getCurrentWeights(skinCls, dagPath, components)

    influencePaths = OpenMaya.MDagPathArray()
    skinFn = get_skin_cluster_fn(skinCls.name())  # Cache function call
    numInfluences = skinFn.influenceObjects(influencePaths)

    numComponentsPerInfluence = int(weights.length() / numInfluences)

    # Precompute influence names (Avoiding PyMEL)
    influenceMap = {
        OpenMaya.MFnDependencyNode(influencePaths[ii].node()).name(): ii
        for ii in range(influencePaths.length())
    }

    for importedInfluence, wtValues in dataDic["weights"].items():
        influenceIndex = influenceMap.get(importedInfluence)
        if influenceIndex is not None:
            if compressed:
                for jj in range(numComponentsPerInfluence):
                    wt = wtValues.get(jj, wtValues.get(str(jj), 0.0))

                    weights.set(wt, jj * numInfluences + influenceIndex)
            else:
                for jj, wt in enumerate(wtValues):
                    weights.set(wt, jj * numInfluences + influenceIndex)
        else:
            unusedImports.append(importedInfluence)

    # influenceIndices assignment
    influenceIndices = OpenMaya.MIntArray()
    influenceIndices.setLength(numInfluences)
    for ii in range(numInfluences):
        influenceIndices[ii] = ii  # Direct assignment is faster

    # Apply the weights
    skinFn.setWeights(dagPath, components, influenceIndices, weights, False)


# @utils.timeFunc
def setBlendWeights(skinCls, dagPath, components, dataDic, compressed):
    if compressed:
        # The compressed format skips 0.0 weights. If the key is empty,
        # set it to 0.0. JSON keys can't be integers. The vtx number key
        # is unicode. example: vtx[35] would be: u"35": 0.6974,
        # But the binary format is still an int, so cast the key to int.
        blendWeights = OpenMaya.MDoubleArray(dataDic["vertexCount"])
        for key, value in dataDic["blendWeights"].items():
            blendWeights.set(value, int(key))
    else:
        # The original weight format was a full list for every vertex
        # For backwards compatibility on older skin files:
        blendWeights = OpenMaya.MDoubleArray(len(dataDic["blendWeights"]))
        for ii, w in enumerate(dataDic["blendWeights"]):
            blendWeights.set(w, ii)

    get_skin_cluster_fn(skinCls.name()).setBlendWeights(
        dagPath, components, blendWeights
    )


######################################
# Partial Vertex Weight Updates
######################################


def setVertexWeights(skinCluster, vertexWeights, normalize=False):
    """Set skin weights for specific vertices only, preserving others.

    This function is optimized for PARTIAL updates where you only want to
    modify a subset of vertices while preserving existing weights on all
    other vertices. It directly manipulates the weight array in memory
    and applies all changes in a single batch call.

    Use this instead of setInfluenceWeights when:
    - You only need to update a subset of vertices
    - You want to preserve existing weights on non-affected vertices
    - Performance is critical for partial updates

    Use setInfluenceWeights instead when:
    - You're importing a complete skin file
    - You want to replace ALL weights on the mesh

    Args:
        skinCluster (str): Name of the skin cluster.
        vertexWeights (dict): Weight data per vertex.
            Format: {vertex_idx: {influence_name: weight, ...}, ...}
            Only vertices in this dict will be modified.
        normalize (bool): If True, normalize weights after setting.
            Defaults to False (assumes input is already normalized).

    Returns:
        bool: True if successful, False otherwise.

    Example:
        >>> # Update only vertices 0, 5, and 10
        >>> weights = {
        ...     0: {"joint1": 0.5, "joint2": 0.5},
        ...     5: {"joint1": 1.0},
        ...     10: {"joint2": 0.7, "joint3": 0.3},
        ... }
        >>> setVertexWeights("skinCluster1", weights)
    """
    skinCls = pm.PyNode(skinCluster)
    dagPath, components = getGeometryComponents(skinCls)

    # Get current weights
    weightsArray = getCurrentWeights(skinCls, dagPath, components)

    # Get influence info
    skinFn = get_skin_cluster_fn(skinCluster)
    influencePaths = OpenMaya.MDagPathArray()
    numInfluences = skinFn.influenceObjects(influencePaths)

    # Build influence name to index map
    influenceMap = {}
    for i in range(influencePaths.length()):
        infName = OpenMaya.MFnDependencyNode(influencePaths[i].node()).name()
        influenceMap[infName] = i

    numVerts = int(weightsArray.length() / numInfluences)

    # Modify weights for specified vertices only
    for vIdx, vertWeights in vertexWeights.items():
        if vIdx >= numVerts:
            continue

        # Zero out all influences for this vertex first
        for infIdx in range(numInfluences):
            weightsArray.set(0.0, vIdx * numInfluences + infIdx)

        # Set the specified weights
        for infName, w in vertWeights.items():
            if infName in influenceMap:
                infIdx = influenceMap[infName]
                weightsArray.set(w, vIdx * numInfluences + infIdx)

    # Build influence indices array
    influenceIndices = OpenMaya.MIntArray()
    influenceIndices.setLength(numInfluences)
    for i in range(numInfluences):
        influenceIndices[i] = i

    # Apply all weights in one batch call
    skinFn.setWeights(dagPath, components, influenceIndices, weightsArray, normalize)

    return True


def getInfluenceMap(skinCluster):
    """Get a mapping of influence names to their indices.

    Args:
        skinCluster (str): Name of the skin cluster.

    Returns:
        dict: Mapping of {influence_name: index, ...}
    """
    skinFn = get_skin_cluster_fn(skinCluster)
    influencePaths = OpenMaya.MDagPathArray()
    skinFn.influenceObjects(influencePaths)

    influenceMap = {}
    for i in range(influencePaths.length()):
        infName = OpenMaya.MFnDependencyNode(influencePaths[i].node()).name()
        influenceMap[infName] = i

    return influenceMap


def initializeToInfluence(skinCluster, influenceName):
    """Initialize all vertices to a single influence with weight 1.0.

    Useful for setting up a "static" or "base" joint that holds
    all vertices before applying partial weight updates.

    Args:
        skinCluster (str): Name of the skin cluster.
        influenceName (str): Name of the influence to set to 1.0.

    Returns:
        bool: True if successful, False otherwise.
    """
    skinCls = pm.PyNode(skinCluster)
    dagPath, components = getGeometryComponents(skinCls)

    skinFn = get_skin_cluster_fn(skinCluster)
    influencePaths = OpenMaya.MDagPathArray()
    numInfluences = skinFn.influenceObjects(influencePaths)

    # Find influence index
    influenceIdx = None
    for i in range(influencePaths.length()):
        infName = OpenMaya.MFnDependencyNode(influencePaths[i].node()).name()
        if infName == influenceName:
            influenceIdx = i
            break

    if influenceIdx is None:
        pm.displayWarning(
            "Influence '{}' not found in skin cluster".format(influenceName)
        )
        return False

    # Get current weights and modify
    weightsArray = getCurrentWeights(skinCls, dagPath, components)
    numVerts = int(weightsArray.length() / numInfluences)

    for vIdx in range(numVerts):
        # Zero all influences
        for infIdx in range(numInfluences):
            weightsArray.set(0.0, vIdx * numInfluences + infIdx)
        # Set target influence to 1.0
        weightsArray.set(1.0, vIdx * numInfluences + influenceIdx)

    # Build influence indices
    influenceIndices = OpenMaya.MIntArray()
    influenceIndices.setLength(numInfluences)
    for i in range(numInfluences):
        influenceIndices[i] = i

    skinFn.setWeights(dagPath, components, influenceIndices, weightsArray, False)

    return True


# @utils.timeFunc
def setData(skinCls, dataDic, compressed):
    dagPath, components = getGeometryComponents(skinCls)
    setInfluenceWeights(skinCls, dagPath, components, dataDic, compressed)
    for attr in ["skinningMethod", "normalizeWeights"]:
        skinCls.attr(attr).set(dataDic[attr])
    setBlendWeights(skinCls, dagPath, components, dataDic, compressed)


######################################
# Skin import
######################################


def _buildPositionLookup(sourcePositions, precision=6):
    """Build a hash lookup table for exact position matching.

    Args:
        sourcePositions (dict): {vertex_index: [x, y, z], ...} source positions.
        precision (int): Decimal places to round positions for matching.

    Returns:
        dict: {(x, y, z): vertex_index, ...} for O(1) lookup.
    """
    lookup = {}
    for idx, pos in sourcePositions.items():
        # Round to precision and convert to tuple for hashability
        key = (
            round(pos[0], precision),
            round(pos[1], precision),
            round(pos[2], precision),
        )
        lookup[key] = int(idx)
    return lookup


def _findClosestSourceVertices(targetPositions, sourcePositions, positionLookup):
    """Find closest source vertex for each target vertex.

    Uses exact position matching first (O(1)), then falls back to
    closest-point search for non-matching vertices.

    Args:
        targetPositions (dict): {vertex_index: [x, y, z], ...} target positions.
        sourcePositions (dict): {vertex_index: [x, y, z], ...} source positions.
        positionLookup (dict): Hash table for exact position matching.

    Returns:
        tuple: (mapping_dict, exact_matches, closest_matches, cancelled)
            - mapping_dict: {target_idx: source_idx, ...}
            - exact_matches: count of exact position matches
            - closest_matches: count of closest-point lookups
            - cancelled: True if user cancelled
    """
    mapping = {}
    exactMatches = 0
    closestMatches = 0

    # Try to use numpy for faster distance calculations
    try:
        import numpy as np
        useNumpy = True
        # Pre-build numpy arrays for source positions
        srcIndices = []
        srcCoords = []
        for idx, pos in sourcePositions.items():
            srcIndices.append(int(idx))
            srcCoords.append(pos)
        srcIndices = np.array(srcIndices)
        srcCoords = np.array(srcCoords)
    except ImportError:
        useNumpy = False

    # Setup progress bar
    numTargets = len(targetPositions)
    gMainProgressBar = pm.mel.eval("$tmp = $gMainProgressBar")
    cmds.progressBar(
        gMainProgressBar,
        edit=True,
        beginProgress=True,
        isInterruptable=True,
        status="Mapping skin weights by position...",
        maxValue=numTargets,
    )

    try:
        updateInterval = max(1, numTargets // 100)  # Update every 1%

        for i, (targetIdx, targetPos) in enumerate(targetPositions.items()):
            # Check for cancel
            if i % updateInterval == 0:
                if cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
                    pm.displayWarning("Skin import cancelled by user")
                    return mapping, exactMatches, closestMatches, True
                cmds.progressBar(gMainProgressBar, edit=True, step=updateInterval)

            # Try exact position match first (O(1) lookup)
            posKey = (
                round(targetPos[0], 6),
                round(targetPos[1], 6),
                round(targetPos[2], 6),
            )
            if posKey in positionLookup:
                mapping[targetIdx] = positionLookup[posKey]
                exactMatches += 1
                continue

            # Fall back to closest-point search
            if useNumpy:
                # Vectorized distance calculation
                targetCoord = np.array(targetPos)
                diffs = srcCoords - targetCoord
                distsSq = np.sum(diffs * diffs, axis=1)
                closestIdx = srcIndices[np.argmin(distsSq)]
            else:
                # Python fallback
                minDist = float("inf")
                closestIdx = 0
                for idx, srcPos in sourcePositions.items():
                    idx = int(idx)
                    dx = targetPos[0] - srcPos[0]
                    dy = targetPos[1] - srcPos[1]
                    dz = targetPos[2] - srcPos[2]
                    dist = dx * dx + dy * dy + dz * dz
                    if dist < minDist:
                        minDist = dist
                        closestIdx = idx

            mapping[targetIdx] = closestIdx
            closestMatches += 1

    finally:
        cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

    return mapping, exactMatches, closestMatches, False


def _getSourceVertexWeights(sourceVertexIdx, dataDic, compressed):
    """Get weights for a specific source vertex from imported data.

    Args:
        sourceVertexIdx (int): Source vertex index.
        dataDic (dict): Imported skin data.
        compressed (bool): Whether data uses compressed format.

    Returns:
        dict: {influence_name: weight, ...} for this vertex.
    """
    vertWeights = {}

    for influence, wtValues in dataDic["weights"].items():
        if compressed:
            # Compressed format: {idx: weight, ...} or {"idx": weight, ...}
            wt = wtValues.get(sourceVertexIdx, wtValues.get(str(sourceVertexIdx), 0.0))
        else:
            # Legacy format: list of weights
            if sourceVertexIdx < len(wtValues):
                wt = wtValues[sourceVertexIdx]
            else:
                wt = 0.0

        if wt > 0.0001:
            vertWeights[influence] = wt

    return vertWeights


def _importSkinVolumeMethod(objNode, targetSkinCluster, dataDic, compressed):
    """Import skin weights using volume/closest-point matching.

    Called when vertex counts don't match and vertexMismatchMode allows it.
    Uses optimized position-based weight mapping:
    1. Exact position matches use O(1) hash lookup (fast for unchanged vertices)
    2. Non-matching vertices use closest-point search (numpy-accelerated if available)
    3. Progress bar allows user to cancel long operations

    Args:
        objNode (PyNode): Target mesh/surface/curve node.
        targetSkinCluster (PyNode): Target skin cluster (already created).
        dataDic (dict): Imported skin data dictionary.
        compressed (bool): Whether data uses compressed format.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        storedPositions = dataDic.get("vertexPositions", {})

        if not storedPositions:
            # No stored positions - skip import
            objName = objNode.name() if hasattr(objNode, "name") else str(objNode)
            pm.displayWarning(
                "Skipping import for '{}': No vertex positions stored in skin "
                "file. To use volume-based import, re-export with 'Export Skin "
                "Pack ASCII with Position Data'.".format(objName)
            )
            return False

        pm.displayInfo(
            "Using stored vertex positions ({} points) for "
            "position-based weight transfer".format(len(storedPositions))
        )

        # Get target vertex positions
        targetPositions, _ = getVertexPositions(objNode)
        if not targetPositions:
            pm.displayWarning("Failed to get target vertex positions")
            return False

        pm.displayInfo(
            "Mapping {} target vertices to {} source vertices...".format(
                len(targetPositions), len(storedPositions)
            )
        )

        # Build position lookup for exact matching
        positionLookup = _buildPositionLookup(storedPositions)

        # Find closest source vertex for each target vertex
        vertexMapping, exactMatches, closestMatches, cancelled = (
            _findClosestSourceVertices(
                targetPositions, storedPositions, positionLookup
            )
        )

        if cancelled:
            return False

        pm.displayInfo(
            "Position matching: {} exact, {} closest-point".format(
                exactMatches, closestMatches
            )
        )

        # Build weight mapping: target vertex -> weights from closest source
        targetWeights = {}
        for targetIdx, sourceIdx in vertexMapping.items():
            srcWeights = _getSourceVertexWeights(sourceIdx, dataDic, compressed)
            if srcWeights:
                targetWeights[targetIdx] = srcWeights

        if not targetWeights:
            pm.displayWarning("No weights could be mapped")
            return False

        # Apply weights using setVertexWeights
        pm.displayInfo("Applying weights to {} vertices...".format(len(targetWeights)))
        setVertexWeights(targetSkinCluster.name(), targetWeights, normalize=True)

        # Apply skinning method from imported data
        for attr in ["skinningMethod", "normalizeWeights"]:
            if attr in dataDic:
                targetSkinCluster.attr(attr).set(dataDic[attr])

        pm.displayInfo(
            "Successfully mapped weights for {} vertices".format(len(targetWeights))
        )
        return True

    except Exception as e:
        pm.displayWarning("Volume-based import failed: {}".format(e))
        import traceback
        traceback.print_exc()
        return False


def _getObjsFromSkinFile(filePath=None, *args):
    # retrive the object names inside gSkin file
    if not filePath:
        f1 = "mGear Skin (*{0} *{1})".format(FILE_EXT, FILE_JSON_EXT)
        f2 = ";;gSkin Binary (*{0});;jSkin ASCII  (*{1})".format(
            FILE_EXT, FILE_JSON_EXT
        )
        f3 = ";;All Files (*.*)"
        fileFilters = f1 + f2 + f3
        filePath = pm.fileDialog2(fileMode=1, fileFilter=fileFilters)
    if not filePath:
        return
    if not isinstance(filePath, string_types):
        filePath = filePath[0]

    # Read in the file
    with open(filePath, "r") as fp:
        if filePath.endswith(FILE_EXT):
            data = pickle.load(fp)
        else:
            data = json.load(fp)

        return data["objs"]


def getObjsFromSkinFile(filePath=None, *args):
    objs = _getObjsFromSkinFile(filePath)
    if objs:
        for x in objs:
            print(x)


# @utils.timeFunc
def importSkin(filePath=None, vertexMismatchMode="auto", *args):
    """Import skinCluster data from file.

    Args:
        filePath (str, optional): File path for import. If None, opens dialog.
        vertexMismatchMode (str): Behavior when vertex counts don't match:
            - "skip": Skip import with warning
            - "closestPoint": Use closest point matching to transfer weights
            - "auto": Index-based first, fallback to closestPoint (default)

    Returns:
        list: Object names that were imported using the volume method.
            Empty list if all objects used standard index-based import.
    """
    if not filePath:
        f1 = "mGear Skin (*{0} *{1})".format(FILE_EXT, FILE_JSON_EXT)
        f2 = ";;gSkin Binary (*{0});;jSkin ASCII  (*{1})".format(
            FILE_EXT, FILE_JSON_EXT
        )
        f3 = ";;All Files (*.*)"
        fileFilters = f1 + f2 + f3
        filePath = pm.fileDialog2(fileMode=1, fileFilter=fileFilters)
    if not filePath:
        return []
    if not isinstance(filePath, string_types):
        filePath = filePath[0]

    # Read in the file
    if filePath.endswith(FILE_EXT):
        with open(filePath, "rb") as fp:
            dataPack = pickle.load(fp)
    else:
        with open(filePath, "r") as fp:
            dataPack = json.load(fp)

    volumeImported = []

    for data in dataPack["objDDic"]:
        # This checks if the jSkin file has the new style compressed format.
        # use a skinDataFormat key to check for backwards compatibility.
        # If it doesn't exist, just continue with the old method.
        compressed = False
        if "skinDataFormat" in data:
            if data["skinDataFormat"] == "compressed":
                compressed = True

        try:
            skinCluster = False
            objName = data["objName"]
            objNode = pm.PyNode(objName)

            try:
                # use getShapes() else meshes with 2+ shapes will fail.
                # TODO: multiple shape nodes is not currently supported in
                # the file structure! It should raise an error.
                # Also noIntermediate otherwise it will count shapeOrig nodes.
                objShapes = objNode.getShapes(noIntermediate=True)

                if isinstance(objNode.getShape(), pm.nodetypes.Mesh):
                    meshVertices = pm.polyEvaluate(objShapes, vertex=True)
                elif isinstance(objNode.getShape(), pm.nodetypes.NurbsSurface):
                    # if nurbs, count the cvs instead of the vertices.
                    # Use cmds to get spans and degree for CV count
                    meshVertices = 0
                    for shape in objShapes:
                        shapeName = shape.name()
                        spansU = cmds.getAttr(shapeName + ".spansU")
                        spansV = cmds.getAttr(shapeName + ".spansV")
                        degreeU = cmds.getAttr(shapeName + ".degreeU")
                        degreeV = cmds.getAttr(shapeName + ".degreeV")
                        meshVertices += (spansU + degreeU) * (spansV + degreeV)
                elif isinstance(objNode.getShape(), pm.nodetypes.NurbsCurve):
                    # Use cmds to get spans and degree for CV count
                    meshVertices = 0
                    for shape in objShapes:
                        shapeName = shape.name()
                        spans = cmds.getAttr(shapeName + ".spans")
                        degree = cmds.getAttr(shapeName + ".degree")
                        meshVertices += spans + degree
                else:
                    # TODO: Implement other skinnable objs like lattices.
                    meshVertices = 0

                if compressed:
                    importedVertices = data["vertexCount"]
                else:
                    importedVertices = len(data["blendWeights"])

                vertexMismatch = meshVertices != importedVertices
            except Exception:
                vertexMismatch = False

            # Handle vertex count mismatch based on mode
            if vertexMismatch:
                if vertexMismatchMode == "skip":
                    warningMsg = "Vertex counts on {} do not match. {} != {}"
                    pm.displayWarning(
                        warningMsg.format(
                            objName, meshVertices, importedVertices
                        )
                    )
                    continue
                elif vertexMismatchMode in ("closestPoint", "auto"):
                    pm.displayInfo(
                        "Vertex count mismatch on {}. Using closest-point "
                        "matching ({} -> {} vertices)...".format(
                            objName, importedVertices, meshVertices
                        )
                    )
                    # Ensure skin cluster exists for volume import
                    skinCluster = getSkinCluster(objNode)
                    if not skinCluster:
                        try:
                            joints = list(data["weights"].keys())
                            skinName = data["skinClsName"].replace("|", "")
                            skinCluster = pm.skinCluster(
                                joints, objNode, tsb=True, nw=2, n=skinName
                            )
                            if isinstance(skinCluster, list):
                                skinCluster = skinCluster[0]
                        except Exception:
                            sceneJoints = set(
                                [pm.PyNode(x).name() for x in pm.ls(type="joint")]
                            )
                            notFound = []
                            for j in data["weights"].keys():
                                if j not in sceneJoints:
                                    notFound.append(str(j))
                            pm.displayWarning(
                                "Object: {} Skipped. Can't find corresponding "
                                "joints: {}".format(objName, notFound)
                            )
                            continue

                    # Use volume-based import
                    success = _importSkinVolumeMethod(
                        objNode, skinCluster, data, compressed
                    )
                    if success:
                        volumeImported.append(objName)
                        print(
                            "Imported skin (volume method) for: {}".format(objName)
                        )
                    else:
                        print(
                            "Skipped skin import for: {} (volume method failed, "
                            "see warning above)".format(objName)
                        )
                    continue

            # Standard index-based import (vertex counts match)
            if getSkinCluster(objNode):
                skinCluster = getSkinCluster(objNode)
            else:
                try:
                    joints = list(data["weights"].keys())
                    # strip | from longName, or skinCluster command may fail.
                    skinName = data["skinClsName"].replace("|", "")
                    skinCluster = pm.skinCluster(
                        joints, objNode, tsb=True, nw=2, n=skinName
                    )
                except Exception:
                    sceneJoints = set(
                        [pm.PyNode(x).name() for x in pm.ls(type="joint")]
                    )
                    notFound = []
                    for j in data["weights"].keys():
                        if j not in sceneJoints:
                            notFound.append(str(j))
                    pm.displayWarning(
                        "Object: " + objName + " Skiped. Can't "
                        "found corresponding deformer for the "
                        "following joints: " + str(notFound)
                    )
                    continue

            if isinstance(skinCluster, list):
                skinCluster = skinCluster[0]

            if skinCluster:
                setData(skinCluster, data, compressed)
                print("Imported skin for: {}".format(objName))

        except Exception:
            warningMsg = "Object: {} Skipped. Can NOT be found in the scene"
            pm.displayWarning(warningMsg.format(objName))

    return volumeImported


@utils.timeFunc
def importSkinPack(filePath=None, *args):
    """Import skin data from a skin pack file.

    Args:
        filePath (str, optional): File path for import. If None, opens dialog.

    Returns:
        list: Object names that were imported using the volume method.
            Empty list if all objects used standard index-based import.
    """
    if not filePath:
        filePath = pm.fileDialog2(
            fileMode=1, fileFilter="mGear skinPack (*%s)" % PACK_EXT
        )
    if not filePath:
        return []
    if not isinstance(filePath, string_types):
        filePath = filePath[0]

    volumeImported = []
    with open(filePath) as fp:
        packDic = json.load(fp)
        for pFile in packDic["packFiles"]:
            skinFilePath = os.path.join(os.path.split(filePath)[0], pFile)
            result = importSkin(skinFilePath)
            volumeImported.extend(result)

    return volumeImported


######################################
# Skin Copy
######################################


@utils.timeFunc
def skinCopy(sourceMesh=None, targetMesh=None, *args, **kwargs):
    if not sourceMesh or not targetMesh:
        if len(pm.selected()) >= 2:
            sourceMesh = pm.selected()[-1]
            targetMeshes = pm.selected()[:-1]
        else:
            pm.displayWarning(
                "Please select target mesh/meshes and source "
                "mesh with skinCluster."
            )
            return
    else:
        targetMeshes = [targetMesh]

        # we check this here, because if not need to check when we work
        # base on selection.
        if isinstance(sourceMesh, string_types):
            sourceMesh = pm.PyNode(sourceMesh)

    for targetMesh in targetMeshes:
        if isinstance(targetMesh, string_types):
            targetMesh = pm.PyNode(targetMesh)

        ss = getSkinCluster(sourceMesh)

        if ss:
            skinMethod = ss.skinningMethod.get()
            oDef = pm.skinCluster(sourceMesh, query=True, influence=True)
            # strip | from longName, or skinCluster command may fail.
            # skinName = targetMesh.name().replace('|', '') + "_skinCluster"
            if "name" in kwargs.keys():
                skinName = kwargs["name"]
            else:
                skinName = targetMesh.name() + "_skinCluster"
            skinCluster = pm.skinCluster(
                oDef, targetMesh, tsb=True, nw=1, n=skinName
            )[0]
            pm.copySkinWeights(
                sourceSkin=ss.stripNamespace(),
                destinationSkin=skinCluster.name(),
                noMirror=True,
                influenceAssociation="oneToOne",
                smooth=True,
                normalize=True,
            )
            skinCluster.skinningMethod.set(skinMethod)
        else:
            errorMsg = "Source Mesh : {} doesn't have a skinCluster."
            pm.displayError(errorMsg.format(sourceMesh.name()))


def skin_copy_add(sourceMesh=None, targetMesh=None, layer_name=None, *args):
    """
    Copies skinning information from a source mesh to a target mesh, adding/Stacking the
    new skinning on top of any existing skin clusters on the target mesh.

    This function first checks if there is an existing skin cluster on the target
    mesh. If found, it disconnects the output geometry of this skin cluster to
    preserve the original skinning setup. After copying the skin weights from the
    source mesh to the target mesh using `skin.skinCopy`, it reconnects the
    original geometry to the newly created skin cluster on the target mesh, ensuring
    that the original skinning is not lost but enhanced with the new skinning
    information.

    Args:
        sourceMesh (str, optional): The name of the source mesh from which to copy
            the skinning information. Defaults to None.
        targetMesh (str, optional): The name of the target mesh to which the skinning
            information will be applied. Defaults to None.
        layer_name (str, optional): Custom Layer name for the skinCluster Node
        *args: Additional arguments passed to the function. Not used in the
            current implementation.

    Returns:
        PyNode: New skin cluster
    """
    previous_skin = getSkinCluster(targetMesh, first_SC=True)
    if previous_skin:
        # Disconnect the original skin cluster's output geometry
        pm.disconnectAttr(previous_skin.outputGeometry[0])
        orig_shape = previous_skin.originalGeometry[0].inputs(shapes=True)[0]
        print(orig_shape)

    # set name
    if layer_name:
        sc_name = "{}_{}_skinCluster".format(targetMesh.name(), layer_name)
    else:
        sc_name = None
    # Copy the skin from sourceMesh to targetMesh
    skinCopy(sourceMesh, targetMesh, name=sc_name)
    new_skin = getSkinCluster(targetMesh, first_SC=True)

    if previous_skin:
        # Reconnect the original geometry to the new skin cluster
        pm.connectAttr(
            previous_skin.outputGeometry[0],
            new_skin.input[0].inputGeometry,
            f=True,
        )
        new_orig_shape = new_skin.originalGeometry[0].inputs(shapes=True)
        pm.connectAttr(
            orig_shape.outMesh, new_skin.originalGeometry[0], f=True
        )

        # Clean up if there's a new original shape connected
        if new_orig_shape:
            pm.delete(new_orig_shape)

    return new_skin


def _skinCopyPartialExecute(sourceMesh, vertices, normalize=True):
    """Execute the partial skin copy operation.

    Strategy:
        1. Store original weights
        2. Apply copySkinWeights to all vertices
        3. Store copied weights
        4. Restore original weights (fast batch with setWeights)
        5. Apply copied weights to selected vertices only (setVertexWeights)

    Args:
        sourceMesh: Source mesh name or node with skinCluster.
        vertices (list): List of vertex components to copy weights to.
        normalize (bool): Normalize weights after copying.

    """
    sourceName = str(sourceMesh)

    # Validate source skinCluster
    sourceSkin = getSkinCluster(sourceMesh)
    if not sourceSkin:
        cmds.warning(
            "Source mesh '{}' has no skinCluster.".format(sourceName)
        )
        return False

    sourceSkinName = str(sourceSkin)

    # Get source influences
    sourceInfluences = cmds.skinCluster(
        sourceSkinName, query=True, influence=True
    )

    # Group vertices by target mesh and extract indices
    verticesByMesh = {}
    for vtx in vertices:
        vtxStr = str(vtx)
        nodeName = vtxStr.split(".")[0]
        # Check if it's a shape node and get transform
        nodeType = cmds.nodeType(nodeName)
        if nodeType == "mesh":
            parents = cmds.listRelatives(nodeName, parent=True)
            if parents:
                nodeName = parents[0]
        # Extract vertex index
        vtxIdx = int(vtxStr.split("[")[1].split("]")[0])
        if nodeName not in verticesByMesh:
            verticesByMesh[nodeName] = []
        verticesByMesh[nodeName].append(vtxIdx)

    # Process each target mesh
    totalVertices = 0
    for meshName, vtxIndices in verticesByMesh.items():
        targetSkin = getSkinCluster(meshName)

        if not targetSkin:
            cmds.warning(
                "Target mesh '{}' has no skinCluster, skipping.".format(
                    meshName
                )
            )
            continue

        targetSkinName = str(targetSkin)
        targetSkinNode = pm.PyNode(targetSkinName)

        # Get current target influences
        targetInfluences = cmds.skinCluster(
            targetSkinName, query=True, influence=True
        )

        # Add missing influences from source to target
        for inf in sourceInfluences:
            if inf not in targetInfluences:
                try:
                    cmds.skinCluster(
                        targetSkinName,
                        edit=True,
                        addInfluence=inf,
                        weight=0.0,
                    )
                except Exception:
                    pass

        # Get geometry components and skin function
        dagPath, components = getGeometryComponents(targetSkinNode)
        skinFn = get_skin_cluster_fn(targetSkinName)
        influencePaths = OpenMaya.MDagPathArray()
        numInfluences = skinFn.influenceObjects(influencePaths)

        # 1. Store original weights
        originalWeights = getCurrentWeights(targetSkinNode, dagPath, components)

        # 2. Apply copySkinWeights to all vertices
        cmds.copySkinWeights(
            sourceSkin=sourceSkinName,
            destinationSkin=targetSkinName,
            noMirror=True,
            surfaceAssociation="closestPoint",
            influenceAssociation=["oneToOne", "closestJoint", "name"],
            normalize=normalize,
        )

        # 3. Store copied weights
        copiedWeights = getCurrentWeights(targetSkinNode, dagPath, components)

        # 4. Merge: replace only selected vertex weights in original array
        for vtxIdx in vtxIndices:
            for infIdx in range(numInfluences):
                arrayIdx = vtxIdx * numInfluences + infIdx
                originalWeights.set(copiedWeights[arrayIdx], arrayIdx)

        # 5. Apply merged weights in one batch
        influenceIndices = OpenMaya.MIntArray()
        influenceIndices.setLength(numInfluences)
        for i in range(numInfluences):
            influenceIndices[i] = i

        skinFn.setWeights(
            dagPath, components, influenceIndices, originalWeights, normalize
        )

        totalVertices += len(vtxIndices)

    cmds.inViewMessage(
        amg="Copied skin to <hl>{}</hl> vertices".format(totalVertices),
        pos="midCenter",
        fade=True,
    )
    return True


class SkinCopyPartialUI(QtWidgets.QDialog):
    """UI for copying skin weights to selected vertices."""

    def __init__(self, parent=None):
        super(SkinCopyPartialUI, self).__init__(parent)
        self.setWindowTitle("Copy Skin Partial")
        self.setMinimumWidth(300)
        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowMinimizeButtonHint
        )

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        """Build the UI layout."""
        layout = QtWidgets.QVBoxLayout(self)

        # Source mesh section
        source_grp = QtWidgets.QGroupBox("Source Mesh")
        source_layout = QtWidgets.QHBoxLayout(source_grp)
        self.source_line = QtWidgets.QLineEdit()
        self.source_line.setPlaceholderText("Select mesh and click <<")
        self.source_btn = QtWidgets.QPushButton("<<")
        self.source_btn.setFixedWidth(30)
        self.source_btn.setToolTip("Load selected mesh")
        source_layout.addWidget(self.source_line)
        source_layout.addWidget(self.source_btn)
        layout.addWidget(source_grp)

        # Options
        self.normalize_chk = QtWidgets.QCheckBox("Normalize weights")
        self.normalize_chk.setChecked(True)
        layout.addWidget(self.normalize_chk)

        # Copy button
        self.copy_btn = QtWidgets.QPushButton("Copy to Selected Vertices")
        self.copy_btn.setMinimumHeight(40)
        layout.addWidget(self.copy_btn)

        # Info label
        self.info_label = QtWidgets.QLabel(
            "Select vertices on target mesh(es), then click Copy."
        )
        self.info_label.setStyleSheet("color: gray;")
        layout.addWidget(self.info_label)

        # Close button
        self.close_btn = QtWidgets.QPushButton("Close")
        layout.addWidget(self.close_btn)

    def _connect_signals(self):
        """Connect signals."""
        self.source_btn.clicked.connect(self._load_source)
        self.copy_btn.clicked.connect(self._copy)
        self.close_btn.clicked.connect(self.close)

    def _load_source(self):
        """Load source mesh from selection."""
        selection = pm.ls(sl=True, fl=True)
        meshes = [
            s for s in selection
            if hasattr(s, "getShape")
            and s.getShape() is not None
            and ".vtx[" not in str(s)
        ]
        if meshes:
            self.source_line.setText(meshes[0].name())
        else:
            pm.displayWarning("Please select a mesh with skinCluster.")

    def _copy(self):
        """Execute the copy operation."""
        source_name = self.source_line.text().strip()
        if not source_name:
            pm.displayWarning("Please set a source mesh.")
            return

        # Validate source mesh
        if not pm.objExists(source_name):
            pm.displayError("Source mesh '{}' not found.".format(source_name))
            return

        sourceMesh = pm.PyNode(source_name)
        sourceSkin = getSkinCluster(sourceMesh)
        if not sourceSkin:
            pm.displayError(
                "Source mesh '{}' has no skinCluster.".format(source_name)
            )
            return

        # Get selected vertices
        selection = pm.ls(sl=True, fl=True)
        vertices = [v for v in selection if ".vtx[" in str(v)]

        if not vertices:
            pm.displayWarning("Please select vertices on target mesh.")
            return

        normalize = self.normalize_chk.isChecked()

        # Store vertex names as strings for safe reselection
        vertex_names = [str(v) for v in vertices]

        # Execute copy
        try:
            _skinCopyPartialExecute(sourceMesh, vertices, normalize)
        except Exception as e:
            pm.displayError("Copy failed: {}".format(e))
            import traceback
            traceback.print_exc()
            return

        # Keep vertices selected
        try:
            pm.select(vertex_names, r=True)
        except Exception:
            pass  # Selection may fail if vertices changed


def openSkinCopyPartialUI():
    """Open the Copy Skin Partial UI."""
    parent = pyqt.maya_main_window()
    dialog = SkinCopyPartialUI(parent)
    dialog.show()
    return dialog


def skinCopyPartial(sourceMesh=None, targetMesh=None, normalize=True):
    """Copy skin weights from source mesh to selected vertices on target mesh.

    Uses closest point matching - for each selected vertex on the target,
    finds the closest vertex on the source and copies its weights.

    When called without sourceMesh, opens the UI for interactive use.

    Args:
        sourceMesh (str or PyNode): Source mesh with skinCluster.
            If None, opens UI.
        targetMesh (str or PyNode): Target mesh with skinCluster.
            If None, derives from selected vertices.
        normalize (bool): Normalize weights after copying. Defaults to True.

    Returns:
        bool: True if successful, False otherwise.

    Example:
        .. code-block:: python

            from mgear.core import skin

            # Open UI for interactive use
            skin.skinCopyPartial()

            # Scripted: provide source mesh explicitly
            skin.skinCopyPartial(sourceMesh="body_geo")
    """
    # If no source provided, open UI
    if not sourceMesh:
        openSkinCopyPartialUI()
        return True

    # Get selected vertices
    selection = pm.ls(sl=True, fl=True)
    vertices = [v for v in selection if ".vtx[" in str(v)]

    if not vertices:
        pm.displayWarning("Please select vertices on target mesh.")
        return False

    # Unused but kept for API compatibility
    _ = targetMesh

    if isinstance(sourceMesh, string_types):
        sourceMesh = pm.PyNode(sourceMesh)

    return _skinCopyPartialExecute(sourceMesh, vertices, normalize)


######################################
# Skin Utils
######################################


# Select deformers
def selectDeformers(*args):
    if pm.selected():
        try:
            oSel = pm.selected()[0]
            oColl = pm.skinCluster(oSel, query=True, influence=True)
            pm.select(oColl)
        except Exception:
            pm.displayError("Select one object with skinCluster")
    else:
        pm.displayWarning("Select one object with skinCluster")


# Skin cluster selector
def rename_skin_clusters(*args):
    """
    Renames the skinClusters of all selected objects to match the
    format: objectName_skinCluster.
    """
    # List all selected objects
    selected_objects = cmds.ls(selection=True)

    for obj in selected_objects:
        # List all skinClusters connected to the current object
        skin_clusters = cmds.ls(cmds.listHistory(obj), type="skinCluster")
        if skin_clusters:
            # Assuming the first found skinCluster is the one to rename
            skin_cluster_name = skin_clusters[0]
            # New name format: objectName_skinCluster
            if "_skinCluster" in skin_cluster_name:
                print(
                    "Looks like {} is correctly formatted".format(
                        skin_cluster_name
                    )
                )
            else:
                new_name = "{}_skinCluster".format(obj)
                # Rename the skinCluster
                cmds.rename(skin_cluster_name, new_name)
                print("Renamed {} to {}".format(skin_cluster_name, new_name))
        else:
            print("No skinCluster found for {}".format(obj))


# Skin cluster selector
class SkinClusterSelector(
    MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin
):
    def __init__(self, parent=None):
        super(SkinClusterSelector, self).__init__(parent)
        self.setWindowTitle("SkinCluster Selector Tool")
        self.setMinimumWidth(200)
        self.setWindowFlags(
            self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
        )

        self.create_widgets()
        self.create_layouts()
        self.create_connections()

        # Get and store the default text color from the list widget
        self.default_text_color = self.skin_cluster_list.palette().color(
            QtGui.QPalette.Text
        )

    def create_widgets(self):
        self.set_object_btn = QtWidgets.QPushButton("Set Object")
        self.skin_cluster_list = QtWidgets.QListWidget()
        self.skin_cluster_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )

    def create_layouts(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.set_object_btn)
        main_layout.addWidget(self.skin_cluster_list)

    def create_connections(self):
        self.set_object_btn.clicked.connect(self.set_object)
        self.skin_cluster_list.itemClicked.connect(self.select_skin_cluster)
        self.skin_cluster_list.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        self.skin_cluster_list.customContextMenuRequested.connect(
            self.show_context_menu
        )

    def find_connected_skinclusters(self, skin_cluster, found_clusters=list()):
        """
        Recursively finds all skinClusters directly connected to another
        skinCluster.

        Args:
            skin_cluster (str): The starting skinCluster's name.
            found_clusters (list): A list of already found skinCluster names.

        Returns:
            set: A set of skinCluster names, including the starting skinCluster
                 and all directly connected skinClusters found recursively.
        """
        if skin_cluster not in found_clusters:
            found_clusters.append(skin_cluster)
            input_connections = (
                cmds.listConnections(
                    "{}.input".format(skin_cluster), type="skinCluster"
                )
                or []
            )
            for connected_sc in input_connections:
                # Recursive call to find further connected skinClusters
                self.find_connected_skinclusters(connected_sc, found_clusters)
        return found_clusters

    def set_object(self):
        """
        Populates the skin_cluster_list with skinClusters connected to the
        selected object. It includes skinClusters connected as inputs to other
        skinClusters, searched recursively.
        """
        # Clear list before
        self.skin_cluster_list.clear()
        selection = cmds.ls(selection=True, objectsOnly=True)
        # recursion new fresh list  before find more connections
        found_clusters = list()
        if selection:
            # self.skin_cluster_list.clear()
            shapes = (
                cmds.listRelatives(selection[0], shapes=True, fullPath=True)
                or []
            )
            for shape in shapes:
                connections = cmds.listConnections(shape, type="skinCluster")
                # print(connections)
                if connections:
                    for sc in connections:
                        # Use recursive function to find all connected skinClusters
                        all_skin_clusters = self.find_connected_skinclusters(
                            sc, found_clusters
                        )
            # print(all_skin_clusters)
            for sc in all_skin_clusters:
                item = QtWidgets.QListWidgetItem(sc)
                # Check if the skin cluster is active (envelope > 0)
                if cmds.getAttr("{}.envelope".format(sc)) <= 0:
                    item.setForeground(QtGui.QColor("red"))
                self.skin_cluster_list.addItem(item)

    def select_skin_cluster(self, item):
        cmds.select(item.text())

    def update_skin_cluster_status(self, skin_clusters, status):
        """
        Update the envelope status of selected skin clusters and adjust list item color.

        Args:
            skin_clusters (list): List of skin cluster names.
            status (float): New envelope status (0 for off, 1 for on).
        """
        for i in range(self.skin_cluster_list.count()):
            item = self.skin_cluster_list.item(i)
            if item.text() in skin_clusters:
                cmds.setAttr("{}.envelope".format(item.text()), status)
                item.setForeground(
                    QtGui.QColor("red")
                    if status <= 0
                    else self.default_text_color
                )

    def show_context_menu(self, position):
        context_menu = QtWidgets.QMenu()
        turn_off_action = context_menu.addAction("Turn OFF Skin Cluster")
        turn_on_action = context_menu.addAction("Turn ON Skin Cluster")
        action = context_menu.exec_(
            self.skin_cluster_list.mapToGlobal(position)
        )
        selected_items = self.skin_cluster_list.selectedItems()
        selected_skin_clusters = [item.text() for item in selected_items]
        if action == turn_off_action:
            self.update_skin_cluster_status(selected_skin_clusters, 0)
        elif action == turn_on_action:
            self.update_skin_cluster_status(selected_skin_clusters, 1)


def openSkinClusterSelector(*args):
    return pyqt.showDialog(SkinClusterSelector, dockable=True)
