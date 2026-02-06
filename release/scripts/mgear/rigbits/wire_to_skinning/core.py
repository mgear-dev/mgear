"""Wire to Skinning - Core logic.

This module contains the core functions for:
- Getting wire deformer and curve information
- Computing skin weights using the de Boor algorithm
- Creating wire deformers from edge loops
- Converting wire deformers to skin clusters
- Exporting/importing wire configurations
"""

# Standard library
import json
import math

# mGear
from mgear.core import deboor
from mgear.core import skin as core_skin

# Maya
from maya import cmds
from maya import mel
import maya.api.OpenMaya as om2
import maya.OpenMaya as om

# Constants
DEFAULT_WEIGHT_THRESHOLD = 0.001
DEFAULT_STATIC_JOINT_NAME = "static_jnt"
CONFIG_FILE_EXT = ".wts"  # Wire To Skinning configuration file extension


# =============================================================================
# CURVE AND WIRE DEFORMER INFO
# =============================================================================


def get_curve_info(curve):
    """Get curve information including CVs, degree, and knots.

    Args:
        curve (str): Name of the curve transform or shape.

    Returns:
        dict: Dictionary with curve information, or None if failed.
            Keys: shape, degree, spans, num_cvs, cvs, knots, min_param, max_param
    """
    if not curve or not cmds.objExists(curve):
        cmds.warning("Curve does not exist: {}".format(curve))
        return None

    curve_shape = None
    node_type = cmds.nodeType(curve)

    if node_type == "nurbsCurve":
        curve_shape = curve
    elif node_type == "transform":
        shapes = cmds.listRelatives(
            curve, shapes=True, type="nurbsCurve", fullPath=True
        )
        if shapes:
            curve_shape = shapes[0]
    else:
        shapes = cmds.listRelatives(curve, shapes=True, fullPath=True)
        if shapes:
            for shape in shapes:
                if cmds.nodeType(shape) == "nurbsCurve":
                    curve_shape = shape
                    break

    if not curve_shape:
        cmds.warning("Could not find nurbsCurve shape for: {}".format(curve))
        return None

    try:
        # Use OpenMaya API for reliable curve info retrieval
        sel_list = om2.MSelectionList()
        sel_list.add(curve_shape)
        dag_path = sel_list.getDagPath(0)
        curve_fn = om2.MFnNurbsCurve(dag_path)

        degree = curve_fn.degree
        num_cvs = curve_fn.numCVs
        spans = curve_fn.numSpans

        # Get CVs
        cvs = []
        cv_positions = curve_fn.cvPositions(om2.MSpace.kWorld)
        for i in range(num_cvs):
            pos = cv_positions[i]
            cvs.append([pos.x, pos.y, pos.z])

        # Get parameter range
        min_param = curve_fn.knotDomain[0]
        max_param = curve_fn.knotDomain[1]

        # Get knots from Maya
        # MFnNurbsCurve.knots() returns n + p - 1 knots
        # Full knot vector should have n + p + 1 knots
        maya_knots = list(curve_fn.knots())
        expected_length = num_cvs + degree + 1

        if len(maya_knots) == num_cvs + degree - 1:
            # Add the missing endpoint knots
            knots = [maya_knots[0]] + maya_knots + [maya_knots[-1]]
        elif len(maya_knots) == expected_length:
            knots = maya_knots
        else:
            # Build uniform knot vector as fallback
            print(
                "Building uniform knot vector. Maya returned {} knots, "
                "expected {}".format(len(maya_knots), expected_length)
            )
            knots = []
            for i in range(expected_length):
                if i <= degree:
                    knots.append(min_param)
                elif i >= num_cvs:
                    knots.append(max_param)
                else:
                    t = (i - degree) / float(spans)
                    knots.append(min_param + t * (max_param - min_param))

        return {
            "shape": curve_shape,
            "degree": degree,
            "spans": spans,
            "num_cvs": num_cvs,
            "cvs": cvs,
            "knots": knots,
            "min_param": min_param,
            "max_param": max_param,
        }
    except Exception as e:
        cmds.warning(
            "Error getting curve info for {}: {}".format(curve_shape, str(e))
        )
        return None


def get_wire_deformer_info(wire_deformer):
    """Get wire deformer information.

    Args:
        wire_deformer (str): Name of the wire deformer node.

    Returns:
        dict: Dictionary with wire info, or None if failed.
            Keys: wire_curve, base_curve, dropoff_distance, scale, envelope
    """
    if not wire_deformer or not cmds.objExists(wire_deformer):
        cmds.warning("Wire deformer does not exist: {}".format(wire_deformer))
        return None

    wire_curve = None
    base_curve = None

    # Try to get the deformed wire curve
    deformed_connections = cmds.listConnections(
        wire_deformer + ".deformedWire",
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
            wire_deformer + ".baseWire",
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
        wire_deformer + ".baseWire",
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
        dropoff_distance = cmds.getAttr(wire_deformer + ".dropoffDistance[0]")
        if isinstance(dropoff_distance, list):
            dropoff_distance = dropoff_distance[0] if dropoff_distance else 1.0
    except Exception:
        dropoff_distance = 1.0

    # Get scale
    try:
        scale = cmds.getAttr(wire_deformer + ".scale[0]")
        if isinstance(scale, list):
            scale = scale[0] if scale else 1.0
    except Exception:
        scale = 1.0

    # Get envelope
    try:
        envelope = cmds.getAttr(wire_deformer + ".envelope")
    except Exception:
        envelope = 1.0

    return {
        "wire_curve": wire_curve,
        "base_curve": base_curve,
        "dropoff_distance": dropoff_distance,
        "scale": scale,
        "envelope": envelope,
    }


def get_wire_weight_map(wire_deformer, mesh):
    """Get the wire deformer's weight map for each vertex.

    Args:
        wire_deformer (str): Name of the wire deformer.
        mesh (str): Name of the mesh.

    Returns:
        dict: Dictionary mapping vertex index to weight value (0.0 to 1.0).
    """
    num_verts = cmds.polyEvaluate(mesh, vertex=True)
    weights = {}

    # Find the geometry index for this mesh
    geometry_index = 0
    try:
        output_geom = cmds.listConnections(
            wire_deformer + ".outputGeometry",
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
                wire_deformer, geometry_index, v_idx
            )
            if cmds.objExists(weight_attr):
                w = cmds.getAttr(weight_attr)
                weights[v_idx] = w if w is not None else 1.0
            else:
                weights[v_idx] = 1.0
        except Exception:
            weights[v_idx] = 1.0

    return weights


def get_mesh_wire_deformers(mesh):
    """Get all wire deformers affecting a mesh.

    Args:
        mesh (str): Name of the mesh.

    Returns:
        list: List of wire deformer names.
    """
    history = cmds.listHistory(mesh, pruneDagObjects=True) or []
    wires = [h for h in history if cmds.nodeType(h) == "wire"]
    return wires


def get_mesh_skin_cluster(mesh):
    """Get the skin cluster affecting a mesh.

    Uses mgear.core.skin.getSkinCluster for robust skin cluster detection.

    Args:
        mesh (str): Name of the mesh.

    Returns:
        str: Name of the skin cluster, or None if not found.
    """
    skin_cls = core_skin.getSkinCluster(mesh)
    if skin_cls:
        return skin_cls.name()
    return None


def get_existing_skin_weights(mesh, skin_cluster):
    """Get existing skin weights from a skin cluster.

    Uses OpenMaya API for efficient batch weight retrieval (much faster than
    per-vertex cmds.skinPercent calls). Leverages mgear.core.skin utilities.

    Args:
        mesh (str): Name of the mesh.
        skin_cluster (str): Name of the skin cluster.

    Returns:
        dict: Dictionary mapping vertex index to joint weights.
            Format: {vertex_idx: {joint_name: weight, ...}, ...}
    """
    if not skin_cluster or not cmds.objExists(skin_cluster):
        return {}

    # Get PyNode for skin cluster
    import mgear.pymaya as pm

    skin_cls = pm.PyNode(skin_cluster)

    print("Reading existing skin weights using OpenMaya API...")

    # Get geometry components using core.skin utilities
    dag_path, components = core_skin.getGeometryComponents(skin_cls)

    # Get all weights in one batch call (fast!)
    weights_array = core_skin.getCurrentWeights(skin_cls, dag_path, components)

    # Get influence names
    influence_paths = om.MDagPathArray()
    skin_fn = core_skin.get_skin_cluster_fn(skin_cluster)
    num_influences = skin_fn.influenceObjects(influence_paths)

    influence_names = [
        om.MFnDependencyNode(influence_paths[i].node()).name()
        for i in range(influence_paths.length())
    ]

    # Calculate number of vertices
    num_verts = int(weights_array.length() / num_influences)

    # Convert flat weight array to per-vertex dictionary
    weights = {}
    for v_idx in range(num_verts):
        vert_weights = {}
        for inf_idx, inf_name in enumerate(influence_names):
            w = weights_array[v_idx * num_influences + inf_idx]
            if w > 0.0001:
                vert_weights[inf_name] = w

        if vert_weights:
            weights[v_idx] = vert_weights

    print("Read weights for {} vertices with non-zero influence.".format(len(weights)))
    return weights


# =============================================================================
# STATIC JOINT
# =============================================================================


def ensure_static_joint_exists(name=DEFAULT_STATIC_JOINT_NAME):
    """Ensure the static joint exists, create if it doesn't.

    Args:
        name (str): Name for the static joint.

    Returns:
        str: Name of the static joint.
    """
    if not cmds.objExists(name):
        cmds.select(clear=True)
        cmds.joint(name=name, position=[0, 0, 0])
        cmds.select(clear=True)
        print("Created static joint: {}".format(name))

    return name


# =============================================================================
# WEIGHT COMPUTATION
# =============================================================================


def compute_skin_weights_deboor(
    mesh,
    curve_info,
    wire_info,
    wire_deformer=None,
    weight_threshold=DEFAULT_WEIGHT_THRESHOLD,
    static_joint_name=DEFAULT_STATIC_JOINT_NAME,
    existing_weights=None,
):
    """Compute skin weights using de Boor algorithm to match wire deformer.

    Optimized to only process vertices that have wire deformer influence.
    Uses wire weight map to blend between wire joints and existing weights
    (if available) or static joint.

    Args:
        mesh (str): Name of the mesh.
        curve_info (dict): Dictionary with curve information.
        wire_info (dict): Dictionary with wire deformer information.
        wire_deformer (str): Name of the wire deformer (for weight map).
        weight_threshold (float): Minimum wire weight to process vertex.
        static_joint_name (str): Name of the static joint.
        existing_weights (dict): Optional existing skin weights per vertex.
            Format: {vertex_idx: {joint_name: weight, ...}, ...}
            When provided, non-wire-affected weight blends with existing
            instead of going to static joint.

    Returns:
        tuple: (weights_dict, uses_static_joint)
    """
    mesh_shape = mesh
    if cmds.nodeType(mesh) == "transform":
        shapes = cmds.listRelatives(mesh, shapes=True, type="mesh")
        if shapes:
            mesh_shape = shapes[0]

    num_verts = cmds.polyEvaluate(mesh, vertex=True)

    degree = curve_info["degree"]
    num_cvs = curve_info["num_cvs"]
    knots = curve_info["knots"]
    dropoff = wire_info["dropoff_distance"]

    curve_shape = curve_info["shape"]

    # Get wire weight map if wire deformer is provided
    wire_weights = {}
    if wire_deformer:
        print("Getting wire weight map...")
        wire_weights = get_wire_weight_map(wire_deformer, mesh)

    # Count affected vertices
    affected_verts = (
        [v for v, w in wire_weights.items() if w > weight_threshold]
        if wire_weights
        else list(range(num_verts))
    )
    total_affected = len(affected_verts)
    print(
        "Processing {} affected vertices out of {} total".format(
            total_affected, num_verts
        )
    )

    # Use OpenMaya for faster closest point calculations
    try:
        sel_list = om2.MSelectionList()
        sel_list.add(curve_shape)
        dag_path = sel_list.getDagPath(0)
        curve_fn = om2.MFnNurbsCurve(dag_path)
    except Exception as e:
        cmds.warning("Could not create MFnNurbsCurve: {}".format(str(e)))
        return {}, False

    weights = {}
    uses_static_joint = False

    # Process only affected vertices
    for progress_idx, v_idx in enumerate(affected_verts):
        # Progress update every 500 vertices
        if progress_idx % 500 == 0 and progress_idx > 0:
            print(
                "  Processed {}/{} vertices...".format(progress_idx, total_affected)
            )

        # Get wire weight for this vertex
        wire_weight = wire_weights.get(v_idx, 1.0) if wire_weights else 1.0

        # Skip vertices with no wire influence
        if wire_weight < weight_threshold:
            continue

        vert_pos = cmds.pointPosition(
            "{}.vtx[{}]".format(mesh, v_idx), world=True
        )
        point = om2.MPoint(vert_pos[0], vert_pos[1], vert_pos[2])

        # Get closest point on curve using OpenMaya
        try:
            closest_point = curve_fn.closestPoint(point, space=om2.MSpace.kWorld)
            if isinstance(closest_point, tuple):
                closest_pt = closest_point[0]
                u = closest_point[1]
            else:
                closest_pt = closest_point
                u = curve_fn.getParamAtPoint(closest_pt, space=om2.MSpace.kWorld)
        except Exception:
            # Use existing weights if available, otherwise static joint
            if existing_weights and v_idx in existing_weights:
                weights[v_idx] = existing_weights[v_idx].copy()
            else:
                weights[v_idx] = {"static": 1.0}
                uses_static_joint = True
            continue

        # Calculate distance
        distance = math.sqrt(
            (vert_pos[0] - closest_pt.x) ** 2
            + (vert_pos[1] - closest_pt.y) ** 2
            + (vert_pos[2] - closest_pt.z) ** 2
        )

        if dropoff > 0:
            distance_falloff = max(0.0, 1.0 - (distance / dropoff))
        else:
            distance_falloff = 1.0 if distance < 0.001 else 0.0

        # Combine wire weight with distance falloff
        combined_falloff = wire_weight * distance_falloff

        if combined_falloff < weight_threshold:
            # Use existing weights if available, otherwise static joint
            if existing_weights and v_idx in existing_weights:
                weights[v_idx] = existing_weights[v_idx].copy()
            else:
                weights[v_idx] = {"static": 1.0}
                uses_static_joint = True
            continue

        # Clamp u to valid range
        u = max(curve_info["min_param"], min(curve_info["max_param"], u))

        n = num_cvs - 1
        span = deboor.find_knot_span(n, degree, u, knots)
        basis = deboor.basis_functions(span, u, degree, knots)

        joint_weights = {}
        total = 0.0

        for i in range(degree + 1):
            cv_idx = span - degree + i
            if 0 <= cv_idx < num_cvs:
                w = basis[i] * combined_falloff
                if w > 0.0001:
                    joint_weights[cv_idx] = w
                    total += w

        # Add remaining influence to existing weights or static joint
        remaining_weight = 1.0 - combined_falloff
        if remaining_weight > 0.0001:
            if existing_weights and v_idx in existing_weights:
                # Distribute remaining weight to existing influences
                existing = existing_weights[v_idx]
                existing_total = sum(existing.values())
                if existing_total > 0:
                    for jnt_name, w in existing.items():
                        # Scale existing weight proportionally
                        scaled_w = (w / existing_total) * remaining_weight
                        if scaled_w > 0.0001:
                            joint_weights[jnt_name] = (
                                joint_weights.get(jnt_name, 0) + scaled_w
                            )
                            total += scaled_w
                else:
                    joint_weights["static"] = remaining_weight
                    uses_static_joint = True
                    total += remaining_weight
            else:
                # No existing weights, use static joint
                joint_weights["static"] = remaining_weight
                uses_static_joint = True
                total += remaining_weight

        # Normalize
        if total > 0:
            for key in joint_weights:
                joint_weights[key] /= total
        else:
            if existing_weights and v_idx in existing_weights:
                joint_weights = existing_weights[v_idx].copy()
            else:
                joint_weights["static"] = 1.0
                uses_static_joint = True

        weights[v_idx] = joint_weights

    print(
        "Weight computation complete. {} vertices with wire influence. "
        "Uses static joint: {}".format(len(weights), uses_static_joint)
    )
    return weights, uses_static_joint


# =============================================================================
# WIRE CREATION FUNCTIONS
# =============================================================================


def get_edges_positions(edges):
    """Get ordered positions from edge selection.

    Args:
        edges (list): List of edge names.

    Returns:
        list: Ordered list of vertex positions.
    """
    if not edges:
        return []

    # Convert edge selection to vertices
    verts = cmds.polyListComponentConversion(edges, toVertex=True)
    verts = cmds.filterExpand(verts, selectionMask=31)

    if not verts:
        return []

    # Get mesh name
    mesh = edges[0].split(".")[0]

    # Build edge connectivity
    edge_to_verts = {}
    vert_to_edges = {}

    edge_list = cmds.filterExpand(edges, selectionMask=32)

    for edge in edge_list:
        edge_verts = cmds.polyListComponentConversion(edge, toVertex=True)
        edge_verts = cmds.filterExpand(edge_verts, selectionMask=31)

        if len(edge_verts) == 2:
            v1_idx = int(edge_verts[0].split("[")[1].split("]")[0])
            v2_idx = int(edge_verts[1].split("[")[1].split("]")[0])
            edge_idx = int(edge.split("[")[1].split("]")[0])

            edge_to_verts[edge_idx] = (v1_idx, v2_idx)

            if v1_idx not in vert_to_edges:
                vert_to_edges[v1_idx] = []
            vert_to_edges[v1_idx].append(edge_idx)

            if v2_idx not in vert_to_edges:
                vert_to_edges[v2_idx] = []
            vert_to_edges[v2_idx].append(edge_idx)

    # Find endpoints (vertices with only one edge connection)
    endpoints = [v for v, e_list in vert_to_edges.items() if len(e_list) == 1]

    if not endpoints:
        # Closed loop - start from first vertex
        start_vert = list(vert_to_edges.keys())[0]
    else:
        start_vert = endpoints[0]

    # Order vertices along the edge loop
    ordered_verts = [start_vert]
    visited_edges = set()
    current_vert = start_vert

    while True:
        found_next = False
        for edge_idx in vert_to_edges.get(current_vert, []):
            if edge_idx in visited_edges:
                continue

            v1, v2 = edge_to_verts[edge_idx]
            next_vert = v2 if v1 == current_vert else v1

            visited_edges.add(edge_idx)
            ordered_verts.append(next_vert)
            current_vert = next_vert
            found_next = True
            break

        if not found_next:
            break

    # Get world positions
    positions = []
    for v_idx in ordered_verts:
        pos = cmds.pointPosition("{}.vtx[{}]".format(mesh, v_idx), world=True)
        positions.append(pos)

    return positions


def create_curve_from_positions(positions, num_cvs, name="wire_curve"):
    """Create a NURBS curve from positions with specified number of CVs.

    Args:
        positions (list): List of 3D positions.
        num_cvs (int): Target number of control vertices.
        name (str): Name for the curve.

    Returns:
        str: Name of created curve, or None if failed.
    """
    if len(positions) < 2:
        cmds.warning("Not enough positions to create curve")
        return None

    # Create initial curve through points
    curve = cmds.curve(point=positions, degree=3, name=name)

    # Rebuild curve with specified number of CVs
    # Number of spans = num_cvs - degree (for degree 3)
    target_spans = max(1, num_cvs - 3)

    cmds.rebuildCurve(
        curve,
        constructionHistory=False,
        replaceOriginal=True,
        rebuildType=0,
        endKnots=1,
        keepRange=0,
        keepControlPoints=False,
        keepEndPoints=True,
        keepTangents=False,
        spans=target_spans,
        degree=3,
    )

    return curve


def create_wire_deformer(mesh, curve, dropoff_distance=1.0, name="wire"):
    """Create a wire deformer on mesh using curve.

    Args:
        mesh (str): Name of the mesh.
        curve (str): Name of the curve.
        dropoff_distance (float): Dropoff distance for the wire.
        name (str): Name for the wire deformer.

    Returns:
        str: Name of created wire deformer, or None if failed.
    """
    wire_result = cmds.wire(
        mesh,
        wire=curve,
        name=name,
        groupWithBase=False,
        envelope=1.0,
        crossingEffect=0,
        localInfluence=0,
        dropoffDistance=(0, dropoff_distance),
    )

    wire_deformer = wire_result[0] if wire_result else None

    # Set rotation to 0 to prevent twisting
    if wire_deformer:
        cmds.setAttr(wire_deformer + ".rotation", 0)

    return wire_deformer


# =============================================================================
# WIRE FROM JOINTS FUNCTIONS
# =============================================================================


def get_curve_connected_joints(curve):
    """Get joints connected to curve via mgear_curveCns deformer.

    Args:
        curve (str): Name of the curve.

    Returns:
        list: Joint names in CV order, or empty list if not connected.
    """
    # Get curve shape if transform was passed (use fullPath to avoid name clashes)
    if cmds.objectType(curve) == "transform":
        shapes = cmds.listRelatives(
            curve, shapes=True, type="nurbsCurve", fullPath=True
        )
        if shapes:
            curve_shape = shapes[0]
        else:
            return []
    else:
        curve_shape = curve

    # Find curveCns deformer in history
    history = cmds.listHistory(curve_shape)
    if not history:
        return []

    curvecns_nodes = [
        h for h in history if cmds.nodeType(h) == "mgear_curveCns"
    ]
    if not curvecns_nodes:
        return []

    curvecns = curvecns_nodes[0]
    joints = []

    # Get connections to inputs array
    i = 0
    while True:
        attr = "{}.inputs[{}]".format(curvecns, i)
        try:
            conn = cmds.listConnections(attr, source=True, destination=False)
        except Exception:
            break

        if not conn:
            break
        joints.append(conn[0])
        i += 1

    return joints


def create_curve_from_joints(joints, name="wire_curve"):
    """Create a NURBS curve where each CV is at a joint position.

    The curve is NOT rebuilt - CVs match joints 1:1 for curvecns connection.

    Args:
        joints (list): List of joint names in order.
        name (str): Name for the curve.

    Returns:
        str: Name of created curve, or None if failed.
    """
    if len(joints) < 2:
        cmds.warning("Need at least 2 joints to create curve")
        return None

    # Get world positions of joints
    positions = []
    for jnt in joints:
        if not cmds.objExists(jnt):
            cmds.warning("Joint not found: {}".format(jnt))
            return None
        pos = cmds.xform(jnt, query=True, worldSpace=True, translation=True)
        positions.append(pos)

    # Determine curve degree based on joint count
    num_joints = len(joints)
    if num_joints == 2:
        degree = 1  # Linear
    elif num_joints == 3:
        degree = 2  # Quadratic
    else:
        degree = 3  # Cubic

    # Create curve through joint positions
    curve = cmds.curve(point=positions, degree=degree, name=name)

    return curve


def connect_curve_to_joints(curve, joints):
    """Connect curve CVs to joints using mgear_curveCns deformer.

    Args:
        curve (str): Name of the NURBS curve.
        joints (list): List of joint names matching CV count and order.

    Returns:
        str: Name of the curveCns deformer node, or None if failed.
    """
    # Ensure mgear_solvers plugin is loaded
    if not cmds.pluginInfo("mgear_solvers", query=True, loaded=True):
        try:
            cmds.loadPlugin("mgear_solvers")
        except Exception:
            cmds.warning("Failed to load mgear_solvers plugin")
            return None

    # Create curveCns deformer
    cmds.select(curve)
    deformer_result = cmds.deformer(type="mgear_curveCns")
    if not deformer_result:
        cmds.warning("Failed to create mgear_curveCns deformer")
        return None

    curvecns = deformer_result[0]

    # Connect each joint's worldMatrix to the deformer's inputs
    for i, jnt in enumerate(joints):
        cmds.connectAttr(
            "{}.worldMatrix".format(jnt),
            "{}.inputs[{}]".format(curvecns, i),
        )

    cmds.select(clear=True)
    return curvecns


def create_wire_from_joints(mesh, joints, dropoff_distance=1.0, name="wire"):
    """Create a wire deformer from joints with curve connected via curveCns.

    This creates a curve where each CV matches a joint position, connects
    the CVs to the joints so the curve follows joint movement, then creates
    a wire deformer on the mesh using this curve.

    Args:
        mesh (str): Name of the mesh to deform.
        joints (list): List of joint names in order.
        dropoff_distance (float): Dropoff distance for the wire.
        name (str): Base name for the wire deformer and curve.

    Returns:
        tuple: (wire_deformer, curve, curvecns_node) or (None, None, None).
    """
    # Validate mesh
    if not mesh or not cmds.objExists(mesh):
        cmds.warning("Mesh not found: {}".format(mesh))
        return None, None, None

    # Validate joints
    if len(joints) < 2:
        cmds.warning("Need at least 2 joints to create wire")
        return None, None, None

    for jnt in joints:
        if not cmds.objExists(jnt):
            cmds.warning("Joint not found: {}".format(jnt))
            return None, None, None

    # Create curve from joints
    curve_name = name + "_curve"
    curve = create_curve_from_joints(joints, curve_name)
    if not curve:
        return None, None, None

    # Connect curve to joints
    curvecns = connect_curve_to_joints(curve, joints)
    if not curvecns:
        cmds.delete(curve)
        return None, None, None

    # Create wire deformer
    wire = create_wire_deformer(mesh, curve, dropoff_distance, name)
    if not wire:
        cmds.delete(curve)
        return None, None, None

    return wire, curve, curvecns


def get_ordered_joints(joints, order_by="selection"):
    """Get joints in specified order.

    Args:
        joints (list): List of joint names.
        order_by (str): Ordering method:
            - "selection": Return as-is (selection order)
            - "hierarchy": Order by parent-child hierarchy
            - "position_x": Sort by world X position

    Returns:
        list: Ordered joint names.
    """
    if not joints:
        return []

    if order_by == "selection":
        return joints[:]

    elif order_by == "hierarchy":
        # Build parent-child relationships
        joint_set = set(joints)
        ordered = []
        remaining = joints[:]

        # Find joints with no parent in the list (roots)
        roots = []
        for jnt in joints:
            parent = cmds.listRelatives(jnt, parent=True)
            if not parent or parent[0] not in joint_set:
                roots.append(jnt)

        # Traverse from roots
        def add_children(jnt):
            if jnt in remaining:
                ordered.append(jnt)
                remaining.remove(jnt)
            children = cmds.listRelatives(jnt, children=True, type="joint")
            if children:
                for child in children:
                    if child in joint_set:
                        add_children(child)

        for root in roots:
            add_children(root)

        # Add any remaining joints (disconnected chains)
        ordered.extend(remaining)
        return ordered

    elif order_by == "position_x":
        # Sort by world X position
        joint_positions = []
        for jnt in joints:
            pos = cmds.xform(jnt, query=True, worldSpace=True, translation=True)
            joint_positions.append((jnt, pos[0]))

        sorted_joints = sorted(joint_positions, key=lambda x: x[1])
        return [jnt for jnt, _ in sorted_joints]

    return joints[:]


# =============================================================================
# SKIN CLUSTER FUNCTIONS
# =============================================================================


def create_joints_at_cvs(curve_info, prefix="wire", parent=None):
    """Create joints at each CV of the curve.

    Args:
        curve_info (dict): Dictionary with curve information.
        prefix (str): Prefix for joint names.
        parent (str): Optional parent joint.

    Returns:
        list: List of created joint names.

    Note:
        Joint naming convention: {prefix}_{index}_jnt
        Example: lip_up_0_jnt, lip_up_1_jnt, etc.
    """
    joints = []
    cmds.select(clear=True)

    for i, cv_pos in enumerate(curve_info["cvs"]):
        jnt_name = "{}_{}_jnt".format(prefix, i)

        # Handle if joint already exists
        if cmds.objExists(jnt_name):
            jnt_name = "{}_{}_jnt#".format(prefix, i)

        jnt = cmds.joint(name=jnt_name, position=cv_pos)
        joints.append(jnt)
        cmds.select(clear=True)

    # Parent to specified parent if provided
    if parent and cmds.objExists(parent):
        for jnt in joints:
            try:
                cmds.parent(jnt, parent)
            except Exception:
                pass

    return joints


def create_skin_cluster(
    mesh,
    joints,
    weights,
    name=None,
    static_joint=None,
    uses_static_joint=False,
):
    """Create a skin cluster and apply the computed weights using OpenMaya.

    Preserves existing skin weights for vertices not affected by the wire.
    Uses OpenMaya batch operations for significantly faster weight application.

    Args:
        mesh (str): Name of the mesh.
        joints (list): List of joint names (for wire CVs).
        weights (dict): Weight dictionary {vertex_idx: {joint_idx or 'static': weight}}
        name (str): Name for the skin cluster (defaults to mesh_skinCluster).
        static_joint (str): Name of the static joint.
        uses_static_joint (bool): Whether the weights include static joint.

    Returns:
        str: Name of the created skin cluster.
    """
    # Default skin cluster name based on mesh
    if not name:
        mesh_short_name = mesh.split("|")[-1].split(":")[-1]
        name = "{}_skinCluster".format(mesh_short_name)

    # Build complete joint list
    all_joints = list(joints)

    # Create and add static joint if needed
    if uses_static_joint:
        static_joint = ensure_static_joint_exists(
            static_joint or DEFAULT_STATIC_JOINT_NAME
        )
        if static_joint not in all_joints:
            all_joints.append(static_joint)

    # Verify all joints exist
    missing_joints = [jnt for jnt in all_joints if not cmds.objExists(jnt)]
    if missing_joints:
        cmds.warning("Joints do not exist: {}".format(missing_joints))
        return None

    # Check if mesh already has a skin cluster
    existing_skin = None
    try:
        existing_skin = mel.eval('findRelatedSkinCluster("{}")'.format(mesh))
    except Exception:
        pass

    if existing_skin:
        print(
            "Found existing skin cluster: {}. Adding new influences...".format(
                existing_skin
            )
        )
        skin_cluster = existing_skin

        # Get existing influences
        existing_influences = (
            cmds.skinCluster(skin_cluster, query=True, influence=True) or []
        )

        # Add new joints to existing skin cluster
        for jnt in all_joints:
            if jnt not in existing_influences:
                try:
                    cmds.skinCluster(
                        skin_cluster,
                        edit=True,
                        addInfluence=jnt,
                        weight=0,
                        lockWeights=False,
                    )
                    print("  Added influence: {}".format(jnt))
                except Exception as e:
                    cmds.warning(
                        "Could not add influence {}: {}".format(jnt, str(e))
                    )
    else:
        # Create new skin cluster
        print("Creating new skin cluster: {}".format(name))
        try:
            skin_cluster = cmds.skinCluster(
                *all_joints,
                mesh,
                name=name,
                toSelectedBones=True,
                bindMethod=0,
                skinMethod=0,
                normalizeWeights=1,
                maximumInfluences=len(all_joints)
            )[0]
        except Exception as e:
            cmds.warning("Failed to create skin cluster: {}".format(str(e)))
            return None

    # Unlock all joints we're working with
    for jnt in all_joints:
        try:
            cmds.setAttr("{}.liw".format(jnt), False)
        except Exception:
            pass

    # Filter out vertices that only have static weight = 1.0
    affected_weights = {
        v_idx: w
        for v_idx, w in weights.items()
        if not (len(w) == 1 and w.get("static", 0) == 1.0)
    }

    print(
        "Applying wire weights to {} affected vertices...".format(
            len(affected_weights)
        )
    )

    # Build CV index to joint name mapping
    cv_to_joint = {idx: jnt for idx, jnt in enumerate(joints)}

    # For new skin cluster, initialize all vertices to static joint
    if not existing_skin and static_joint and uses_static_joint:
        print("Initializing all vertices to static joint...")
        core_skin.initializeToInfluence(skin_cluster, static_joint)

    # Convert weights format: {v_idx: {key: w}} -> {v_idx: {joint_name: w}}
    vertex_weights = {}
    for v_idx, vert_weights in affected_weights.items():
        vertex_weights[v_idx] = {}
        for key, w in vert_weights.items():
            # Determine joint name from key
            if key == "static":
                jnt_name = static_joint
            elif isinstance(key, int):
                jnt_name = cv_to_joint.get(key)
            else:
                jnt_name = key

            if jnt_name:
                vertex_weights[v_idx][jnt_name] = w

    # Apply weights using core_skin partial update function
    # Uses setVertexWeights which only modifies affected vertices,
    # preserving existing weights on all other vertices.
    # This is more efficient than setInfluenceWeights for partial updates.
    print("Applying weights with core_skin.setVertexWeights...")
    core_skin.setVertexWeights(skin_cluster, vertex_weights)

    print(
        "Skin weights applied successfully to {} vertices.".format(
            len(affected_weights)
        )
    )
    return skin_cluster


# =============================================================================
# CONFIGURATION EXPORT/IMPORT
# =============================================================================


def export_configuration(mesh, filepath, conversion_settings=None):
    """Export wire deformer configuration to file.

    Exports wire deformer settings to a .wts (Wire To Skinning) file,
    which uses JSON format internally.

    Args:
        mesh (str): Name of the mesh.
        filepath (str): Path to save the configuration file (.wts).
        conversion_settings (dict, optional): Settings for conversion to skin.
            Keys:
                - convert_all (bool): Convert all wire deformers.
                - selected_wire (str): Currently selected wire in dropdown.
                - use_auto_joints (bool): Create joints automatically at CVs.
                - joint_prefix (str): Prefix for auto-created joints.
                - parent_joint (str): Parent joint name for auto-created joints.
                - custom_joints (list): List of custom joint names.
                - delete_wire (bool): Delete wire after conversion.

    Returns:
        bool: True if successful, False otherwise.
    """
    wires = get_mesh_wire_deformers(mesh)

    if not wires:
        cmds.warning("No wire deformers found on {}".format(mesh))
        return False

    config = {"mesh": mesh, "wires": []}

    # Store conversion settings if provided
    if conversion_settings:
        config["conversion_settings"] = conversion_settings

    for wire in wires:
        wire_info = get_wire_deformer_info(wire)

        if wire_info["wire_curve"]:
            curve_info = get_curve_info(wire_info["wire_curve"])

            wire_config = {
                "name": wire,
                "curve_name": wire_info["wire_curve"],
                "dropoff_distance": wire_info["dropoff_distance"],
                "scale": wire_info["scale"],
                "envelope": wire_info["envelope"],
                "curve": {
                    "degree": curve_info["degree"],
                    "cvs": curve_info["cvs"],
                    "knots": curve_info["knots"],
                },
            }

            # Check if curve has connected joints (from joint mode)
            connected_joints = get_curve_connected_joints(wire_info["wire_curve"])
            if connected_joints:
                wire_config["connected_joints"] = connected_joints

            config["wires"].append(wire_config)

    with open(filepath, "w") as f:
        json.dump(config, f, indent=2)

    return True


def import_configuration(filepath, target_mesh=None):
    """Import wire deformer configuration from file.

    Imports wire deformer settings from a .wts (Wire To Skinning) file.

    Args:
        filepath (str): Path to the configuration file (.wts).
        target_mesh (str): Optional target mesh (uses stored mesh if not provided).

    Returns:
        dict: Result dictionary with keys:
            - wires (list): List of created wire deformers.
            - mesh (str): The mesh name used.
            - conversion_settings (dict): Stored conversion settings, or None.
        Returns False if import failed.
    """
    with open(filepath, "r") as f:
        config = json.load(f)

    mesh = target_mesh or config.get("mesh")

    if not mesh or not cmds.objExists(mesh):
        cmds.warning("Mesh not found: {}".format(mesh))
        return False

    created_wires = []

    for wire_config in config.get("wires", []):
        curve_data = wire_config.get("curve", {})
        cvs = curve_data.get("cvs", [])
        degree = curve_data.get("degree", 3)
        connected_joints = wire_config.get("connected_joints", [])

        if not cvs:
            continue

        wire_name = wire_config.get("name", "imported_wire")
        dropoff = wire_config.get("dropoff_distance", 1.0)
        wire = None
        curve = None

        # Check if we should recreate from joints
        if connected_joints:
            # Verify all joints exist
            joints_exist = all(cmds.objExists(j) for j in connected_joints)

            if joints_exist:
                # Recreate wire from joints (preserves joint connection)
                result = create_wire_from_joints(
                    mesh, connected_joints, dropoff, wire_name
                )
                if result:
                    wire, curve, _curvecns = result
                    print(
                        "Imported wire '{}' connected to joints: {}".format(
                            wire_name, connected_joints
                        )
                    )
            else:
                missing = [j for j in connected_joints if not cmds.objExists(j)]
                cmds.warning(
                    "Some connected joints not found: {}. "
                    "Creating static curve instead.".format(missing)
                )

        # Fallback: create static curve from CV positions
        if not wire:
            curve_name = wire_config.get("curve_name", "imported_wire_curve")
            curve = cmds.curve(point=cvs, degree=degree, name=curve_name)
            wire = create_wire_deformer(mesh, curve, dropoff, wire_name)

        if wire:
            # Set additional attributes
            if "scale" in wire_config:
                cmds.setAttr(wire + ".scale[0]", wire_config["scale"])
            if "envelope" in wire_config:
                cmds.setAttr(wire + ".envelope", wire_config["envelope"])

            created_wires.append(wire)

    return {
        "wires": created_wires,
        "mesh": mesh,
        "conversion_settings": config.get("conversion_settings"),
    }
