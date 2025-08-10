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
    dagPath = OpenMaya.MDagPath()
    sel.getDependNode(0, dep)
    sel.getDagPath(0, dagPath)
    fn_dep = OpenMaya.MFnDependencyNode(dep)
    plug = fn_dep.findPlug(out_attr, True)
    obj = plug.asMObject()

    # Use the MFnGeometryData class to query the components for a tag
    # expression
    fn_geodata = OpenMaya.MFnGeometryData(obj)

    # Components MObject
    components = fn_geodata.resolveComponentTagExpression(tag)

    dagPath.pop()
    fn_parent = OpenMaya.MFnDagNode(dagPath)
    for i in range(fn_parent.childCount()):
        child = fn_parent.child(i)
        fn_child = OpenMaya.MFnDependencyNode(child)
        if (child.hasFn(OpenMaya.MFn.kMesh) or
            child.hasFn(OpenMaya.MFn.kNurbsSurface) or
            child.hasFn(OpenMaya.MFn.kNurbsCurve)):
            try:
                if not fn_child.findPlug("intermediateObject", True).asBool():
                    dagPath = OpenMaya.MDagPath.getAPathTo(child)
                    break
            except RuntimeError:
                dagPath = OpenMaya.MDagPath.getAPathTo(child)
                break

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


######################################
# Skin Collectors
######################################


def collectInfluenceWeights(skinCls, dagPath, components, dataDic):
    weights = getCurrentWeights(skinCls, dagPath, components)

    influencePaths = OpenMaya.MDagPathArray()
    numInfluences = get_skin_cluster_fn(skinCls.name()).influenceObjects(
        influencePaths
    )
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
        # cast to float to avoid rounding errors when dividing integers?
        dataDic["vertexCount"] = int(weights.length() / float(numInfluences))
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


######################################
# Skin export
######################################


def exportSkin(filePath=None, objs=None, *args):
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
            if isinstance(obj.getShape(), pm.nodetypes.Mesh):
                # TODO: Implement pruning on nurbs. Less straight-forward
                pm.skinPercent(skinCls, obj, pruneWeights=0.001)

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
def exportSkinPack(packPath=None, objs=None, use_json=False, *args):
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
        if exportSkin(filePath, [obj], use_json):
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


def exportJsonSkinPack(packPath=None, objs=None, *args):
    exportSkinPack(packPath, objs, use_json=True)


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
def importSkin(filePath=None, *args):

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
    if filePath.endswith(FILE_EXT):
        with open(filePath, "rb") as fp:
            dataPack = pickle.load(fp)
    else:
        with open(filePath, "r") as fp:
            dataPack = json.load(fp)

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
                    meshVertices = sum([len(shape.cv) for shape in objShapes])
                elif isinstance(objNode.getShape(), pm.nodetypes.NurbsCurve):
                    # meshVertices = sum([len(shape.cv) for shape in objShapes])
                    meshVertices = sum(1 for _ in objShapes[0].cv)
                else:
                    # TODO: Implement other skinnable objs like lattices.
                    meshVertices = 0

                if compressed:
                    importedVertices = data["vertexCount"]
                else:
                    importedVertices = len(data["blendWeights"])
                if meshVertices != importedVertices:
                    warningMsg = "Vertex counts on {} do not match. {} != {}"
                    pm.displayWarning(
                        warningMsg.format(
                            objName, meshVertices, importedVertices
                        )
                    )
                    continue
            except Exception:
                pass

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


@utils.timeFunc
def importSkinPack(filePath=None, *args):
    if not filePath:
        filePath = pm.fileDialog2(
            fileMode=1, fileFilter="mGear skinPack (*%s)" % PACK_EXT
        )
    if not filePath:
        return
    if not isinstance(filePath, string_types):
        filePath = filePath[0]

    with open(filePath) as fp:
        packDic = json.load(fp)
        for pFile in packDic["packFiles"]:
            filePath = os.path.join(os.path.split(filePath)[0], pFile)
            importSkin(filePath, True)


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
            sourceMesh = pm.PyNode(targetMesh)

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

    Notes:
        - This function requires `pm` (pymel.core) and assumes the existence of
          a `skin.skinCopy` function for copying skin weights.
        - It also uses `getSkinCluster` to retrieve the skin cluster associated
          with a given mesh. Implementations of `skin.skinCopy` and `getSkinCluster`
          are assumed to be available in the current script or environment.

    No Longer Returned:
        None: This function does not return a value but modifies the target mesh
            by adding or updating its skinning information based on the source mesh.

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
