import json

from maya import cmds
from maya.api import OpenMaya

import mgear


def get_flattened_nodes(nodes):
    """Will 'flatten' sets to get all nodes"""
    # Init results
    results = []

    # Parse nodes
    for node in nodes or []:
        # Skip if not doesn't exists
        if not cmds.objExists(node):
            continue

        # Object set type
        if cmds.nodeType(node) == "objectSet":
            content = cmds.sets(node, q=True, no=True)
            set_nodes = get_flattened_nodes(content)

            for set_node in set_nodes:
                if set_node in results:
                    continue
                results.append(set_node)

            continue

        # Append not to results
        results.append(node)

    return results


def select_nodes(nodes, namespace=None, modifier=None):
    """Select maya node handler with specific modifier behavior"""
    # Parse nodes
    filtered_nodes = []
    for node in nodes:
        # Add namespace to node name
        if namespace:
            node = "{}:{}".format(namespace, node)

        # skip invalid nodes
        if not cmds.objExists(node):
            mgear.log(
                "node '{}' not found, skipping".format(node),
                mgear.sev_warning,
            )
            continue

        # Set case
        if cmds.nodeType(node) == "objectSet":
            content = get_flattened_nodes([node])
            filtered_nodes.extend(content)
            continue

        filtered_nodes.append(node)

    # Stop here on empty list
    if not filtered_nodes:
        return

    # Remove duplicates
    filtered_nodes = list(set(filtered_nodes))

    # No modifier case selection
    if not modifier:
        return cmds.select(filtered_nodes)

    # Control case (toggle)
    if modifier == "control":
        return cmds.select(filtered_nodes, tgl=True)

    # Alt case (remove)
    elif modifier == "alt":
        return cmds.select(filtered_nodes, d=True)

    # Shift case (add) and none
    else:
        return cmds.select(filtered_nodes, add=True)


def reset_node_attributes(node, attr="rigBindPose"):
    """Will reset attribute to stored values"""
    # Sanity check
    if not cmds.objExists(node):
        mgear.log(
            "reset_node_attributes -> '{}' not found, skipping".format(node),
            mgear.sev_warning,
        )
        return

    # Check for attribute
    if not cmds.attributeQuery(attr, n=node, ex=True):
        mgear.log(
            "reset_node_attributes -> '{}' has no attribute named '{}', "
            "skipping".format(node, attr),
            mgear.sev_warning,
        )
        return

    # Get attributes dictionary (stored as JSON)
    str_values = cmds.getAttr("{}.{}".format(node, attr))
    if not str_values:
        return
    try:
        attr_values = json.loads(str_values)
    except (ValueError, TypeError) as exc:
        mgear.log(
            "reset_node_attributes -> stored data for node '{}' is not "
            "valid JSON ({})".format(node, exc),
            mgear.sev_warning,
        )
        return

    # Check type
    if not isinstance(attr_values, dict):
        mgear.log(
            "reset_node_attributes -> stored data for node '{}' is not a "
            "dictionary".format(node),
            mgear.sev_warning,
        )
        return

    # Apply values
    for attr_key in attr_values:
        # Check if attribute exists
        if not cmds.attributeQuery(attr_key, n=node, ex=True):
            continue

        # Apply stored value
        try:
            cmds.setAttr("{}.{}".format(node, attr_key), attr_values[attr_key])
        except Exception:
            mgear.log(
                "reset_node_attributes -> failed to set attribute '{}.{}' "
                "to {}".format(node, attr, str(attr_values[attr_key])),
                mgear.sev_warning,
            )

    return True


class SelectionCheck(object):
    def __init__(self):
        self.sel = OpenMaya.MSelectionList()

    def update(self):
        """Will update selection data"""
        # Get current selection (API 2.0 returns a new list)
        self.sel = OpenMaya.MGlobal.getActiveSelectionList()

    @staticmethod
    def get_node_mobject(node):
        """Will return node mobject if possible"""
        # Sanity check
        if not cmds.objExists(node):
            return None

        # Cast node to MSelectionList and return its mobject
        nodes = OpenMaya.MSelectionList()
        nodes.add(node)
        return nodes.getDependNode(0)

    @classmethod
    def get_node_mdagpath(cls, node):
        """Return node MDagPath if possible"""
        mobject = cls.get_node_mobject(node)
        if mobject is None:
            return None

        # Abort if not a Dag object
        if not mobject.hasFn(OpenMaya.MFn.kDagNode):
            return None

        return OpenMaya.MDagPath.getAPathTo(mobject)

    def is_selected(self, node):
        """Will check if node is currently selected"""
        # Get node MDagPath
        node = self.get_node_mdagpath(node)
        if not node:
            return False

        # Check if node is in selection list
        return self.sel.hasItem(node)
