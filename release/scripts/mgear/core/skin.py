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
import maya.api.OpenMaya as om2

string_types = str
from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui
from mgear.core import pyqt
from mgear.core import applyop
from mgear.core import node_remap
from mgear.core import utils
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

FILE_EXT = ".gSkin"
FILE_JSON_EXT = ".jSkin"
PACK_EXT = ".gSkinPack"
MAP_EXT = ".gSkinMap"

# Results of the missing-items policy for one skin file
REMAP_APPLY = "apply"
REMAP_SKIP_FILE = "skip_file"
REMAP_CANCEL = "cancel"

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
        # build a dictionary of {vtx: weight}. Skip 0.0 weights.
        inf_w = {
            jj: weights[jj * numInfluences + ii]
            for jj in range(numComponentsPerInfluence)
            if weights[jj * numInfluences + ii] != 0.0
        }
        dataDic["weights"][_influence_key(influencePaths[ii])] = inf_w


def _influence_key(dagPath):
    """Return the name used to store an influence in skin files.

    Args:
        dagPath (MDagPath): The influence DAG path.

    Returns:
        str: Namespace-stripped partial path name.
    """
    return node_remap.strip_namespace_path(dagPath.partialPathName())


def _bind_position(bindPrePlug, node):
    """Return the bind-pose world position of an influence.

    Args:
        bindPrePlug (str): The skinCluster ``bindPreMatrix[i]`` plug of the
            influence, or None if it isn't an influence.
        node (str): The influence node, used for the current world position
            when there is no usable bindPreMatrix.

    Returns:
        list: [x, y, z]
    """
    if bindPrePlug:
        try:
            bindPre = om2.MMatrix(cmds.getAttr(bindPrePlug))
            return list(bindPre.inverse())[12:15]
        except (RuntimeError, ValueError, TypeError):
            pass
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def get_influence_bind_positions(skinCls):
    """Get the bind-pose world position of each influence of a skinCluster.

    The position comes from the inverse of the skinCluster bindPreMatrix at
    the influence logical index, so it does not depend on the current pose.
    Falls back to the current world position if bindPreMatrix is not set.

    Args:
        skinCls (str or PyNode): The skinCluster.

    Returns:
        dict: ``{stored influence name: [x, y, z]}``
    """
    skinName = str(skinCls)
    skinFn = get_skin_cluster_fn(skinName)
    influencePaths = OpenMaya.MDagPathArray()
    skinFn.influenceObjects(influencePaths)

    positions = {}
    for ii in range(influencePaths.length()):
        path = influencePaths[ii]
        plug = "{}.bindPreMatrix[{}]".format(
            skinName, skinFn.indexForInfluenceObject(path)
        )
        positions[_influence_key(path)] = _bind_position(plug, path.fullPathName())
    return positions


def get_bind_world_positions(nodes):
    """Get the bind-pose world position of transform nodes.

    Uses the bindPreMatrix of the first skinCluster the node drives, and
    the current world position for nodes that are not influences.

    Args:
        nodes (list): Transform node names or paths.

    Returns:
        dict: ``{node: [x, y, z]}`` for the nodes that exist.
    """
    positions = {}
    for node in nodes:
        if not cmds.objExists(node):
            continue
        plugs = cmds.listConnections(
            node + ".worldMatrix", type="skinCluster", plugs=True
        )
        bindPlug = None
        if plugs:
            bindPlug = plugs[0].replace(".matrix[", ".bindPreMatrix[")
        positions[node] = _bind_position(bindPlug, node)
    return positions


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
            dataDic["objLongName"] = obj.longName()
            dataDic["nameSpace"] = obj.namespace()

            collectData(skinCls, dataDic)
            dataDic["influencePositions"] = get_influence_bind_positions(skinCls)

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


def _skin_file_name(objName, usedNames):
    """Build a portable, unique skin file name for an object in a pack.

    ``|`` becomes ``-`` and ``:`` becomes ``.``. Neither can appear in a
    Maya name, so the label stays readable and unambiguous. A ``_N``
    suffix is added when the name is already used in the pack.

    Args:
        objName (str): Object name, may include namespace and DAG path.
        usedNames (set): Lowercase names already used in the pack. The
            returned name is added to it.

    Returns:
        str: File name without extension.
    """
    base = objName.lstrip("|").replace("|", "-").replace(":", ".")
    fileName = base
    index = 1
    # Compare lowercase: Windows and macOS file systems ignore case.
    while fileName.lower() in usedNames:
        fileName = "{}_{}".format(base, index)
        index += 1
    usedNames.add(fileName.lower())
    return fileName


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

    usedNames = set()
    for obj in objs:
        fileName = _skin_file_name(obj.name(), usedNames) + file_ext
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


def _influence_index_map(influencePaths):
    """Map influence names and full DAG paths to their influence index.

    Full paths let resolved skin data address influences unambiguously,
    while node names keep older callers working.

    Args:
        influencePaths (MDagPathArray): The skinCluster influences.

    Returns:
        dict: ``{name or full path: index}``
    """
    influenceMap = {}
    for ii in range(influencePaths.length()):
        path = influencePaths[ii]
        influenceMap[OpenMaya.MFnDependencyNode(path.node()).name()] = ii
        influenceMap[path.fullPathName()] = ii
    return influenceMap


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

    influenceMap = _influence_index_map(influencePaths)

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

    influenceMap = _influence_index_map(influencePaths)

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
        dict: Mapping of {influence_name or full path: index, ...}
    """
    influencePaths = OpenMaya.MDagPathArray()
    get_skin_cluster_fn(skinCluster).influenceObjects(influencePaths)
    return _influence_index_map(influencePaths)


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
    # No main progress bar in batch mode (mayapy builds)
    gMainProgressBar = None
    if not cmds.about(batch=True):
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
            if gMainProgressBar and i % updateInterval == 0:
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
        if gMainProgressBar:
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


def _load_skin_file(filePath):
    """Load the data of a .gSkin or .jSkin file.

    Args:
        filePath (str): Skin file path.

    Returns:
        dict: The skin data pack with ``objs`` and ``objDDic`` keys.
    """
    if filePath.endswith(FILE_EXT):
        with open(filePath, "rb") as fp:
            return pickle.load(fp)
    with open(filePath, "r") as fp:
        return json.load(fp)


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

    return _load_skin_file(filePath)["objs"]


def getObjsFromSkinFile(filePath=None, *args):
    objs = _getObjsFromSkinFile(filePath)
    if objs:
        for x in objs:
            print(x)


######################################
# Skin import name resolution
######################################


def load_skin_mapping(mapping=None):
    """Return a normalized skin remap mapping.

    Args:
        mapping (dict or str, optional): Mapping dict, or path to a
            ``.gSkinMap`` file. Missing sections are allowed.

    Returns:
        dict: ``{"geometry": {exported: scene}, "influences": {exported:
            scene}}``. Always a new dict.
    """
    result = {"geometry": {}, "influences": {}}
    if not mapping:
        return result
    if isinstance(mapping, string_types):
        with open(mapping, "r") as fp:
            mapping = json.load(fp)
    for key, table in result.items():
        table.update(mapping.get(key) or {})
    return result


def save_skin_mapping(mapping, filePath):
    """Save a skin remap mapping as a ``.gSkinMap`` JSON file.

    Args:
        mapping (dict): Mapping with ``geometry`` and ``influences`` tables.
        filePath (str): Destination file path.

    Returns:
        str: The written file path.
    """
    data = {"version": 1}
    data.update(load_skin_mapping(mapping))
    with open(filePath, "w") as fp:
        json.dump(data, fp, indent=4, sort_keys=True)
    return filePath


class SkinRemapReport(object):
    """Unresolved geometry and influences of one skin file.

    Attributes:
        file_path (str): The skin file the report belongs to.
        geometry (list): One dict per missing or ambiguous object with
            ``name``, ``long_name`` and ``candidates`` (scene paths).
        influences (dict): ``{name: info}`` per missing influence, with
            ``position`` (bind position or None), ``users`` (object names)
            and ``candidates`` (ambiguous scene paths).
        influence_pool (list): Influences of the target skinClusters that
            already exist. Preferred match candidates; empty if no target
            is skinned yet.
    """

    def __init__(self, file_path=None):
        self.file_path = file_path
        self.geometry = []
        self.influences = {}
        self.influence_pool = []

    def is_empty(self):
        """Return True when nothing is missing or ambiguous.

        Returns:
            bool: True if the report has no items.
        """
        return not self.geometry and not self.influences

    def item_keys(self):
        """Return a key per reported item.

        Returns:
            set: ``("geometry", name)`` and ``("influence", name)`` tuples.
        """
        keys = {("geometry", geo["name"]) for geo in self.geometry}
        keys.update(("influence", name) for name in self.influences)
        return keys

    def subset(self, keys):
        """Return a copy of the report with only some items.

        Args:
            keys (set): Item keys to keep, see item_keys.

        Returns:
            SkinRemapReport: The narrowed report.
        """
        report = SkinRemapReport(self.file_path)
        report.geometry = [
            geo for geo in self.geometry if ("geometry", geo["name"]) in keys
        ]
        report.influences = {
            name: info
            for name, info in self.influences.items()
            if ("influence", name) in keys
        }
        report.influence_pool = self.influence_pool
        return report

    def summary(self):
        """Return a readable multi-line description of the report.

        Returns:
            str: One line per unresolved item.
        """
        label = os.path.basename(self.file_path or "skin data")
        lines = []
        for geo in self.geometry:
            if geo["candidates"]:
                lines.append(
                    "{}: ambiguous object '{}' ({})".format(
                        label, geo["name"], ", ".join(geo["candidates"])
                    )
                )
            else:
                lines.append("{}: object '{}' not found".format(label, geo["name"]))
        for name, info in sorted(self.influences.items()):
            lines.append(
                "{}: influence '{}' not found (used by {})".format(
                    label, name, ", ".join(info["users"])
                )
            )
        return "\n".join(lines)


class SkinRemapError(RuntimeError):
    """Raised by skin import when ``on_missing="error"`` finds issues.

    Attributes:
        reports (list): SkinRemapReport per skin file with issues.
    """

    def __init__(self, reports):
        self.reports = reports
        message = "Skin import has unresolved items:\n" + "\n".join(
            report.summary() for report in reports
        )
        super(SkinRemapError, self).__init__(message)


class SkinRemapSession(object):
    """Choices made during one skin import, shared by its remap dialogs.

    Attributes:
        mapping (dict): Normalized mapping (see load_skin_mapping) with the
            mapping passed to the import plus every choice made so far.
            Later files of a skin pack reuse it.
        save_path (str): ``.gSkinMap`` file rewritten each time choices are
            added, or None. Set by the dialog's Save mapping.
        scene_geometry (dict): Cache for get_skinnable_geometry, or None.
            Point counts don't change during an import.
    """

    def __init__(self, mapping=None):
        self.mapping = load_skin_mapping(mapping)
        self.save_path = None
        self.scene_geometry = None

    def merged(self, extra=None):
        """Return a copy of the session mapping with extra choices.

        Args:
            extra (dict or str, optional): Mapping dict or ``.gSkinMap``
                path merged on top.

        Returns:
            dict: Normalized mapping.
        """
        mapping = load_skin_mapping(self.mapping)
        for key, table in load_skin_mapping(extra).items():
            mapping[key].update(table)
        return mapping

    def add(self, mapping):
        """Merge choices into the session and update the saved file.

        Args:
            mapping (dict or str): Mapping dict or ``.gSkinMap`` path.
        """
        self.mapping = self.merged(mapping)
        self.save()

    def save(self, extra=None):
        """Write the session mapping to save_path, if set.

        Args:
            extra (dict, optional): Choices not added yet, e.g. the rows of
                an open dialog.
        """
        if self.save_path:
            save_skin_mapping(self.merged(extra), self.save_path)

    def get_scene_geometry(self):
        """Return the skinnable scene geometry, queried once per import.

        Returns:
            dict: ``{transform full path: point count}``
        """
        if self.scene_geometry is None:
            self.scene_geometry = get_skinnable_geometry()
        return self.scene_geometry


def _resolve_mapped(name, table):
    """Return the scene path a user mapping assigns to a name.

    Args:
        name (str): Exported name.
        table (dict): ``{exported: scene}`` mapping table.

    Returns:
        str: The unique full path, or None.
    """
    target = table.get(name) or table.get(node_remap.strip_namespace_path(name))
    if not target:
        return None
    hits = cmds.ls(target, long=True) or []
    return hits[0] if len(hits) == 1 else None


def _skin_influence_paths(skinCls):
    """Return the full DAG paths of a skinCluster influences.

    Args:
        skinCls (str or PyNode): The skinCluster.

    Returns:
        list: Full paths.
    """
    influencePaths = OpenMaya.MDagPathArray()
    get_skin_cluster_fn(str(skinCls)).influenceObjects(influencePaths)
    return [influencePaths[ii].fullPathName() for ii in range(influencePaths.length())]


def _resolve_influence(name, existingIndex, namespace, mapping, cache):
    """Resolve a stored influence name to a scene node.

    Args:
        name (str): Stored influence name.
        existingIndex (dict): Influences of the target skinCluster grouped
            by short name, see node_remap.group_by_short_name. Empty if
            not skinned.
        namespace (str): Forced namespace, or None for automatic.
        mapping (dict): Normalized user mapping.
        cache (dict): Scene lookups already done, reused across objects
            and files sharing the same joints.

    Returns:
        tuple: (full path or None, ambiguous candidates)
    """
    mapped = _resolve_mapped(name, mapping["influences"])
    if mapped:
        return mapped, []
    if existingIndex and namespace is None:
        hits = node_remap.filter_by_path_suffix(
            existingIndex.get(node_remap.short_name(name), []),
            node_remap.strip_namespace_path(name),
        )
        if len(hits) == 1:
            return hits[0], []
    key = (name, namespace)
    if key not in cache:
        cache[key] = node_remap.find_node_candidates(
            name, node_type="transform", namespace=namespace
        )
    hits = cache[key]
    if len(hits) == 1:
        return hits[0], []
    return None, hits


def _resolve_skin_data(dataPack, filePath, namespace, mapping, cache=None):
    """Resolve the objects and influences of one skin file to the scene.

    Args:
        dataPack (dict): Loaded skin file data.
        filePath (str): Skin file path, for reporting.
        namespace (str): Forced namespace, or None for automatic.
        mapping (dict): Normalized user mapping, see load_skin_mapping.
        cache (dict, optional): Influence lookup cache shared between the
            files of a pack.

    Returns:
        tuple: (resolved, report). ``resolved`` is a list of
            ``(data, geometry path, {stored influence: scene path})`` for
            the objects found. ``report`` is a SkinRemapReport.
    """
    cache = {} if cache is None else cache
    report = SkinRemapReport(filePath)
    resolved = []
    pool = []
    for data in dataPack["objDDic"]:
        objName = data["objName"]
        geoPath = _resolve_mapped(objName, mapping["geometry"])
        if not geoPath:
            hits = node_remap.find_node_candidates(
                objName,
                long_name=data.get("objLongName"),
                node_type="transform",
                namespace=namespace,
            )
            if len(hits) != 1:
                report.geometry.append(
                    {
                        "name": objName,
                        "long_name": data.get("objLongName"),
                        "point_count": _stored_point_count(data),
                        "candidates": hits,
                    }
                )
                continue
            geoPath = hits[0]

        skinCls = getSkinCluster(geoPath)
        existing = _skin_influence_paths(skinCls) if skinCls else []
        existingIndex = node_remap.group_by_short_name(existing)
        pool.extend(existing)
        positions = data.get("influencePositions") or {}
        influenceMap = {}
        for name in data["weights"]:
            path, candidates = _resolve_influence(
                name, existingIndex, namespace, mapping, cache
            )
            if path:
                influenceMap[name] = path
                continue
            info = report.influences.setdefault(
                name,
                {"position": positions.get(name), "users": [], "candidates": []},
            )
            info["users"].append(objName)
            for candidate in candidates:
                if candidate not in info["candidates"]:
                    info["candidates"].append(candidate)
        resolved.append((data, geoPath, influenceMap))

    report.influence_pool = list(dict.fromkeys(pool))
    return resolved, report


def _remap_weights(weights, influenceMap, compressed):
    """Rekey stored weights from influence names to scene paths.

    Unresolved influences are dropped. Influences mapped to the same scene
    node have their weights added together. Weights are only copied when
    they are merged, otherwise the stored values are shared.

    Args:
        weights (dict): Stored ``{influence: weights}``.
        influenceMap (dict): ``{stored influence: scene path}``.
        compressed (bool): True for ``{vtx: weight}`` values, False for
            per-vertex lists.

    Returns:
        dict: ``{scene path: weights}``
    """
    remapped = {}
    merged = set()
    for name, values in weights.items():
        target = influenceMap.get(name)
        if not target:
            continue
        if target not in remapped:
            remapped[target] = values
        elif compressed:
            if target not in merged:
                remapped[target] = dict(remapped[target])
                merged.add(target)
            current = remapped[target]
            for key, wt in values.items():
                current[key] = current.get(key, 0.0) + wt
        else:
            remapped[target] = [a + b for a, b in zip(remapped[target], values)]
    return remapped


def _stored_point_count(data):
    """Return the vertex or CV count stored for one object of a skin file.

    Args:
        data (dict): One object entry of a skin file.

    Returns:
        int: Point count of the exported geometry.
    """
    if data.get("skinDataFormat") == "compressed":
        return data["vertexCount"]
    return len(data["blendWeights"])


def get_skinnable_geometry():
    """Return the scene meshes, nurbs surfaces and curves with point counts.

    Point counts of transforms with several shapes are added together,
    like _geometry_point_count.

    Returns:
        dict: ``{transform full path: vertex or CV count}``
    """
    shapes = cmds.ls(
        type=("mesh", "nurbsSurface", "nurbsCurve"),
        noIntermediate=True,
        long=True,
    )
    selection = om2.MSelectionList()
    for shape in shapes or []:
        selection.add(shape)

    geometry = {}
    for ii in range(selection.length()):
        path = selection.getDagPath(ii)
        if path.hasFn(om2.MFn.kMesh):
            count = om2.MFnMesh(path).numVertices
        elif path.hasFn(om2.MFn.kNurbsSurface):
            surface = om2.MFnNurbsSurface(path)
            count = surface.numCVsInU * surface.numCVsInV
        else:
            count = om2.MFnNurbsCurve(path).numCVs
        parent = path.fullPathName().rsplit("|", 1)[0]
        geometry[parent] = geometry.get(parent, 0) + count
    return geometry


def _geometry_point_count(objNode):
    """Return the number of vertices or CVs of a skinnable object.

    Args:
        objNode (PyNode): Mesh, nurbsSurface or nurbsCurve transform.

    Returns:
        int: Point count, 0 for unsupported types.
    """
    # use getShapes() else meshes with 2+ shapes will fail.
    # noIntermediate otherwise it will count shapeOrig nodes.
    objShapes = objNode.getShapes(noIntermediate=True)
    shape = objNode.getShape()
    if isinstance(shape, pm.nodetypes.Mesh):
        return pm.polyEvaluate(objShapes, vertex=True)
    count = 0
    if isinstance(shape, pm.nodetypes.NurbsSurface):
        for shp in objShapes:
            name = shp.name()
            spansU = cmds.getAttr(name + ".spansU")
            spansV = cmds.getAttr(name + ".spansV")
            degreeU = cmds.getAttr(name + ".degreeU")
            degreeV = cmds.getAttr(name + ".degreeV")
            count += (spansU + degreeU) * (spansV + degreeV)
    elif isinstance(shape, pm.nodetypes.NurbsCurve):
        for shp in objShapes:
            name = shp.name()
            count += cmds.getAttr(name + ".spans") + cmds.getAttr(name + ".degree")
    # TODO: Implement other skinnable objs like lattices.
    return count


def _create_skin_cluster(geoPath, influences, skinName):
    """Create a skinCluster on resolved influences.

    Args:
        geoPath (str): Geometry full path.
        influences (list): Influence full paths.
        skinName (str): Exported skinCluster name.

    Returns:
        PyNode: The new skinCluster.
    """
    # The exported name may carry a path or a namespace that doesn't exist
    # in this scene. Either would make the skinCluster command fail.
    skinCls = pm.skinCluster(
        influences,
        geoPath,
        toSelectedBones=True,
        normalizeWeights=2,
        name=node_remap.short_name(skinName),
    )
    if isinstance(skinCls, list):
        skinCls = skinCls[0]
    return skinCls


def _add_missing_influences(skinCls, influences):
    """Add resolved influences that the target skinCluster doesn't have.

    Args:
        skinCls (PyNode): Target skinCluster.
        influences (list): Influence full paths.
    """
    existing = set(_skin_influence_paths(skinCls))
    missing = [inf for inf in influences if inf not in existing]
    if missing:
        cmds.skinCluster(skinCls.name(), edit=True, addInfluence=missing, weight=0.0)
        pm.displayInfo("Added influences to {}: {}".format(skinCls.name(), missing))


def _apply_skin_data(data, geoPath, influenceMap, vertexMismatchMode="auto"):
    """Apply one object's skin data using resolved scene names.

    Args:
        data (dict): One object entry of a skin file.
        geoPath (str): Resolved geometry full path.
        influenceMap (dict): ``{stored influence: scene path}``.
        vertexMismatchMode (str, optional): ``"skip"``, ``"closestPoint"``
            or ``"auto"``. See importSkin.

    Returns:
        str: ``"index"`` or ``"volume"`` for the method used, None if the
            object was skipped.
    """
    compressed = data.get("skinDataFormat") == "compressed"
    objName = data["objName"]
    objNode = pm.PyNode(geoPath)

    remapped = dict(data)
    remapped["weights"] = _remap_weights(data["weights"], influenceMap, compressed)
    if not remapped["weights"]:
        pm.displayWarning(
            "Object: {} Skipped. None of its influences were found in the "
            "scene".format(objName)
        )
        return None

    importedVertices = _stored_point_count(data)
    try:
        meshVertices = _geometry_point_count(objNode)
        vertexMismatch = meshVertices != importedVertices
    except Exception:
        vertexMismatch = False

    if vertexMismatch and vertexMismatchMode == "skip":
        pm.displayWarning(
            "Vertex counts on {} do not match. {} != {}".format(
                objName, meshVertices, importedVertices
            )
        )
        return None

    influences = list(remapped["weights"])
    skinCls = getSkinCluster(objNode)
    if skinCls:
        _add_missing_influences(skinCls, influences)
    else:
        try:
            skinCls = _create_skin_cluster(geoPath, influences, data["skinClsName"])
        except Exception as e:
            pm.displayWarning(
                "Object: {} Skipped. Can't create skinCluster: {}".format(objName, e)
            )
            return None

    if vertexMismatch and vertexMismatchMode in ("closestPoint", "auto"):
        pm.displayInfo(
            "Vertex count mismatch on {}. Using closest-point "
            "matching ({} -> {} vertices)...".format(
                objName, importedVertices, meshVertices
            )
        )
        if _importSkinVolumeMethod(objNode, skinCls, remapped, compressed):
            print("Imported skin (volume method) for: {}".format(objName))
            return "volume"
        print(
            "Skipped skin import for: {} (volume method failed, "
            "see warning above)".format(objName)
        )
        return None

    setData(skinCls, remapped, compressed)
    print("Imported skin for: {}".format(objName))
    return "index"


def _run_missing_policy(report, on_missing, session, index=None, total=None):
    """Run the caller-chosen policy for a skin file with missing items.

    Args:
        report (SkinRemapReport): The file report.
        on_missing (str or callable): ``"skip"``, ``"error"``, ``"ui"`` or
            a callable taking the report and returning a mapping or None.
        session (SkinRemapSession): Choices made so far in this import.
        index (int, optional): File position in a pack, from 1.
        total (int, optional): Number of files in the pack.

    Returns:
        tuple: (status, mapping). status is REMAP_APPLY, REMAP_SKIP_FILE
            or REMAP_CANCEL.

    Raises:
        SkinRemapError: When ``on_missing`` is ``"error"``.
        ValueError: When ``on_missing`` is not a valid policy.
    """
    if on_missing == "skip":
        return REMAP_APPLY, None
    if on_missing == "error":
        raise SkinRemapError([report])
    if on_missing == "ui":
        from mgear.core import skin_remap_ui

        return skin_remap_ui.run_remap_dialog(
            report, index=index, total=total, session=session
        )
    if callable(on_missing):
        mapping = on_missing(report)
        if mapping is None:
            return REMAP_CANCEL, None
        return REMAP_APPLY, mapping
    raise ValueError("Invalid on_missing policy: {}".format(on_missing))


def _apply_resolved(resolved, vertexMismatchMode):
    """Apply the resolved objects of one skin file.

    Args:
        resolved (list): Output of _resolve_skin_data.
        vertexMismatchMode (str): See importSkin.

    Returns:
        list: Object names imported with the volume method.
    """
    volumeImported = []
    for data, geoPath, influenceMap in resolved:
        try:
            method = _apply_skin_data(data, geoPath, influenceMap, vertexMismatchMode)
        except Exception as e:
            pm.displayWarning("Object: {} Skipped. {}".format(data["objName"], e))
            continue
        if method == "volume":
            volumeImported.append(data["objName"])
    return volumeImported


def _import_skin_file(
    filePath,
    vertexMismatchMode,
    namespace,
    on_missing,
    session,
    cache,
    index=None,
    total=None,
):
    """Resolve, run the missing policy and apply one skin file.

    Args:
        filePath (str): Skin file path.
        vertexMismatchMode (str): See importSkin.
        namespace (str): Forced namespace, or None for automatic.
        on_missing (str or callable): See importSkin.
        session (SkinRemapSession): Choices made so far in this import.
            Updated with the choices made by the policy, so later files
            reuse them.
        cache (dict): Influence lookup cache, see _resolve_influence.
        index (int, optional): File position in a pack, from 1.
        total (int, optional): Number of files in the pack.

    Returns:
        tuple: (status, object names imported with the volume method)
    """
    dataPack = _load_skin_file(filePath)
    resolved, report = _resolve_skin_data(
        dataPack, filePath, namespace, session.mapping, cache
    )

    # A user mapping can reveal new missing items, e.g. the influences of an
    # object picked as target. Ask again, only about the new items.
    asked = set()
    while not report.is_empty():
        new = report.item_keys() - asked
        if not new:
            break
        asked.update(new)
        status, userMapping = _run_missing_policy(
            report.subset(new), on_missing, session, index, total
        )
        if status != REMAP_APPLY:
            pm.displayWarning("Skin file not imported: {}".format(filePath))
            return status, []
        if not userMapping:
            break
        session.add(userMapping)
        resolved, report = _resolve_skin_data(
            dataPack, filePath, namespace, session.mapping, cache
        )
    if not report.is_empty():
        pm.displayWarning("Skipped unresolved items:\n" + report.summary())

    return REMAP_APPLY, _apply_resolved(resolved, vertexMismatchMode)


# @utils.timeFunc
def importSkin(
    filePath=None,
    vertexMismatchMode="auto",
    namespace=None,
    on_missing="skip",
    mapping=None,
    *args
):
    """Import skinCluster data from file.

    Args:
        filePath (str, optional): File path for import. If None, opens dialog.
        vertexMismatchMode (str): Behavior when vertex counts don't match:
            - "skip": Skip import with warning
            - "closestPoint": Use closest point matching to transfer weights
            - "auto": Index-based first, fallback to closestPoint (default)
        namespace (str, optional): Force the namespace of the target
            geometry and influences, e.g. ``"char:"`` or ``""`` for root.
            None resolves names automatically.
        on_missing (str or callable, optional): What to do when objects or
            influences can't be resolved:
            - "skip": Skip them with a warning (default)
            - "error": Raise SkinRemapError before applying any weights
            - "ui": Open the remap dialog
            - callable: Called with the SkinRemapReport; returns a mapping
              dict, or None to cancel the import
        mapping (dict or str, optional): Remap mapping, or path to a
            ``.gSkinMap`` file, applied before automatic resolution.

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

    _, volumeImported = _import_skin_file(
        filePath,
        vertexMismatchMode,
        namespace,
        on_missing,
        SkinRemapSession(mapping),
        {},
    )
    return volumeImported


@utils.timeFunc
def importSkinPack(
    filePath=None,
    vertexMismatchMode="auto",
    namespace=None,
    on_missing="skip",
    mapping=None,
    *args
):
    """Import skin data from a skin pack file.

    Files are resolved and applied one at a time. The ``on_missing`` policy
    runs once per file with missing items, and the choices made for one
    file are reused for the next ones. With ``on_missing="error"`` every
    file is checked before any weights are applied.

    Args:
        filePath (str, optional): File path for import. If None, opens dialog.
        vertexMismatchMode (str, optional): See importSkin.
        namespace (str, optional): See importSkin.
        on_missing (str or callable, optional): See importSkin.
        mapping (dict or str, optional): See importSkin.

    Returns:
        list: Object names that were imported using the volume method.
            Empty list if all objects used standard index-based import.

    Raises:
        SkinRemapError: When ``on_missing`` is ``"error"`` and any file has
            unresolved items.
    """
    if not filePath:
        filePath = pm.fileDialog2(
            fileMode=1, fileFilter="mGear skinPack (*%s)" % PACK_EXT
        )
    if not filePath:
        return []
    if not isinstance(filePath, string_types):
        filePath = filePath[0]

    with open(filePath) as fp:
        packDic = json.load(fp)
    rootPath = os.path.dirname(filePath)
    skinFiles = [os.path.join(rootPath, f) for f in packDic["packFiles"]]
    session = SkinRemapSession(mapping)

    cache = {}

    if on_missing == "error":
        # Check every file before applying any, then reuse the results.
        checked = []
        reports = []
        for skinFile in skinFiles:
            resolved, report = _resolve_skin_data(
                _load_skin_file(skinFile),
                skinFile,
                namespace,
                session.mapping,
                cache,
            )
            checked.append(resolved)
            if not report.is_empty():
                reports.append(report)
        if reports:
            raise SkinRemapError(reports)
        volumeImported = []
        for resolved in checked:
            volumeImported.extend(_apply_resolved(resolved, vertexMismatchMode))
        return volumeImported

    volumeImported = []
    total = len(skinFiles)
    for ii, skinFile in enumerate(skinFiles):
        status, result = _import_skin_file(
            skinFile,
            vertexMismatchMode,
            namespace,
            on_missing,
            session,
            cache,
            index=ii + 1,
            total=total,
        )
        volumeImported.extend(result)
        if status == REMAP_CANCEL:
            pm.displayWarning(
                "Skin pack import cancelled. {} of {} files not "
                "imported.".format(total - ii, total)
            )
            break

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


def get_soft_selection_weights():
    """Return per-vertex soft-selection falloff weights.

    Returns:
        dict: ``{(transform_short_name, vertex_index): float}`` mapping.
            Empty dict when soft selection is disabled, when there is
            no vertex selection, or when rich selection cannot be
            retrieved.
    """
    if not cmds.softSelect(query=True, softSelectEnabled=True):
        return {}

    rich_sel = OpenMaya.MRichSelection()
    try:
        OpenMaya.MGlobal.getRichSelection(rich_sel)
    except RuntimeError:
        return {}

    sel_list = OpenMaya.MSelectionList()
    rich_sel.getSelection(sel_list)

    weights = {}
    iterator = OpenMaya.MItSelectionList(sel_list)
    while not iterator.isDone():
        dag_path = OpenMaya.MDagPath()
        component = OpenMaya.MObject()
        iterator.getDagPath(dag_path, component)

        if component.isNull() or not component.hasFn(
            OpenMaya.MFn.kMeshVertComponent
        ):
            iterator.next()
            continue

        # Match the short-name resolution used by _skinCopyPartialExecute.
        # partialPathName() can include parent prefixes when the transform
        # short name is ambiguous; strip to the final token for consistency.
        transform_path = OpenMaya.MDagPath(dag_path)
        if transform_path.node().hasFn(OpenMaya.MFn.kMesh):
            transform_path.pop()
        transform_name = transform_path.partialPathName().split("|")[-1]

        comp_fn = OpenMaya.MFnSingleIndexedComponent(component)
        # Probe weight access once.  When rich selection has no per-element
        # weights (uniform case) this lets the entire component default to
        # 1.0 without paying an exception per vertex.
        try:
            comp_fn.weight(0).influence()
            has_weights = True
        except RuntimeError:
            has_weights = False

        for i in range(comp_fn.elementCount()):
            vtx_idx = comp_fn.element(i)
            if has_weights:
                w = comp_fn.weight(i).influence()
            else:
                w = 1.0
            weights[(transform_name, vtx_idx)] = w
        iterator.next()

    return weights


def _skinCopyPartialExecute(
    sourceMesh, vertices, normalize=True, soft_weights=None
):
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
        soft_weights (dict, optional): Mapping of
            ``(transform_name, vertex_index) -> falloff (0-1)``.  When
            provided, each vertex's final weight per influence is a
            linear blend ``original * (1 - soft) + copied * soft``.
            Vertices missing from the dict default to 1.0 (full
            effect), making this argument backwards-compatible with
            hard selection.

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
            verticesByMesh[nodeName] = set()
        verticesByMesh[nodeName].add(vtxIdx)

    # Expand each mesh's vertex set with the soft-selection falloff
    # region; pm.ls(sl=True, fl=True) only returns hard-selected
    # vertices, so falloff vertices need to be unioned in explicitly.
    if soft_weights:
        for (meshName, vtxIdx) in soft_weights:
            if meshName in verticesByMesh:
                verticesByMesh[meshName].add(vtxIdx)

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

        # 4. Merge: blend copied into original per soft falloff.
        # Missing vertices default to 1.0, collapsing to a pure overwrite.
        soft_lookup = soft_weights or {}
        for vtxIdx in vtxIndices:
            soft = soft_lookup.get((meshName, vtxIdx), 1.0)
            inv = 1.0 - soft
            for infIdx in range(numInfluences):
                arrayIdx = vtxIdx * numInfluences + infIdx
                blended = (
                    originalWeights[arrayIdx] * inv
                    + copiedWeights[arrayIdx] * soft
                )
                originalWeights.set(blended, arrayIdx)

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

        # Capture soft-selection falloff before any selection change
        soft_weights = get_soft_selection_weights()

        # Store vertex names as strings for safe reselection
        vertex_names = [str(v) for v in vertices]

        # Execute copy
        try:
            _skinCopyPartialExecute(
                sourceMesh, vertices, normalize, soft_weights=soft_weights
            )
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


def skinCopyPartial(
    sourceMesh=None, targetMesh=None, normalize=True, soft_select=True
):
    """Copy skin weights from source mesh to selected vertices on target mesh.

    Uses closest point matching - for each selected vertex on the target,
    finds the closest vertex on the source and copies its weights.

    When Maya's soft selection is enabled the falloff weights are read
    from the active rich selection and used to linearly blend the
    copied weights with the original weights per vertex.

    When called without sourceMesh, opens the UI for interactive use.

    Args:
        sourceMesh (str or PyNode): Source mesh with skinCluster.
            If None, opens UI.
        targetMesh (str or PyNode): Target mesh with skinCluster.
            If None, derives from selected vertices.
        normalize (bool): Normalize weights after copying. Defaults to True.
        soft_select (bool): Honor Maya's soft selection falloff when
            blending the copied weights. Defaults to True. Set False
            to force a hard copy regardless of soft-select state.

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

    soft_weights = get_soft_selection_weights() if soft_select else None

    # Unused but kept for API compatibility
    _ = targetMesh

    if isinstance(sourceMesh, string_types):
        sourceMesh = pm.PyNode(sourceMesh)

    return _skinCopyPartialExecute(
        sourceMesh, vertices, normalize, soft_weights=soft_weights
    )


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


def localize_skin_clusters(
    joints, offset_node, world_ctl=None, tweak_pattern="_tweak_"
):
    """Localize skinCluster connections to avoid floating-point precision loss.

    When a rig is far from Maya's world origin, skinCluster evaluation can
    suffer from floating-point precision artifacts. This function inserts
    mgear_mulMatrix nodes between each joint's worldMatrix and its
    skinCluster .matrix[N] inputs, making the skinning evaluate relative
    to offset_node instead of world space.

    For tweak joints (name contains tweak_pattern), a prebind mulmatrix
    is also connected to .bindPreMatrix[N] to maintain correct deformation.

    If world_ctl is provided, its worldMatrix drives offset_node transforms
    via a mulmatrix and decomposeMatrix chain.

    Args:
        joints (list): Joint nodes to localize. Accepts strings or PyNodes.
        offset_node (str): Reference transform for localization
            (e.g. "geo_root"). Joint matrices are multiplied by this
            node's worldInverseMatrix.
        world_ctl (str, optional): If provided, drives offset_node SRT
            from this control via mulmatrix + decomposeMatrix.
        tweak_pattern (str, optional): Substring pattern to identify
            tweak joints. Tweak joints get additional bindPreMatrix
            compensation. Defaults to "_tweak_".

    Returns:
        list: Created mgear_mulMatrix PyNodes.

    Example:
        >>> from maya import cmds
        >>> from mgear.core import skin
        >>> joints = cmds.sets("rig_deformers_grp", query=True)
        >>> nodes = skin.localize_skin_clusters(
        ...     joints, "geo_root", world_ctl="world_ctl"
        ... )
    """
    created_nodes = []

    if isinstance(offset_node, string_types):
        offset_node = pm.PyNode(offset_node)

    if world_ctl:
        if isinstance(world_ctl, string_types):
            world_ctl = pm.PyNode(world_ctl)
        node = applyop.gear_mulmatrix_op(
            world_ctl + ".worldMatrix",
            offset_node + ".parentInverseMatrix",
            target=offset_node,
            transform="srt",
        )
        created_nodes.append(node)

    for jnt in joints:
        if isinstance(jnt, string_types):
            jnt = pm.PyNode(jnt)

        skin_conns = pm.listConnections(
            jnt + ".worldMatrix",
            plugs=True,
            type="skinCluster",
        )
        if not skin_conns:
            continue

        is_tweak = tweak_pattern and tweak_pattern in jnt.name()

        parent_mul_mat = None
        if is_tweak:
            jnt_parent = jnt.getParent()
            if jnt_parent:
                parent_mul_mat = applyop.gear_mulmatrix_op(
                    offset_node + ".worldMatrix",
                    jnt_parent + ".worldInverseMatrix",
                )
                created_nodes.append(parent_mul_mat)

        mul_mat = applyop.gear_mulmatrix_op(
            jnt + ".worldMatrix",
            offset_node + ".worldInverseMatrix",
        )
        created_nodes.append(mul_mat)

        for cn in skin_conns:
            pm.connectAttr(mul_mat + ".output", cn, force=True)
            if parent_mul_mat:
                prebind = pm.PyNode(
                    str(cn).replace(".matrix[", ".bindPreMatrix[")
                )
                pm.connectAttr(
                    parent_mul_mat + ".output", prebind, force=True
                )

    cmds.dgdirty(allPlugs=True)

    return created_nodes


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
