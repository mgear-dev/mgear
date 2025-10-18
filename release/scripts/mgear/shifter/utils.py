from mgear import pymaya as pm


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


def get_guide():
    """
    Get the guide top node in the scene.
    """
    return pm.ls("*.ismodel") or []
