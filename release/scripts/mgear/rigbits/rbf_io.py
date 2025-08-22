#!/usr/bin/env python
"""Handles the import and exporting of all supported RBF node types

Attributes:
    RBF_FILE_EXTENSION (str): extention of the serialized json data
    RBF_MODULES (Dict): nodeType: module api, normalized to fit the rbfManager

__author__ = "Rafael Villar"
__email__ = "rav@ravrigs.com"

"""
# python
import json
from .six import PY2

# core
import maya.cmds as mc

# RBF setups
if PY2:
    import mGearWeightNode_io
    import weightNode_io
else:
    from . import mGearWeightNode_io
    from . import weightNode_io

# debug
# reload(weightNode_io)
# =============================================================================
# Constants
# =============================================================================
RBF_FILE_EXTENSION = ".rbf"

# Additional node support should be added here
RBF_MODULES = {
    "mGearWeightDriver": mGearWeightNode_io,
    "weightDriver": weightNode_io,
}


# =============================================================================
# Data export
# =============================================================================
def fileDialog(startDir=None, mode=0):
    """prompt dialog for either import/export from a UI

    Args:
        startDir (str): A directory to start from
        mode (int, optional): import or export, 0/1

    Returns:
        str: path selected by user
    """
    ext = RBF_FILE_EXTENSION
    fPath = mc.fileDialog2(
        fileMode=mode,
        startingDirectory=startDir,
        fileFilter="mGear RBF (*{})".format(ext),
    )
    if fPath is not None:
        fPath = fPath[0]
    return fPath


def __importData(filePath):
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
        return None


def __exportData(data, filePath):
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


def importRBFs(filePath):
    """import rbfs from file, using the assoiciated module type to recreate

    Args:
        filePath (str): filepath to json

    Returns:
        n/a: n/a
    """
    data = __importData(filePath)
    if data is None:
        return
    for k, v in data.items():
        rbfModule = RBF_MODULES[v["rbfType"]]
        rbfModule.createRBFFromInfo({k: v})


def exportRBFs(nodes, filePath):
    """exports the desired rbf nodes to the filepath provided

    Args:
        nodes (list): of rbfnodes
        filePath (str): filepath to json
    """
    rbfNode_Info = {}
    for n in nodes:
        rbfType = mc.nodeType(n)
        rbfNode_Info[n] = RBF_MODULES[rbfType].getNodeInfo(n)
    __exportData(rbfNode_Info, filePath)
    print("RBF Data exported: {}".format(filePath))
