from maya import cmds
import re
from . import base
from . import node
from . import geometry


def __find_attr(name):

    nspts = re.split("[.]", name)
    cur = node.BindNode(nspts[0])
    for n in nspts[1:]:
        res = re.search("([^[]+)\[?([0-9]+)?\]?", n)
        if not res:
            raise Exception("Unexpected name")

        an, ai = res.groups()
        cur = getattr(cur, an)
        if ai is not None:
            i = int(ai)
            cur = cur.__getitem__(i)

    return cur


def PyNode(name_or_node):
    """
    Find the corresponding node, attribute, or geometry in the Maya scene.

    Args:
        name_or_node (str or base.Base): The name of the node or attribute, or an existing object.

    Returns:
        The corresponding node, attribute, or geometry object.

    Raises:
        RuntimeError: If the node or attribute does not exist in the scene.
    """

    # If the input is already a Base type, return it directly
    if isinstance(name_or_node, base.Base):
        return name_or_node

    # Check if it's an attribute (contains a ".")
    if "." in name_or_node:
        try:
            # Try to find the attribute
            return __find_attr(name_or_node)
        except Exception:
            # If attribute search fails, try geometry binding
            bound = geometry.BindGeometry(name_or_node, silent=True)
            if bound:
                return bound
            else:
                # If both fail, raise an error indicating it doesn't exist
                raise RuntimeError(
                    "Attribute or geometry '{}' does not exist.".format(
                        name_or_node
                    )
                )
    else:
        # Check if the node exists before attempting to bind
        if not cmds.objExists(name_or_node):
            raise RuntimeError(
                "Node '{}' does not exist.".format(name_or_node)
            )

        # If it exists, bind and return the node
        return node.BindNode(name_or_node)
