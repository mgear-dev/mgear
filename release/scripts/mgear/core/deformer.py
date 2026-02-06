import mgear.pymaya as pm
from maya import cmds

import maya.internal.nodes.proximitywrap.node_interface as ifc


def is_deformer(node):
    """check if the node is from a deformer type

    Args:
        node (TYPE): node to check

    Returns:
        TYPE: bool
    """
    deformer_types = set(
        [
            "skinCluster",
            "blendShape",
            "nonLinear",
            "ffd",
            "cluster",
            "sculpt",
            "wire",
            "wrap",
            "jiggle",
            "deltaMush",
            "softMod",
            "morph",
        ]
    )
    node_type = pm.nodeType(node)
    return node_type in deformer_types


def filter_deformers(node_list):
    """Filter the list of nodes to only return the deformers

    Args:
        node_list (list): list of pyNode

    Returns:
        TYPE: filtered list of pyNode
    """
    deformer_list = []
    for node in node_list:
        if is_deformer(node):
            deformer_list.append(node)
    return deformer_list


def create_cluster_on_curve(curve, control_points=None):
    """
    Create a cluster deformer on a given curve at specified control points.

    Args:
        curve (str or PyNode): The name or PyNode of the curve to apply
            the cluster deformer.
        control_points (list of int, optional): List of control point
            indices to affect. Applies to all if None. Default is None.

    Returns:
        tuple: The name of the cluster and the name of the cluster handle.
    """
    # Check if curve is a PyNode, if not make it one
    if not isinstance(curve, pm.nt.Transform):
        curve = pm.PyNode(curve)

    # If control_points is None, apply cluster to the entire curve
    if control_points is None:
        cluster_node, cluster_handle = pm.cluster(curve)
    else:
        # Generate list representing the control points on the curve
        control_points_list = [
            "{}.cv[{}]".format(curve, i) for i in control_points
        ]

        # Create the cluster deformer
        cluster_node, cluster_handle = pm.cluster(control_points_list)

    return cluster_node, cluster_handle


def create_proximity_wrap(
    target_geos,
    driver_geos,
    deformer_name=None,
    weights_path=None,
    weights_filename=None,
    smoothInfluences=0,

):
    """
    Create a proximity wrap deformer.

    Args:
        target_geos: Single geometry or list of geometries to be deformed (string or PyNode)
        driver_geos: Single driver geometry or list of drivers (string or PyNode)
        deformer_name: Optional name for the deformer. If None, generates from first target geo.
        weights_path: Optional path to the weights file directory
        weights_filename: Optional filename for the weights (defaults to deformer_name + ".json")

    Returns:
        The renamed deformer node name
    """
    # Ensure lists
    if not isinstance(target_geos, (list, tuple)):
        target_geos = [target_geos]
    if not isinstance(driver_geos, (list, tuple)):
        driver_geos = [driver_geos]

    # Convert strings to PyNodes
    target_geos = [pm.PyNode(geo) if isinstance(geo, str) else geo for geo in target_geos]
    driver_geos = [pm.PyNode(geo) if isinstance(geo, str) else geo for geo in driver_geos]

    # Generate deformer name if not provided
    if deformer_name is None:
        base_name = target_geos[0].name().split("|")[-1].split(":")[-1]
        deformer_name = f"{base_name}_proximityWrap"

    # Create the proximity wrap deformer on all target geos
    target_names = [geo.name() for geo in target_geos]
    d = cmds.deformer(target_names, type="proximityWrap")
    pwni = ifc.NodeInterface(d[0])

    # Add all drivers (Maya 2023 changed method name to addDrivers)
    for driver_geo in driver_geos:
        try:
            pwni.addDriver(driver_geo.getShape().name())
        except AttributeError:
            pwni.addDrivers(driver_geo.getShape().name())

    pm.rename(d[0], deformer_name)

    # Import weights if path is provided
    if weights_path is not None:
        filename = weights_filename if weights_filename else f"{deformer_name}.json"
        pm.deformerWeights(
            filename,
            im=True,
            method="index",
            deformer=deformer_name,
            path=weights_path,
        )

    cmds.setAttr(f"{deformer_name}.smoothInfluences", smoothInfluences)

    return deformer_name


# =============================================================================
# WIRE DEFORMER FUNCTIONS
# =============================================================================


def createWireDeformer(mesh, curve, dropoffDistance=1.0, name="wire"):
    """Create a wire deformer on a mesh using a curve.

    Args:
        mesh (str): Name of the target mesh.
        curve (str): Name of the driver curve.
        dropoffDistance (float): Dropoff distance for the wire influence.
            Defaults to 1.0.
        name (str): Name for the wire deformer. Defaults to "wire".

    Returns:
        str: Name of created wire deformer, or None if failed.

    Example:
        >>> wire = createWireDeformer("pSphere1", "curve1", dropoffDistance=5.0)
    """
    wire_result = cmds.wire(
        mesh,
        wire=curve,
        name=name,
        groupWithBase=False,
        envelope=1.0,
        crossingEffect=0,
        localInfluence=0,
        dropoffDistance=(0, dropoffDistance),
    )

    wire_deformer = wire_result[0] if wire_result else None

    # Set rotation to 0 to prevent twisting
    if wire_deformer:
        cmds.setAttr(wire_deformer + ".rotation", 0)

    return wire_deformer


def getWireDeformerInfo(wireDeformer):
    """Get wire deformer information.

    Retrieves the wire curve, base curve, and key attributes from a wire
    deformer node.

    Args:
        wireDeformer (str): Name of the wire deformer node.

    Returns:
        dict: Dictionary with wire info, or None if failed.
            Keys:
                - wire_curve (str): The deformed/animated curve
                - base_curve (str): The original undeformed curve
                - dropoff_distance (float): Wire influence falloff distance
                - scale (float): Wire scale multiplier
                - envelope (float): Wire envelope value

    Example:
        >>> info = getWireDeformerInfo("wire1")
        >>> print(info["dropoff_distance"])
        5.0
    """
    if not wireDeformer or not cmds.objExists(wireDeformer):
        cmds.warning("Wire deformer does not exist: {}".format(wireDeformer))
        return None

    wire_curve = None
    base_curve = None

    # Try to get the deformed wire curve
    deformed_connections = cmds.listConnections(
        wireDeformer + ".deformedWire",
        source=True,
        destination=False,
        shapes=True,
    )

    if deformed_connections:
        for conn in deformed_connections:
            if cmds.nodeType(conn) == "nurbsCurve":
                parents = cmds.listRelatives(conn, parent=True, fullPath=True)
                if parents:
                    wire_curve = parents[0]
                else:
                    wire_curve = conn
                break
            elif cmds.nodeType(conn) == "transform":
                wire_curve = conn
                break

    # If still not found, try baseWire
    if not wire_curve:
        base_connections = cmds.listConnections(
            wireDeformer + ".baseWire",
            source=True,
            destination=False,
            shapes=True,
        )
        if base_connections:
            for conn in base_connections:
                if cmds.nodeType(conn) == "nurbsCurve":
                    parents = cmds.listRelatives(conn, parent=True, fullPath=True)
                    if parents:
                        wire_curve = parents[0]
                    else:
                        wire_curve = conn
                    break

    # Try to find base curve
    base_wire_conn = cmds.listConnections(
        wireDeformer + ".baseWire",
        source=True,
        destination=False,
        shapes=True,
    )
    if base_wire_conn:
        for conn in base_wire_conn:
            if cmds.nodeType(conn) == "nurbsCurve":
                parents = cmds.listRelatives(conn, parent=True, fullPath=True)
                if parents:
                    base_curve = parents[0]
                else:
                    base_curve = conn
                break

    # Get dropoff distance
    try:
        dropoff_distance = cmds.getAttr(wireDeformer + ".dropoffDistance[0]")
        if isinstance(dropoff_distance, list):
            dropoff_distance = dropoff_distance[0] if dropoff_distance else 1.0
    except Exception:
        dropoff_distance = 1.0

    # Get scale
    try:
        scale = cmds.getAttr(wireDeformer + ".scale[0]")
        if isinstance(scale, list):
            scale = scale[0] if scale else 1.0
    except Exception:
        scale = 1.0

    # Get envelope
    try:
        envelope = cmds.getAttr(wireDeformer + ".envelope")
    except Exception:
        envelope = 1.0

    return {
        "wire_curve": wire_curve,
        "base_curve": base_curve,
        "dropoff_distance": dropoff_distance,
        "scale": scale,
        "envelope": envelope,
    }


def getWireWeightMap(mesh, wireDeformer):
    """Get the wire deformer's per-vertex weight map.

    Retrieves the weight value for each vertex affected by the wire deformer.
    Weights of 1.0 mean full influence, 0.0 means no influence.

    Args:
        mesh (str): Name of the mesh.
        wireDeformer (str): Name of the wire deformer.

    Returns:
        dict: Dictionary mapping vertex index to weight value (0.0 to 1.0).

    Example:
        >>> weights = getWireWeightMap("pSphere1", "wire1")
        >>> print(weights[0])  # Weight for vertex 0
        1.0
    """
    num_verts = cmds.polyEvaluate(mesh, vertex=True)
    weights = {}

    # Find the geometry index for this mesh
    geometry_index = 0
    try:
        output_geom = cmds.listConnections(
            wireDeformer + ".outputGeometry",
            source=False,
            destination=True,
            plugs=True,
        )
        if output_geom:
            for i, conn in enumerate(output_geom):
                if mesh in conn or mesh.split("|")[-1] in conn:
                    geometry_index = i
                    break
    except Exception:
        pass

    # Try to get weights from the deformer
    for v_idx in range(num_verts):
        try:
            weight_attr = "{}.weightList[{}].weights[{}]".format(
                wireDeformer, geometry_index, v_idx
            )
            if cmds.objExists(weight_attr):
                w = cmds.getAttr(weight_attr)
                weights[v_idx] = w if w is not None else 1.0
            else:
                weights[v_idx] = 1.0
        except Exception:
            weights[v_idx] = 1.0

    return weights


def getMeshWireDeformers(mesh):
    """Get all wire deformers affecting a mesh.

    Searches the mesh's deformation history for wire deformer nodes.

    Args:
        mesh (str): Name of the mesh.

    Returns:
        list: List of wire deformer names, or empty list if none found.

    Example:
        >>> wires = getMeshWireDeformers("pSphere1")
        >>> print(wires)
        ['wire1', 'wire2']
    """
    history = cmds.listHistory(mesh, pruneDagObjects=True) or []
    wires = [h for h in history if cmds.nodeType(h) == "wire"]
    return wires
