"""Wire to Skinning - Core business logic.

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

# Maya
from maya import cmds
from maya import mel
import maya.api.OpenMaya as om2

# Constants
DEFAULT_WEIGHT_THRESHOLD = 0.001
DEFAULT_STATIC_JOINT_NAME = "static_jnt"


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
):
    """Compute skin weights using de Boor algorithm to match wire deformer.

    Optimized to only process vertices that have wire deformer influence.
    Uses wire weight map to blend between wire joints and static joint.

    Args:
        mesh (str): Name of the mesh.
        curve_info (dict): Dictionary with curve information.
        wire_info (dict): Dictionary with wire deformer information.
        wire_deformer (str): Name of the wire deformer (for weight map).
        weight_threshold (float): Minimum wire weight to process vertex.
        static_joint_name (str): Name of the static joint.

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
            # Assign to static joint if curve lookup fails
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
            # Assign to static joint
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

        # Add static joint weight for the remaining influence
        static_weight = 1.0 - combined_falloff
        if static_weight > 0.0001:
            joint_weights["static"] = static_weight
            uses_static_joint = True
            total += static_weight

        # Normalize
        if total > 0:
            for key in joint_weights:
                joint_weights[key] /= total
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
    """Create a skin cluster and apply the computed weights.

    Preserves existing skin weights for vertices not affected by the wire.

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

        # For a NEW skin cluster, initialize ALL vertices to static_jnt
        if static_joint and uses_static_joint:
            print("Initializing all vertices to static joint...")
            num_verts = cmds.polyEvaluate(mesh, vertex=True)

            cmds.skinPercent(
                skin_cluster,
                "{}.vtx[0:{}]".format(mesh, num_verts - 1),
                transformValue=[(static_joint, 1.0)],
                normalize=True,
            )

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

    processed = 0

    for v_idx, vert_weights in affected_weights.items():
        weight_list = []

        for key, w in vert_weights.items():
            if key == "static":
                if static_joint:
                    weight_list.append((static_joint, w))
            elif isinstance(key, int) and 0 <= key < len(joints):
                weight_list.append((joints[key], w))

        if weight_list:
            try:
                cmds.skinPercent(
                    skin_cluster,
                    "{}.vtx[{}]".format(mesh, v_idx),
                    transformValue=weight_list,
                    normalize=True,
                )
            except Exception as e:
                cmds.warning(
                    "Failed to set weights for vertex {}: {}".format(v_idx, str(e))
                )

        processed += 1
        if processed % 500 == 0:
            print(
                "  Applied weights to {}/{} vertices...".format(
                    processed, len(affected_weights)
                )
            )

    print("Skin weights applied successfully to {} vertices.".format(processed))
    return skin_cluster


# =============================================================================
# CONFIGURATION EXPORT/IMPORT
# =============================================================================


def export_configuration(mesh, filepath):
    """Export wire deformer configuration to JSON file.

    Args:
        mesh (str): Name of the mesh.
        filepath (str): Path to save the JSON file.

    Returns:
        bool: True if successful, False otherwise.
    """
    wires = get_mesh_wire_deformers(mesh)

    if not wires:
        cmds.warning("No wire deformers found on {}".format(mesh))
        return False

    config = {"mesh": mesh, "wires": []}

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
            config["wires"].append(wire_config)

    with open(filepath, "w") as f:
        json.dump(config, f, indent=2)

    return True


def import_configuration(filepath, target_mesh=None):
    """Import wire deformer configuration from JSON file.

    Args:
        filepath (str): Path to the JSON file.
        target_mesh (str): Optional target mesh (uses stored mesh if not provided).

    Returns:
        list: List of created wire deformers, or False if failed.
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

        if not cvs:
            continue

        # Create curve from CVs
        curve_name = wire_config.get("curve_name", "imported_wire_curve")
        curve = cmds.curve(point=cvs, degree=degree, name=curve_name)

        # Create wire deformer
        wire_name = wire_config.get("name", "imported_wire")
        dropoff = wire_config.get("dropoff_distance", 1.0)

        wire = create_wire_deformer(mesh, curve, dropoff, wire_name)

        if wire:
            # Set additional attributes
            if "scale" in wire_config:
                cmds.setAttr(wire + ".scale[0]", wire_config["scale"])
            if "envelope" in wire_config:
                cmds.setAttr(wire + ".envelope", wire_config["envelope"])

            created_wires.append(wire)

    return created_wires
