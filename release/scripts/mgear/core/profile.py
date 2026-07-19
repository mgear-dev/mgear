from contextlib import contextmanager
from typing import Iterable, Set, Tuple

from maya import cmds

from mgear.core import color


@contextmanager
def add_profiler_tag_to_created_nodes(
    tag_name: str, tag_color: Tuple[float, float, float]
):
    """
    Context manager that tags newly created Maya nodes with a profiler tag.

    Captures the scene state before entering the block, then compares it
    after execution to determine which nodes were created. Newly created
    nodes are assigned the provided profiler tag and color.

    Args:
        tag_name: Name of the profiler tag to apply.
        tag_color: RGB color (float, float, float) used for the tag.
    """
    before_nodes: Set[str] = set(cmds.ls())
    try:
        yield
    finally:
        after_nodes: Set[str] = set(cmds.ls())
        added_nodes: Set[str] = after_nodes - before_nodes
        add_profiler_tag(added_nodes, tag_name, tag_color)


def set_metadata_color(node: str, byte_color: Tuple[float, float, float]):
    for i, value in enumerate(byte_color):
        cmds.editMetadata(
            node,
            streamName="ProfileTagColorStream",
            memberName="NodeProfileTagColor",
            channelName="ProfileTagColor",
            value=value,
            index=i,
        )


def add_profiler_tag(
    node: str | Iterable[str], tag_name: str, tag_color: Tuple[float, float, float]
):
    """
    Add a profiler tag to a node for rig speed profiling based on part/name.

    Args:
        node: Node(s) to be tagged.
        tag_name: Name for the tag (for example a rig part name).
        tag_color: RGB color for the tag, if None it will be generated automatically from the tag_name.
    """

    # Create the data structure. See documentation here:
    # https://help.autodesk.com/view/MAYAUL/2024/ENU/?guid=GUID-8D5FFC12-608C-45EA-B035-1AB56F3C42F1
    if "NodeProfileStruct" not in (cmds.dataStructure(q=True) or []):
        cmds.dataStructure(
            format="raw",
            asString="name=NodeProfileStruct:string=NodeProfileTag:int32=NodeProfileTagColor",
        )

    if isinstance(node, str):
        nodes = [node]
    else:
        nodes = node

    for node in nodes:
        try:
            # tagging meshes will break GPU evaluation. so skip mesh nodes
            if cmds.nodeType(node) == "mesh":
                continue
            # Add metadata channels only if they don't yet exist
            extant_metadata: list[str] = (
                cmds.addMetadata(node, q=True, channelName=True) or []
            )
            if "ProfileTag" in extant_metadata and "ProfileTagColor" in extant_metadata:
                continue
            if "ProfileTag" not in extant_metadata:
                cmds.addMetadata(
                    node,
                    streamName="ProfileTagStream",
                    channelName="ProfileTag",
                    structure="NodeProfileStruct",
                )
            if "ProfileTagColor" not in extant_metadata:
                cmds.addMetadata(
                    node,
                    streamName="ProfileTagColorStream",
                    channelName="ProfileTagColor",
                    structure="NodeProfileStruct",
                )
            # Set the actual metadata
            cmds.editMetadata(
                node,
                streamName="ProfileTagStream",
                memberName="NodeProfileTag",
                channelName="ProfileTag",
                stringValue=tag_name,
                index=0,
            )
            # Set the tag color value
            byte_color: tuple[int, int, int] = color.float_to_byte_color(tag_color)
            set_metadata_color(node, byte_color)
        except Exception:
            pass
