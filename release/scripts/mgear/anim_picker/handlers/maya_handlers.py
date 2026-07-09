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


def _shape_cv_points(shape):
    """Return a shape's world-space CV / vertex points (empty on failure).

    Args:
        shape (str): a nurbsCurve / nurbsSurface / mesh shape node.

    Returns:
        list: ``(x, y, z)`` world-space points.
    """
    sel = OpenMaya.MSelectionList()
    try:
        sel.add(shape)
        dag = sel.getDagPath(0)
    except Exception:
        return []
    world = OpenMaya.MSpace.kWorld
    node_type = cmds.nodeType(shape)
    try:
        if node_type == "nurbsCurve":
            points = OpenMaya.MFnNurbsCurve(dag).cvPositions(world)
        elif node_type == "nurbsSurface":
            points = OpenMaya.MFnNurbsSurface(dag).cvPositions(world)
        elif node_type == "mesh":
            points = OpenMaya.MFnMesh(dag).getPoints(world)
        else:
            return []
    except Exception:
        return []
    return [(point.x, point.y, point.z) for point in points]


def _bounding_box_points(node):
    """Return the eight world-bounding-box corners of ``node`` (or empty)."""
    if not cmds.objExists(node):
        return []
    x0, y0, z0, x1, y1, z1 = cmds.exactWorldBoundingBox(node)
    return [
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y1, z0),
        (x0, y1, z0),
        (x0, y0, z1),
        (x1, y0, z1),
        (x1, y1, z1),
        (x0, y1, z1),
    ]


def get_shape_points(node):
    """Return a node's world-space shape points for the trace tool.

    Gathers NURBS curve / surface CVs or mesh vertices in world space via the
    Maya API; when the node has no such shape (or the query fails) it falls
    back to the eight corners of the world bounding box, so the trace never
    fails on an unusual control.

    Args:
        node (str): a transform or shape node name.

    Returns:
        list: ``(x, y, z)`` world-space points (empty only for a bad node).
    """
    if not cmds.objExists(node):
        return []
    if cmds.nodeType(node) == "transform":
        shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
    else:
        shapes = [node]

    points = []
    for shape in shapes:
        points.extend(_shape_cv_points(shape))

    if points:
        return points
    return _bounding_box_points(node)


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
