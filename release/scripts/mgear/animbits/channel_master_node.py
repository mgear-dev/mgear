import json
import ast
from maya import cmds
import mgear.pymaya as pm

from mgear.core import attribute
from mgear.core import string

from . import channel_master_utils as cmu
import sys
import os

if sys.version_info[0] == 2:
    string_types = (basestring,)
else:
    string_types = (str,)


__TAG__ = "_isChannelMasterNode"

# TODO: Node should store the current active tab

CHANNEL_MASTER_PATH = "CHANNEL_MASTER_PATH"


def _convert_path_token(file_path):
    """convert CHANNEL_MASTER_PATH env var to a full path

    Args:
        file_path (str): file path

    Returns:
        str: file path with updated token to path
    """
    path_token = "[{}]".format(CHANNEL_MASTER_PATH)
    if path_token in file_path:
        if os.environ.get(CHANNEL_MASTER_PATH, ""):
            file_path = file_path.replace(
                path_token, os.environ.get(CHANNEL_MASTER_PATH, "")
            )
    return file_path


def list_channel_master_nodes():
    """return a list of channel master nodes in the scene

    Returns:
        list: List of channel master nodes
    """
    return [n for n in cmds.ls("*.{}".format(__TAG__), o=True, r=True)]


def create_channel_master_node(name):
    """Create a new channel master node

    Args:
        name (str): name of the nodes

    Returns:
        str: name of the channel master node
    """

    # Create data node (render sphere for outliner "icon")
    shp = cmds.createNode("renderSphere")
    cmds.setAttr("{}.radius".format(shp), 0)
    cmds.setAttr("{}.isHistoricallyInteresting".format(shp), 0)
    cmds.setAttr("{}.v".format(shp), 0)

    # Rename data node
    node = cmds.listRelatives(shp, p=True)[0]
    node = cmds.rename(node, string.normalize(name))

    cmds.addAttr(node, ln=__TAG__, at="bool", dv=True)
    cmds.setAttr("{}.{}".format(node, __TAG__), k=False, l=True)
    cmds.addAttr(node, ln="data", dt="string")
    cmds.addAttr(node, ln="external_data", dt="string")
    cmds.addAttr(node, ln="use_node_namespace", at="bool", dv=True)
    cmds.addAttr(node, ln="force_local_data", at="bool", dv=False)

    attribute.lockAttribute(pm.PyNode(node))

    # init data
    cmds.setAttr(
        "{}.data".format(node),
        cmu.init_channel_master_config_data(),
        type="string",
    )
    return node


def get_external_data(node):
    if pm.PyNode(node).hasAttr("external_data"):
        path = cmds.getAttr("{}.external_data".format(node))
        if path and os.path.isfile(path):
            path = _convert_path_token(path)
            data = json.load(open(path))
            return data["config"]


def get_node_data(node):
    """Get the configuration data from a node
    Can get the data from the external data or from local data

    Args:
        node (str): nme of the node
        use_local_data (bool, optional): If true will force to use the node
                                         local data

    Returns:
        dict: configuration data
    """
    data = get_external_data(node)
    # if not data or use_local_data:
    if not data or cmds.getAttr("{}.force_local_data".format(node)):
        data = cmds.getAttr("{}.data".format(node))
        return ast.literal_eval(data)
    else:
        return data


def set_node_data(node, data):
    """Set the node data attribute

    Args:
        node (str): node name
        data (dict): configuration dict
    """
    cmds.setAttr("{}.data".format(node), data, type="string")


def export_data(node, tab=None, filePath=None):
    """Export the node data

    Args:
        node (str): node to export
        tab (str, optional): if a tab name is set, only that taba will
                              be exported
        filePath (str, optional): the path to save the configuration file

    Returns:
        TYPE: Description
    """
    # if isinstance(node, (str, unicode)):
    #     node = pm.PyNode(node)
    config = get_node_data(node)
    data = {}
    data["node_name"] = node
    if tab:
        if tab in config["tabs_data"].keys():
            config["tabs"] = [tab]
            tabs_data = {}
            tabs_data[tab] = config["tabs_data"][tab]
            config["tabs_data"] = tabs_data
        else:
            keys = config["tabs_data"].keys()
            pm.displayWarning(
                "Tab {}, not found int current node.".format(tab)
                + " Available tabs are: {}".format(keys)
            )
    data["config"] = config

    data_string = json.dumps(data, indent=4, sort_keys=True)
    if not filePath:
        filePath = pm.fileDialog2(
            fileMode=0,
            fileFilter="Channel Master Configuration .cmc (*%s)" % ".cmc",
        )
    if not filePath:
        return
    if not isinstance(filePath, string_types):
        filePath = filePath[0]
    f = open(filePath, "w")
    f.write(data_string)
    f.close()


def import_data(filePath=None, node=None, add_data=False):
    """Import and create channel master configuration nodes

    Args:
        filePath (str, optional): Path to the channel master config file
        node (None, str): Node to add the data. If None, will create a new node
        add_data (bool, optional): If true, will add the data to existing node

    Returns:
        TYPE: Description
    """
    if not filePath:
        filePath = pm.fileDialog2(
            fileMode=1,
            fileFilter="Channel Master Configuration .cmc (*%s)" % ".cmc",
        )

    if not filePath:
        return
    if not isinstance(filePath, string_types):
        filePath = filePath[0]
    data = json.load(open(filePath))
    config = data["config"]

    if not node:
        if data:
            node = create_channel_master_node(data["node_name"])
        else:
            pm.displayWarning("Data not imported!")
            return

    if add_data:
        config = get_node_data(node)
        for tab in data["config"]["tabs"]:
            tab_config = data["config"]["tabs_data"][tab]
            # ensure that tab name is unique when add to existing node
            init_tab_name = tab
            i = 1
            while tab in config["tabs"]:
                tab = init_tab_name + str(i)
                i += 1
            config["tabs"].append(tab)
            config["tabs_data"][tab] = tab_config

    set_node_data(node, config)

    return node


def set_external_config_path(node, filePath=None):
    """Set the path to the external file configuration

    Args:
        node (PyNode): Channel Master node
        filePath (str, optional): Path to the file confituration

    Returns:
        TYPE: Description
    """
    if not node:
        pm.displayWarning("Channel Master Node doesn't exist")
        return
    if not filePath:
        filePath = pm.fileDialog2(
            fileMode=1,
            fileFilter="Channel Master Configuration .cmc (*%s)" % ".cmc",
        )
    if not filePath:
        return
    else:
        # this enable back comatibility with old nodes just in case
        # the externa data attr is missing
        if not pm.PyNode(node).hasAttr("external_data"):
            cmds.addAttr(node, ln="external_data", dt="string")
        cmds.setAttr(
            "{}.external_data".format(node), filePath[0], type="string"
        )


def remove_external_config_path(node):
    cmds.setAttr("{}.external_data".format(node), "", type="string")
