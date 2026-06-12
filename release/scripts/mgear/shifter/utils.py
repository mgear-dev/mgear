from mgear import pymaya as pm
from typing import Any, Iterable, List, Optional


def get_deformer_joint_grp(rigTopNode):
    """
    Searches for a node group that ends with "_deformers_grp" under the given rigTopNode.

    Args:
        rigTopNode (pm.PyNode): The top-level rig node where we start the search.

    Returns:
        pm.PyNode or None: Returns the deformer joints node if found, otherwise returns None.
    """
    deformer_jnts_node = None
    for i in range(0, 100):
        try:
            potential_node = rigTopNode.rigGroups[i].connections()[0]
        except IndexError:
            break

        if potential_node.name().endswith("_deformers_grp"):
            deformer_jnts_node = potential_node
            break
    return deformer_jnts_node


def get_deformer_joints(rigTopNode):
    """
    Retrieves the deformer joints under the given rigTopNode.

    Args:
        rigTopNode (pm.PyNode): The top-level rig node to search under.

    Returns:
        list or None: Returns a list of deformer joints if found, otherwise displays an error and returns None.
    """
    deformer_jnts_node = get_deformer_joint_grp(rigTopNode)
    if deformer_jnts_node:
        deformer_jnts = deformer_jnts_node.members()
    else:
        deformer_jnts = None

    if not deformer_jnts:
        pm.displayError(
            "{} is empty. The tool can't find any joint".format(rigTopNode)
        )
    return deformer_jnts


def get_root_joint(rigTopNode):
    """
    Retrieves the root joint of the rig from the rigTopNode.

    Args:
        rigTopNode (pm.PyNode): The top-level rig node to search under.

    Returns:
        pm.PyNode: Returns the root joint node.
    """
    jnt_org = rigTopNode.jnt_vis.listConnections()[0]
    root_jnt = jnt_org.child(0)
    return root_jnt


def get_guide() -> List[pm.PyNode]:
    """
    Get the guide top node in the scene.

    :return: List of guide nodes that have the attribute 'ismodel'.
    """
    return pm.ls("*.ismodel") or []


def get_rig() -> List[pm.PyNode]:
    """
    Get the rig top node in the scene.

    :return: List of rig nodes that have the attribute 'is_rig'.
    """
    return pm.ls("*.is_rig") or []


def get_rig_name(guide: str) -> [str]:
    """
    Get the rig name from the guide.
    """
    return pm.getAttr(f"{guide}.rig_name")


def get_components(guide_name: str) -> List[pm.PyNode]:
    """
    Return all valid component transforms under the given guide.

    Traverses all descendant transforms of the guide and filters out
    nodes that do not have a 'comp_type' attribute.

    :param guide_name: Name of the guide root.
    :return: List of component transform nodes that have 'comp_type'.
    :rtype: list
    """
    components = pm.listRelatives(guide_name,
                                  children=True,
                                  allDescendents=True,
                                  type="transform",
                                  fullPath=True)

    valid_components: List[pm.PyNode] = []
    # -- Filter out components
    for cmp in components:
        if not cmp.hasAttr("comp_type"):
            continue
        valid_components.append(cmp)

    return valid_components


def obj_exists(node: str) -> bool:
    """
    Check whether a DAG or DG node exists in the Maya scene.

    :param node: Name of the node to check.
    :return: True if the node exists, otherwise False.
    """
    return bool(node) and pm.objExists(node)


def select_items(items: Iterable[str], replace: bool = True) -> None:
    """
    Select the given items in the Maya scene.

    :param items: A single node name or a list/iterable of node names.
    :param replace: If True, replace the current selection. If False, add to it.
    :return: None
    """
    # -- Normalize to list and filter only items that exist
    normalized: List[str] = [i for i in to_list(items) if obj_exists(i)]

    if not normalized:
        return

    if replace:
        pm.select(clear=True)

    pm.select(normalized, add=not replace)


def to_list(x) -> List[str]:
    """
    Normalize an input into a flat list of strings.

    :param x: A string, iterable of strings, or any value.
    :return: A list of strings.
    """
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    if isinstance(x, Iterable):
        return list(x)
    return [x]


def delete_nodes(nodes: List) -> None:
    """
    Delete the given Maya nodes safely.

    :param nodes: List of node names or PyNodes to delete.
    :type nodes: List
    """
    for node in nodes:
        try:
            pm.delete(node)
        except:
            print(f"Could not delete node: {node}")


def select_by_uuid(uuid: str) -> Optional[pm.PyNode]:
    """
    Select a Maya node by its UUID.

    :param uuid: The UUID of the node to select.
    :return: The selected PyNode, or None if no node was found.
    """
    node = node_from_uuid(uuid=uuid)

    # -- Exit early
    if node is None:
        return

    pm.select(node, replace=True)

    return node


def node_from_uuid(uuid: str) -> Optional[pm.PyNode]:
    """
    Resolve a Maya node from its UUID.

    :param str uuid: The UUID string of the node to look up.
    :return: The resolved PyNode if it exists, otherwise 'None'.
    :rtype: Optional[pm.PyNode]
    """
    try:
        nodes = pm.ls(uuid, uuid=True)
    except Exception:
        return None
    return nodes[0] if nodes else None


def uuid_from_node(node: Any) -> Optional[str]:
    """
    Return the UUID string for a given Maya node.

    :param Any node: A node reference, name, or PyNode-like object.
    :return: The UUID string if resolved, otherwise 'None'.
    :rtype: Optional[str]
    """

    pynode = node_from_name(node)

    if pynode is None:
        return None

    try:
        uuids = pm.ls(pynode, uuid=True)
    except Exception:
        return None

    return uuids[0] if uuids else None


def node_from_name(name: str) -> Optional[pm.PyNode]:
    """
    Resolve a Maya node from its name.

    :param str name: The node name to convert into a PyNode.
    :return: The resolved PyNode if it exists, otherwise 'None'.
    :rtype: Optional[pm.PyNode]
    """
    try:
        return pm.PyNode(name)
    except Exception:
        return None


def get_selection() -> List[pm.PyNode]:
    """
    Return the current Maya selection as a list of PyNodes.

    :return: List of selected nodes.
    """
    return pm.ls(selection=True)


def find_component_root(node):
    """
    Walks up the DAG hierarchy from the given node until a node with
    the `comp_type` attribute is found. This identifies the root of an
    mGear component or guide.

    :param node: Node to start searching from. Can be a name or PyNode.
    :return: The component root node, or None if not found.
    """
    if isinstance(node, str):
        node = pm.PyNode(node)

    current = node

    while current:
        if current.hasAttr("comp_type"):
            return current
        parent = current.getParent()
        if not parent or parent == current:
            break
        current = parent

    return None