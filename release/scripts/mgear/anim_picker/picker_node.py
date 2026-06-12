from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# python
import sys
import os

# dcc
from maya import cmds
import mgear.pymaya as pm

# anim picker
import mgear.anim_picker
from .handlers import maya_handlers
from .handlers import file_handlers


def get_nodes():
    """Return data nodes found in scene"""
    data_nodes = []
    for maya_node in (
        cmds.ls("*.{}".format(DataNode.__TAG__), o=True, r=True) or []
    ):
        data_node = DataNode(maya_node)
        data_node.read_data()
        data_nodes.append(data_node)

    data_nodes.sort()
    return data_nodes


def get_node_for_object(item):
    """Will try to return related picker data_node for specified object"""
    namespaces = []

    # No namespace case
    if not cmds.referenceQuery(item, inr=True):
        namespaces.append(":")

    # Referenced node case
    else:
        prev_namespace = ":"
        for namespace in item.split(":")[:-1]:
            namespace = "{}{}:".format(prev_namespace, namespace)
            namespaces.append(namespace)

    # Parse namespaces
    for namespace in namespaces:
        for data_node in (
            cmds.ls("{}*.{}".format(namespace, DataNode.__TAG__), o=True) or []
        ):
            data_node = DataNode(data_node)
            if data_node.countains(item.replace(namespace[1:], "")):
                return data_node
    return False


# =============================================================================
# classes
# =============================================================================
class DataNode(object):
    # Pipeline
    __NODE__ = "PICKER_DATAS"
    __TAG__ = "picker_datas_node"

    # Attributes names
    __DATAS_ATTR__ = "picker_datas"
    __FILE_ATTR__ = "picker_datas_file"
    __VERSION_ATTR__ = "picker_version"

    def __init__(self, name=None):
        self.name = name
        if not name:
            self.name = self.__NODE__

        self.data = {}
        if cmds.objExists(self.name):
            self.data = self.read_data()

    def __repr__(self):
        return "{}.{}(u'{}')".format(
            self.__class__.__module__, self.__class__.__name__, self.name
        )

    def __eq__(self, other):
        """Compare datas"""
        return self.data == other

    def __lt__(self, other):
        """Override for "sort" function"""
        return self.name < other.name

    def __str__(self):
        return self.name

    def __melobject__(self):
        """Return maya mel friendly string result"""
        return self.name

    def exists(self):
        return cmds.objExists(self.name)

    def _assert_exists(self):
        assert self.exists(), "Data node '{}' not found.".format(self.name)

    def is_referenced(self):
        return cmds.referenceQuery(self.name, inr=True)

    def _assert_not_referenced(self):
        assert (
            self.is_referenced
        ), "Data node '{}' is referenced, and can not \
        be modified.".format(
            self.name
        )

    def create(self, node=None):
        """Will create the node data

        if a node is provided will create the picker data in the node. If not
        will create a new node

        Args:
            node (PyNode, optional): node to add the picker data

        Returns:
            TYPE: Description
        """
        if node:
            if node.hasAttr("picker_datas_node"):
                pm.displayWarning(
                    "{} have anim picker data".formant(node.name())
                )
            else:
                node = node.name()

        else:
            # Abort if node already exists
            if cmds.objExists(self.name):
                sys.stderr.write("node '{}' already exists.".format(self.name))
                return self.name

            # Create data node (render sphere for outliner "icon")
            shp = cmds.createNode("renderSphere")
            cmds.setAttr("{}.radius".format(shp), 0)
            cmds.setAttr("{}.v".format(shp, 0))

            # Rename data node
            node = cmds.listRelatives(shp, p=True)[0]
            node = cmds.rename(node, self.name)

        # Tag data node
        cmds.addAttr(node, ln=self.__TAG__, at="bool", dv=True)
        cmds.setAttr("{}.{}".format(node, self.__TAG__), k=False, l=True)

        # Add version attribute
        self._add_str_attr(node, self.__VERSION_ATTR__)
        self.set_version()

        # Add datas path attribute
        self._add_str_attr(node, self.__DATAS_ATTR__)

        # Add data file path attribute
        self._add_str_attr(node, self.__FILE_ATTR__)

    # =========================================================================
    # Maya attributes
    def _get_attr(self, attr):
        """Return node's attribute value"""
        self._assert_exists()
        if not cmds.attributeQuery(attr, n=self.name, ex=True):
            return
        return cmds.getAttr("{}.{}".format(self.name, attr)) or None

    def _add_str_attr(self, node, ln):
        """Add string attribute to data node"""
        self._assert_exists()

        cmds.addAttr(node, ln=ln, dt="string")
        cmds.setAttr("{}.{}".format(node, ln), k=False, l=False, type="string")

    def _set_str_attr(self, attr, value=None):
        """Set string attribute value"""
        # Sanity check
        self._assert_exists()
        self._assert_not_referenced()

        # Init value
        if not value:
            value = ""

        # Unlock attribute
        cmds.setAttr("{}.{}".format(self.name, attr), l=False, type="string")

        # Set value and re-lock attr
        cmds.setAttr(
            "{}.{}".format(self.name, attr), value, l=True, type="string"
        )

    def get_namespace(self):
        """Return namespace for current node"""
        self._assert_exists()
        if not self.name.count(":"):
            return None
        return self.name.rsplit(":", 1)[0]

    def get_file_path(self):
        """Return stored file path"""
        return self._get_attr(self.__FILE_ATTR__)

    # ==========================================================================
    # Set attributes
    def get_data(self):
        return self.data

    def set_data(self, data):
        self.data = data

    def write_data(
        self, data=None, to_node=True, to_file=False, file_path=None
    ):
        """Write data to data node and data file"""
        if not data:
            data = self.data

        # Write data to file
        if to_file:
            file_handlers.write_data_file(file_path, data=data)
            self._set_str_attr(self.__FILE_ATTR__, value=file_path)

        # Write data to node attribute
        if to_node:
            self._set_str_attr(self.__DATAS_ATTR__, value=data)

    def read_data_from_node(self):
        """Read data from data node or data file"""
        # Init data dict
        data = {}

        # Get data from attribute
        attr_data = self._get_attr(self.__DATAS_ATTR__)
        if attr_data:
            data = eval(attr_data)

        return data

    def read_data_from_file(self):
        """Read data from specified file"""
        file_path = self.get_file_path()
        if not file_path:
            return
        if not os.path.exists(
            file_handlers.replace_token_with_path(file_path)
        ):
            return

        return file_handlers.read_data_file(file_path)

    def read_data(self, from_file=True):
        """Read picker data"""
        self._assert_exists()

        # Init data dict
        data = {}

        # Read data from file
        if from_file:
            data = self.read_data_from_file()

        # Read data from node
        if not data:
            data = self.read_data_from_node()

        self.data = data
        return data

    def countains(self, node):
        """Will return True if data_node contains selected node in
        related controls data
        """
        for tab_data in self.data["tabs"]:
            for item_data in tab_data.get("data", {}).get("items", []):
                if not item_data:
                    continue
                controls = item_data.get("controls", [])
                controls = maya_handlers.get_flattened_nodes(controls)
                if controls.count(node):
                    return True
        return False

    def set_version(self, version=None):
        """Set node data version attribute"""
        if not version:
            version = mgear.anim_picker.version.version

        attrPlug = "{}.{}".format(self.name, self.__VERSION_ATTR__)
        cmds.setAttr(attrPlug, k=False, l=False)
        cmds.setAttr(attrPlug, str(version), l=True, type="string")
