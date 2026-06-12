# Weigth maps IO

import json

from maya import cmds
import mgear.pymaya as pm
import maya.OpenMaya as OpenMaya
string_types = str

FILE_EXT = ".wmap"


def get_weights(deformer):
    """Get the weight map from a given deformers

    It supports multiple objects/weight maps for one sigle deformer

    Args:
        deformer (PyNode or str): Name or pynode of a deformer with weight map

    Returns:
        dict: The weights dictionary
    """
    if isinstance(deformer, string_types):
        deformer = pm.PyNode(deformer)
    dataDic = {}
    dataDic["_deformed_index"] = []
    try:
        fnSet = OpenMaya.MFnSet(deformer.__apimfn__().deformerSet())
        members = OpenMaya.MSelectionList()
        fnSet.getMembers(members, False)
        dagPath = OpenMaya.MDagPath()
        components = OpenMaya.MObject()
        members.getDagPath(0, dagPath, components)

        for m in range(members.length()):
            dagPath = OpenMaya.MDagPath()
            members.getDagPath(m, dagPath, components)
            weights = OpenMaya.MFloatArray()
            deformer.__apimfn__().getWeights(dagPath, components, weights)
            dataDic[dagPath.fullPathName()] = [
                weights[i] for i in range(weights.length())
            ]
            dataDic["_deformed_index"].append(dagPath.fullPathName())
    except:
        # Fallback to Maya cmds if Open Maya deformerSet and getWeights Fail
        # Since Maya 2022 with new Component tags system this 2 method are not
        # working because deformer Set are not used anymore
        def_objs = deformer.outputGeometry.listConnections()
        for e, mesh in enumerate(def_objs):
            VertexNb = cmds.polyEvaluate(mesh.name(), v=1) - 1
            weight = cmds.getAttr(
                "{0}.weightList[{1}].weights[0:{2}]".format(
                    deformer.name(), e, VertexNb
                )
            )
            dataDic[mesh.fullPathName()] = weight
            dataDic["_deformed_index"].append(mesh.fullPathName())

    return dataDic


def set_weights(deformer, dataWeights):
    """Set the weight map from a given deformers

    It supports multiple objects/weight maps for one sigle deformer

    Args:
        deformer (PyNode or str): Name or pynode of a deformer with weight map
    """

    if isinstance(deformer, string_types):
        deformer = pm.PyNode(deformer)
    try:
        fnSet = OpenMaya.MFnSet(deformer.__apimfn__().deformerSet())
        members = OpenMaya.MSelectionList()
        fnSet.getMembers(members, False)
        dagPath = OpenMaya.MDagPath()
        components = OpenMaya.MObject()
        members.getDagPath(0, dagPath, components)

        for m in range(members.length()):
            dagPath = OpenMaya.MDagPath()
            members.getDagPath(m, dagPath, components)
            dw = dataWeights[dagPath.fullPathName()]
            weights = OpenMaya.MFloatArray(len(dw))
            for x in range(len(dw)):
                weights.set(dw[x], int(x))

            deformer.__apimfn__().setWeight(dagPath, components, weights)
    except:
        # Fallback to Maya cmds if Open Maya deformerSet and getWeights Fail
        # Since Maya 2022 with new Component tags system this 2 method are not
        # working because deformer Set are not used anymore
        def_objs = deformer.outputGeometry.listConnections()
        for mesh in def_objs:
            if mesh.fullPathName() in dataWeights.keys():
                weights = dataWeights[mesh.fullPathName()]
                VertexNb = cmds.polyEvaluate(mesh.name(), v=1) - 1
                idx = dataWeights["_deformed_index"].index(mesh.fullPathName())
                cmds.setAttr(
                    "{0}.weightList[{1}].weights[0:{2}]".format(
                        deformer.name(), idx, VertexNb
                    ),
                    *weights,
                    size=len(weights)
                )


def export_weights(deformer, filePath):
    """Export the wmap to a  json file

    Args:
        deformer (PyNode or str): Name or pynode of a deformer with weight map
        filePath (str): Path to save the file
    """
    wdata = get_weights(deformer)
    with open(filePath, "w") as fp:
        json.dump(wdata, fp, indent=4, sort_keys=True)


def import_weights(deformer, filePath):
    """Import the wmap from a  json file

    Args:
        deformer (PyNode or str): Name or pynode of a deformer to
                                  assign the wmap
        filePath (str): Path to load the file
    """
    with open(filePath, "r") as fp:
        wdata = json.load(fp)
    set_weights(deformer, wdata)


def export_weights_selected(filePath=None, *args):
    """Export the wmap to a  json file from selected objet

    Args:
        filePath (str): Path to save the file. If None wil pop up file browser
    """
    oSel = pm.selected()
    if oSel:
        deformer = oSel[0]
    else:
        pm.displayWarning("Nothing selected to export weights")
        return

    if not filePath:
        filePath = file_browser(mode=0)
    if not filePath:
        return

    export_weights(deformer, filePath)


def import_weights_selected(filePath=None, *args):
    """Import the wmap to from  json file from selected objet

    Args:
        filePath (str): Path to load the file. If None wil pop up file browser
    """
    oSel = pm.selected()
    if oSel:
        deformer = oSel[0]
    else:
        pm.displayWarning("Nothing selected to import weights")
        return

    if not filePath:
        filePath = file_browser(mode=1)
    if not filePath:
        return

    import_weights(deformer, filePath)


def file_browser(mode=1):
    """open file browser

    Args:
        mode (int, optional): 0 save mode, 1 load mode

    Returns:
        str: file path
    """
    fileFilters = "Deformer Weigth map (*{})".format(FILE_EXT)
    startDir = pm.workspace(q=True, rootDirectory=True)
    filePath = pm.fileDialog2(
        fileMode=mode, startingDirectory=startDir, fileFilter=fileFilters
    )
    if filePath:
        return filePath[0]
    else:
        return False
