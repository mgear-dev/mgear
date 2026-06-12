import mgear.pymaya as pm


def find_connected_proximity_pin_node(source_mesh):
    """
    Check if the Mesh Source object worldMesh[0] output of an object is connected to the
    deformedGeometry of a proximityPin node. Return the proximityPin node as
    a PyNode if found.

    Args:
        source_mesh (pyNode or str): Name of the source Mesh object.

    Returns:
        pymel.core.general.PyNode: The connected proximityPin node as a PyNode
            if a connection exists, otherwise None.
    """
    # Get the source worldMesh[0] plug as PyNode
    if isinstance(source_mesh, str):
        source_mesh = pm.PyNode(source_mesh)
    source_plug = source_mesh.worldMesh[0]

    # Find all destination connections from this plug
    connections = source_plug.connections(d=True, s=False, p=True)

    # Check each connection to see if it is to a proximityPin node
    for connection in connections:
        # The node connected to
        node = connection.node()
        # Check if this node is of the type 'proximityPin'
        if node.type() == "proximityPin":
            # Check if the connected attribute is deformedGeometry
            if "deformedGeometry" in connection.name():
                return node

    return None


def find_connected_uv_pin_node(source_nurbs):
    """
    Check if the NURBS source object worldSpace[0] output of an object is connected to the
    deformedGeometry of a uvPin node. Return the proximityPin node as
    a PyNode if found.

    Args:
        source_nurbs (pyNode or str): Name of the source NURBS object.

    Returns:
        pymel.core.general.PyNode: The connected proximityPin node as a PyNode
            if a connection exists, otherwise None.
    """
    # Get the source worldSpace[0] plug as PyNode
    if isinstance(source_nurbs, str):
        source_nurbs = pm.PyNode(source_nurbs)
    source_plug = source_nurbs.worldSpace[0]
    # Find all destination connections from this plug
    connections = source_plug.connections(d=True, s=False, p=True)

    # Check each connection to see if it is to a proximityPin node
    for connection in connections:
        # The node connected to
        node = connection.node()
        # Check if this node is of the type 'proximityPin'
        if node.type() == "uvPin":
            # Check if the connected attribute is deformedGeometry
            if "deformedGeometry" in connection.name():
                return node

    return None
