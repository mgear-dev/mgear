import logging

from maya import cmds
import maya.api.OpenMaya as om2
import maya.internal.nodes.proximitywrap.node_interface as ifc

import mgear.pymaya as pm
from mgear.core import utils

# Backward-compat re-exports (moved to mgear.core.blendshape)
from mgear.core.blendshape import BS_TARGET_ITEM_ATTR  # noqa: F401
from mgear.core.blendshape import bs_target_weight  # noqa: F401

logger = logging.getLogger(__name__)

# Weights closer than this to the default value are skipped in sparse maps
WEIGHT_TOLERANCE = 1e-6


# =============================================================================
# DEFORMER DETECTION
# =============================================================================


def is_deformer(node):
    """Check if a node is a geometry deformer.

    Uses Maya's API class hierarchy (MFn.kGeometryFilt)
    to detect all deformer types, including custom and
    plugin deformers.

    Args:
        node (str or PyNode): Node name to check.

    Returns:
        bool: True if the node is a deformer.
    """
    m_sel = om2.MSelectionList()
    try:
        m_sel.add(str(node))
    except (RuntimeError, ValueError):
        return False
    return m_sel.getDependNode(0).hasFn(om2.MFn.kGeometryFilt)


def filter_deformers(node_list):
    """Filter a list of nodes to only return deformers.

    Args:
        node_list (list): List of node names or PyNodes.

    Returns:
        list: Filtered list containing only deformer nodes.
    """
    return [node for node in node_list if is_deformer(node)]


def get_deformers(mesh, deformer_type=None, exclude_types=None):
    """Get deformer nodes from a geometry's history.

    Args:
        mesh (str): The geometry transform or shape name (any geometry
            type, not only meshes).
        deformer_type (str, optional): Filter by a specific Maya
            deformer type name (e.g. "skinCluster", "blendShape").
        exclude_types (list, optional): Deformer type names to skip
            (e.g. ``["tweak"]``).

    Returns:
        list: List of deformer node names, from the last evaluated to the
            first evaluated.
    """
    history = cmds.listHistory(mesh, pruneDagObjects=True) or []
    result = [n for n in history if is_deformer(n)]
    if not deformer_type and not exclude_types:
        return result
    exclude_types = exclude_types or ()
    filtered = []
    for node in result:
        node_type = cmds.nodeType(node)
        if deformer_type and node_type != deformer_type:
            continue
        if node_type not in exclude_types:
            filtered.append(node)
    return filtered


# =============================================================================
# DEFORMER ENVELOPE MANAGEMENT
# =============================================================================


def disable_deformer_envelopes(mesh, exclude_types=None):
    """Disable all deformer envelopes on a mesh.

    Stores original envelope values for later restoration
    via ``restore_deformer_envelopes``. Uses ``cmds.mute``
    for envelopes that have input connections.

    Args:
        mesh (str): The mesh transform name.
        exclude_types (set, optional): Deformer type names
            to skip (e.g. ``{"blendShape"}``).

    Returns:
        dict: Mapping of deformer name to original state.
            Values are either a float (original envelope
            value) or the string ``"muted"`` if the envelope
            was muted to disable it.
    """
    exclude_types = exclude_types or set()
    deformers = get_deformers(mesh)
    original_envelopes = {}

    for d in deformers:
        if cmds.nodeType(d) in exclude_types:
            continue
        envelope_attr = "{}.envelope".format(d)
        try:
            original_envelopes[d] = cmds.getAttr(envelope_attr)
            cmds.setAttr(envelope_attr, 0)
        except RuntimeError:
            mute_nodes = cmds.mute(
                envelope_attr, force=True
            )
            if mute_nodes:
                cmds.setAttr(
                    "{}.hold".format(mute_nodes[0]), 0
                )
            original_envelopes[d] = "muted"

    return original_envelopes


def restore_deformer_envelopes(original_envelopes):
    """Restore deformer envelopes to their original values.

    Args:
        original_envelopes (dict): State dict returned by
            ``disable_deformer_envelopes``.
    """
    for d, val in original_envelopes.items():
        if not cmds.objExists(d):
            continue
        envelope_attr = "{}.envelope".format(d)
        if val == "muted":
            cmds.mute(
                envelope_attr, disable=True, force=True
            )
        else:
            try:
                cmds.setAttr(envelope_attr, val)
            except RuntimeError:
                pass


# =============================================================================
# WRAP DEFORMER
# =============================================================================


def create_wrap_deformer(
    target, driver, use_base_duplicate=False, name=None
):
    """Create a wrap deformer on target driven by driver.

    Supports two base mesh strategies:

    - **Intermediate shape** (``use_base_duplicate=False``):
      Connects to the driver's existing intermediate (orig)
      shape. Suitable when the driver won't be modified or
      deleted during the wrap's lifetime.

    - **Base duplicate** (``use_base_duplicate=True``):
      Creates a separate static duplicate as the base mesh.
      Safer when the wrap will be deleted later, as it
      avoids corrupting the driver's deformation chain.

    Args:
        target (str): Target mesh transform to deform.
        driver (str): Driver mesh transform.
        use_base_duplicate (bool): If True, create a
            separate base mesh duplicate instead of using
            the driver's intermediate shape.
        name (str, optional): Name for the wrap deformer.

    Returns:
        tuple: ``(wrap_node, base_dup)`` where base_dup is
            the static base mesh to clean up later (only
            when ``use_base_duplicate=True``), or None.
            Returns ``(None, None)`` on failure.
    """
    # Get visible shape on driver
    driver_shapes = cmds.listRelatives(
        driver, shapes=True, type="mesh",
        noIntermediate=True, fullPath=True,
    ) or []

    if not driver_shapes:
        return None, None

    driver_shape = driver_shapes[0]

    # Determine base mesh strategy
    base_dup = None
    if use_base_duplicate:
        base_name = "{}_wrapBase".format(
            driver.split("|")[-1]
        )
        base_dup = cmds.duplicate(
            driver, returnRootsOnly=True,
            inputConnections=False, name=base_name,
        )[0]

        # Unlock transforms on base duplicate
        for attr in (
            "translateX", "translateY", "translateZ",
            "rotateX", "rotateY", "rotateZ",
            "scaleX", "scaleY", "scaleZ",
        ):
            try:
                cmds.setAttr(
                    "{}.{}".format(base_dup, attr),
                    lock=False,
                )
            except RuntimeError:
                pass

        cmds.delete(base_dup, constructionHistory=True)
        cmds.setAttr(
            "{}.visibility".format(base_dup), 0
        )

        base_shapes = cmds.listRelatives(
            base_dup, shapes=True, type="mesh",
            fullPath=True,
        ) or []
        if not base_shapes:
            cmds.delete(base_dup)
            return None, None

        base_shape = base_shapes[0]
    else:
        # Use driver's intermediate (orig) shape
        all_shapes = cmds.listRelatives(
            driver, shapes=True, type="mesh",
            fullPath=True,
        ) or []
        orig_shapes = [
            s for s in all_shapes
            if cmds.getAttr(
                "{}.intermediateObject".format(s)
            )
        ]
        if orig_shapes:
            base_shape = orig_shapes[0]
        else:
            base_shape = driver_shape

    # Create wrap deformer
    wrap_name = name or "wrap"
    wrap = cmds.deformer(
        target, type="wrap", name=wrap_name
    )[0]
    cmds.setAttr("{}.exclusiveBind".format(wrap), 1)
    cmds.setAttr(
        "{}.autoWeightThreshold".format(wrap), 1
    )
    cmds.setAttr("{}.dropoff[0]".format(wrap), 4.0)
    cmds.setAttr("{}.inflType[0]".format(wrap), 2)

    # Connect base mesh
    cmds.connectAttr(
        "{}.worldMesh[0]".format(base_shape),
        "{}.basePoints[0]".format(wrap),
        force=True,
    )

    # Connect driver (visible/deformed shape)
    cmds.connectAttr(
        "{}.outMesh".format(driver_shape),
        "{}.driverPoints[0]".format(wrap),
        force=True,
    )

    # Connect geometry matrix
    cmds.connectAttr(
        "{}.worldMatrix[0]".format(target),
        "{}.geomMatrix".format(wrap),
        force=True,
    )

    return wrap, base_dup


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


def get_plug_source_shape(plug):
    """Return the shape connected to a destination plug.

    Args:
        plug (str): Destination plug, e.g. ``shrinkWrap1.targetGeom``.

    Returns:
        tuple: ``(transform, shape)`` long names, or ``(None, None)`` when
            nothing is connected.
    """
    source = cmds.connectionInfo(plug, sourceFromDestination=True)
    if not source:
        return None, None
    shape = cmds.ls(source.split(".")[0], long=True)[0]
    parents = cmds.listRelatives(shape, parent=True, fullPath=True)
    return (parents[0] if parents else None), shape


def get_proximity_wrap_drivers(node):
    """Return the driver meshes of a proximityWrap.

    Args:
        node (str): proximityWrap name.

    Returns:
        list: ``(index, transform, shape)`` tuples with long names.
    """
    drivers = []
    for index in cmds.getAttr(node + ".drivers", multiIndices=True) or []:
        transform, shape = get_plug_source_shape(
            "{}.drivers[{}].driverGeometry".format(node, index)
        )
        if shape:
            drivers.append((index, transform, shape))
    return drivers


PROXIMITY_WRAP_MODES = ("offset", "surface", "snap", "rigid", "cluster")


def add_proximity_wrap_drivers(node, shapes):
    """Add driver meshes to a proximityWrap deformer.

    Uses Maya's proximity wrap node interface. ``addDriver`` is tried
    first and ``addDrivers`` is used when it doesn't exist (Maya 2023+),
    the same order as :func:`create_proximity_wrap` always used.

    Args:
        node (str): proximityWrap name.
        shapes (list): Driver shape names.

    Returns:
        list: The new driver indices, in the order of ``shapes``.

    Raises:
        AttributeError: If the proximity wrap interface can't add drivers.
    """
    pwni = ifc.NodeInterface(node)
    indices = []
    for shape in shapes:
        before = set(cmds.getAttr(node + ".drivers", multiIndices=True) or [])
        try:
            pwni.addDriver(shape)
        except AttributeError:
            pwni.addDrivers(shape)
        after = cmds.getAttr(node + ".drivers", multiIndices=True) or []
        indices += [i for i in after if i not in before]
    return indices


def create_proximity_wrap(
    target_geos,
    driver_geos,
    deformer_name=None,
    weights_path=None,
    weights_filename=None,
    smoothInfluences=0,
    wrap_mode=None,
):
    """
    Create a proximity wrap deformer.

    Args:
        target_geos: Single geometry or list of geometries to be deformed (string or PyNode)
        driver_geos: Single driver geometry or list of drivers (string or PyNode)
        deformer_name: Optional name for the deformer. If None, generates from first target geo.
        weights_path: Optional path to the weights file directory
        weights_filename: Optional filename for the weights (defaults to deformer_name + ".json")
        smoothInfluences (int, optional): Smooth influences value.
        wrap_mode (int or str, optional): Wrap mode, as the enum index or
            its name: "offset", "surface", "snap", "rigid" or "cluster".
            None keeps Maya's default (surface).

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

    # Add all drivers (Maya 2023 changed method name to addDrivers)
    add_proximity_wrap_drivers(
        d[0], [driver_geo.getShape().name() for driver_geo in driver_geos]
    )

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

    if wrap_mode is not None:
        if isinstance(wrap_mode, str):
            wrap_mode = PROXIMITY_WRAP_MODES.index(wrap_mode.lower())
        cmds.setAttr(f"{deformer_name}.wrapMode", wrap_mode)

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


# =============================================================================
# DEFORMER STACK ORDER
# =============================================================================


def get_deformer_stack(geometry):
    """Return the deformers of a geometry in stack order.

    The list goes from the last evaluated deformer (closest to the output)
    to the first evaluated one, the same order as ``cmds.listHistory``.
    Tweak nodes are skipped, since they can not be reordered.

    Args:
        geometry (str): Geometry transform or shape name.

    Returns:
        list: Deformer names.
    """
    return get_deformers(geometry, exclude_types=("tweak",))


def move_deformer(deformer, geometry, after=None, stack=None):
    """Move a deformer in the deformer stack of a geometry.

    The other deformers keep their relative order.

    Args:
        deformer (str): Deformer to move.
        geometry (str): Geometry transform or shape name.
        after (str, optional): Deformer that ``deformer`` should evaluate
            directly after. If None, ``deformer`` is moved to the front of
            the chain (evaluated first).
        stack (list, optional): Current stack from
            :func:`get_deformer_stack`, to avoid querying it again.

    Raises:
        ValueError: If ``deformer`` or ``after`` is not in the stack.
    """
    stack = list(stack or get_deformer_stack(geometry))
    if deformer not in stack:
        raise ValueError("'{}' does not deform '{}'".format(deformer, geometry))
    others = [d for d in stack if d != deformer]
    if not others:
        return

    # cmds.reorderDeformers(a, b) moves b directly after a in the stack
    # list, so b evaluates directly before a.
    if after is None:
        if stack[-1] != deformer:
            cmds.reorderDeformers(others[-1], deformer, geometry)
        return

    if after not in others:
        raise ValueError("'{}' does not deform '{}'".format(after, geometry))
    if stack.index(deformer) == stack.index(after) - 1:
        return
    index = others.index(after)
    if index > 0:
        cmds.reorderDeformers(others[index - 1], deformer, geometry)
        return

    # "after" is the last evaluated deformer: swap up to the top
    for above in reversed(stack[: stack.index(deformer)]):
        cmds.reorderDeformers(deformer, above, geometry)


# =============================================================================
# DEFORMER MEMBERSHIP AND WEIGHTS
# =============================================================================


def get_deformer_geometry(deformer):
    """Return the geometry affected by a deformer.

    Args:
        deformer (str): Deformer name.

    Returns:
        list: ``(geo_index, shape_long_name)`` tuples.
    """
    shapes = cmds.deformer(deformer, query=True, geometry=True) or []
    indices = cmds.deformer(deformer, query=True, geometryIndices=True) or []
    return [
        (index, cmds.ls(shape, long=True)[0]) for shape, index in zip(shapes, indices)
    ]


def get_deformer_set_members(deformer):
    """Return the members of a deformer's legacy deformer set.

    Deformers using component tags (Maya 2022+ default) have no deformer
    set, so the result is empty.

    Args:
        deformer (str): Deformer name.

    Returns:
        list: Member strings (objects or components).
    """
    members = []
    for obj_set in cmds.listConnections(deformer, type="objectSet") or []:
        members += cmds.sets(obj_set, query=True) or []
    return members


def get_component_tag_expression(deformer, geo_index):
    """Return the component tag expression of a deformer input.

    Args:
        deformer (str): Deformer name.
        geo_index (int): Geometry index in the deformer.

    Returns:
        str: The expression, or None if the deformer has no component tag
            support (Maya < 2022).
    """
    plug = "{}.input[{}].componentTagExpression".format(deformer, geo_index)
    return cmds.getAttr(plug) if cmds.objExists(plug) else None


def set_component_tag_expression(deformer, geo_index, expression):
    """Set the component tag expression of a deformer input.

    Args:
        deformer (str): Deformer name.
        geo_index (int): Geometry index in the deformer.
        expression (str): Component tag expression, e.g. ``"lips*"``.

    Returns:
        bool: True if set, False if the deformer has no component tag
            support (Maya < 2022).
    """
    plug = "{}.input[{}].componentTagExpression".format(deformer, geo_index)
    if not cmds.objExists(plug):
        return False
    cmds.setAttr(plug, expression, type="string")
    return True


def _get_deformer_shape(deformer, geo_index):
    """Return the shape deformed at a geometry index.

    Args:
        deformer (str): Deformer name.
        geo_index (int): Geometry index in the deformer.

    Returns:
        str: Shape long name.

    Raises:
        ValueError: If the deformer has no geometry at that index.
    """
    shape = dict(get_deformer_geometry(deformer)).get(geo_index)
    if not shape:
        raise ValueError("'{}' has no geometry at index {}".format(deformer, geo_index))
    return shape


def get_deformer_weights(deformer, geo_index, default=1.0, sparse=True, shape=None):
    """Read the weight map of a deformer for one geometry.

    Works with any weighted deformer (geometryFilter) and any geometry
    type, including setups that use component tags. The whole map is read
    with a single command.

    Args:
        deformer (str): Deformer name.
        geo_index (int): Geometry index in the deformer.
        default (float, optional): Weights within tolerance of this value
            are skipped when ``sparse`` is True.
        sparse (bool, optional): If True, only return weights different
            from ``default``. If False, return the weight of every point.
        shape (str, optional): Shape deformed at ``geo_index``, to avoid
            querying it again.

    Returns:
        dict: ``{point_index (int): weight (float)}``.
    """
    shape = shape or _get_deformer_shape(deformer, geo_index)
    count = utils.get_point_count(shape)
    if not count:
        return {}
    values = cmds.getAttr(
        "{}.weightList[{}].weights[0:{}]".format(deformer, geo_index, count - 1)
    )
    if not isinstance(values, list):
        values = [values]
    if not sparse:
        return dict(enumerate(values))
    return {
        index: value
        for index, value in enumerate(values)
        if abs(value - default) > WEIGHT_TOLERANCE
    }


def set_deformer_weights(
    deformer,
    geo_index,
    weights,
    default=1.0,
    point_count=None,
    shape=None,
    sparse=False,
):
    """Set the weight map of a deformer for one geometry.

    By default every point gets a weight: points missing in ``weights``
    get ``default``, and the whole map is written with a single command.

    Args:
        deformer (str): Deformer name.
        geo_index (int): Geometry index in the deformer.
        weights (dict): ``{point_index: weight}``. Keys can be int or str
            (as loaded from JSON). Indices out of range are ignored.
        default (float, optional): Weight for points not in ``weights``.
        point_count (int, optional): Expected point count. A warning is
            logged if the geometry has a different count.
        shape (str, optional): Shape deformed at ``geo_index``, to avoid
            querying it again.
        sparse (bool, optional): Only write the given weights, e.g. on a
            new deformer where every weight is still the default. Keeps
            the scene small when few points are painted. A dense map is
            written in one command instead when most points are given.
    """
    shape = shape or _get_deformer_shape(deformer, geo_index)
    count = utils.get_point_count(shape)
    if point_count is not None and point_count != count:
        logger.warning(
            "Point count mismatch on '%s' (expected: %d, scene: %d). "
            "Weights applied by index.",
            shape.split("|")[-1],
            point_count,
            count,
        )
    if not count:
        return

    if sparse and len(weights) < count // 2:
        plug = "{}.weightList[{}].weights[{}]"
        for index, value in weights.items():
            index = int(index)
            if 0 <= index < count:
                cmds.setAttr(plug.format(deformer, geo_index, index), float(value))
        return

    values = [default] * count
    for index, value in weights.items():
        index = int(index)
        if 0 <= index < count:
            values[index] = float(value)
    cmds.setAttr(
        "{}.weightList[{}].weights[0:{}]".format(deformer, geo_index, count - 1),
        *values,
        size=count,
    )


# =============================================================================
# LATTICE
# =============================================================================


def get_ffd_nodes():
    """Return all the ffd (lattice) deformers in the scene.

    Returns:
        list: ffd node names.
    """
    return cmds.ls(type="ffd") or []


def find_deformer_nodes(nodes, deformer_type, drivers=False, driver_types=None):
    """Find the deformers of a type related to arbitrary nodes.

    Accepts deformer nodes and deformed geometry or components (searching
    their history). With ``drivers``, also the deformers driven by the
    nodes' shapes, e.g. a lattice shape or a shrinkWrap target mesh, or by
    the node itself, e.g. a control driving the envelope. Missing nodes
    are ignored.

    Args:
        nodes (list): Node or component names.
        deformer_type (str): Deformer node type, e.g. ``"shrinkWrap"``.
        drivers (bool, optional): Also search downstream connections.
        driver_types (tuple, optional): Only search downstream connections
            of shapes of these types, e.g. ``("lattice", "baseLattice")``.

    Returns:
        list: Unique deformer names.
    """
    result = {}
    # A component selection gives one entry per range: query each node once
    for node in dict.fromkeys(n.split(".")[0] for n in nodes or []):
        if not cmds.objExists(node):
            continue
        if cmds.nodeType(node) == deformer_type:
            result.setdefault(node)
            continue
        found = get_deformers(node, deformer_type)
        if drivers:
            shapes = cmds.listRelatives(
                node, shapes=True, noIntermediate=True, fullPath=True
            )
            for shape in shapes or [node]:
                if driver_types and cmds.nodeType(shape) not in driver_types:
                    continue
                found += (
                    cmds.listConnections(
                        shape, source=False, destination=True, type=deformer_type
                    )
                    or []
                )
        for deformer_node in found:
            result.setdefault(deformer_node)
    return list(result)


def find_ffd_nodes(nodes):
    """Find the ffd deformers related to arbitrary nodes.

    Accepts ffd nodes, lattice or base lattice transforms and shapes, and
    deformed geometry or components (searching their history).

    Args:
        nodes (list): Node or component names.

    Returns:
        list: Unique ffd node names.
    """
    return find_deformer_nodes(
        nodes, "ffd", drivers=True, driver_types=("lattice", "baseLattice")
    )


def get_lattice_nodes(ffd):
    """Return the lattice and base lattice nodes driving an ffd.

    Args:
        ffd (str): ffd deformer name.

    Returns:
        tuple: ``(lattice_transform, lattice_shape, base_transform,
            base_shape)`` as long names. Missing items are None.
    """

    def _connected(node_type):
        shapes = cmds.listConnections(
            ffd, source=True, destination=False, type=node_type, shapes=True
        )
        if not shapes:
            return None, None
        shape = cmds.ls(shapes[0], long=True)[0]
        parents = cmds.listRelatives(shape, parent=True, fullPath=True)
        return (parents[0] if parents else None), shape

    lat_tfm, lat_shape = _connected("lattice")
    base_tfm, base_shape = _connected("baseLattice")
    return lat_tfm, lat_shape, base_tfm, base_shape


def _get_lattice_shape(lattice):
    """Return the lattice shape of a lattice transform or shape.

    Args:
        lattice (str): Lattice transform or shape name.

    Returns:
        str: Lattice shape long name.

    Raises:
        ValueError: If no lattice shape is found.
    """
    if cmds.nodeType(lattice) == "lattice":
        return cmds.ls(lattice, long=True)[0]
    shapes = cmds.listRelatives(
        lattice, shapes=True, type="lattice", noIntermediate=True, fullPath=True
    )
    if not shapes:
        raise ValueError("'{}' is not a lattice".format(lattice))
    return shapes[0]


def get_lattice_divisions(lattice):
    """Return the s, t and u divisions of a lattice.

    Args:
        lattice (str): Lattice transform or shape name.

    Returns:
        list: ``[s, t, u]`` divisions.
    """
    shape = _get_lattice_shape(lattice)
    return [cmds.getAttr("{}.{}Divisions".format(shape, axis)) for axis in "stu"]


def get_lattice_points(lattice, divisions=None):
    """Read the object space positions of all the lattice points.

    Points are ordered with nested loops ``s -> t -> u`` (u varies
    fastest). All the points are read with a single command.

    Args:
        lattice (str): Lattice transform or shape name.
        divisions (list, optional): ``[s, t, u]`` divisions. Read from the
            lattice if None.

    Returns:
        list: ``[x, y, z]`` positions.
    """
    shape = _get_lattice_shape(lattice)
    s_div, t_div, u_div = divisions or get_lattice_divisions(shape)
    count = s_div * t_div * u_div
    raw = cmds.getAttr("{}.controlPoints[0:{}]".format(shape, count - 1))

    # Maya stores the points with s varying fastest
    points = []
    for s in range(s_div):
        for t in range(t_div):
            for u in range(u_div):
                points.append(list(raw[s + t * s_div + u * s_div * t_div]))
    return points


def set_lattice_points(lattice, divisions, points):
    """Set the object space positions of all the lattice points.

    All the points are set with a single, undoable command.

    Args:
        lattice (str): Lattice transform or shape name.
        divisions (list): ``[s, t, u]`` divisions.
        points (list): ``[x, y, z]`` positions ordered ``s -> t -> u``
            (u varies fastest), as returned by :func:`get_lattice_points`.

    Raises:
        ValueError: If the number of points doesn't match the divisions.
    """
    shape = _get_lattice_shape(lattice)
    s_div, t_div, u_div = divisions
    count = s_div * t_div * u_div
    if len(points) != count:
        raise ValueError(
            "Expected {} lattice points, got {}".format(count, len(points))
        )

    values = []
    for index in range(count):
        s = index % s_div
        t = (index // s_div) % t_div
        u = index // (s_div * t_div)
        values.extend(points[s * t_div * u_div + t * u_div + u])
    cmds.setAttr("{}.controlPoints[0:{}]".format(shape, count - 1), *values)


def delete_lattice(ffd):
    """Delete an ffd deformer with its lattice and base lattice.

    The deformed geometry is kept.

    Args:
        ffd (str): ffd deformer name.
    """
    lat_tfm, _, base_tfm, _ = get_lattice_nodes(ffd)
    nodes = [n for n in (ffd, lat_tfm, base_tfm) if n and cmds.objExists(n)]
    if nodes:
        cmds.delete(nodes)
