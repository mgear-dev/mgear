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
