"""Proximity Wrap IO - Core functions.

Export and import Maya proximityWrap deformers so they can be rebuilt
when a rig is regenerated. The following data is serialized:

* Node settings (wrap mode, falloff and dropoff scale, smoothing, span
  samples...) and the node falloff ramp.
* Every driver mesh with its own settings (falloff, strength, wrap
  mode, overrides...) and falloff ramp. Drivers are bound again at their
  shape on import, as Maya does when a driver is added.
* Every other incoming connection, e.g. a rig control driving the
  envelope or a driver strength.
* Affected geometry, deformer membership (component tag expression or
  legacy deformer set members), per-geometry sparse weight maps and the
  deformer stack of each geometry.
* The deformer order mode used to place the proximityWrap on import.

The generic parts come from :mod:`mgear.core.deformer_io`.

Example:
    >>> from mgear.rigbits import proximitywrap_io
    >>> proximitywrap_io.export_proximitywraps(["pw1"], "C:/tmp/cloth.pxw")
    >>> proximitywrap_io.import_proximitywraps("C:/tmp/cloth.pxw")
"""

import logging

from maya import cmds

from mgear.core import attribute
from mgear.core import deformer
from mgear.core import deformer_io
from mgear.core import node_remap
from mgear.core.deformer_io import ORDER_CURRENT

logger = logging.getLogger(__name__)

PROXIMITYWRAP_FILE_EXT = ".pxw"
FILE_TYPE = "proximitywrap_config"
SCHEMA_VERSION = 1
ITEMS_KEY = "proximitywraps"
NODE_TYPE = "proximityWrap"

# Order matters: envelope is applied last. Attributes missing in older
# Maya versions are skipped.
PROXIMITYWRAP_ATTRS = (
    "maxDrivers",
    "wrapMode",
    "falloffScale",
    "dropoffRateScale",
    "scaleCompensation",
    "coordinateFrames",
    "smoothNormals",
    "spanSamples",
    "smoothInfluences",
    "softNormalization",
    "useBindTags",
    "envelope",
)

# Settings of each drivers[i] element
DRIVER_ATTRS = (
    "driverFalloffStart",
    "driverFalloffEnd",
    "driverDropoffRate",
    "driverOverrideFalloffRamp",
    "driverStrength",
    "driverUseTransformAsDeformation",
    "driverScaleCompensation",
    "driverSmoothNormals",
    "driverOverrideSmoothNormals",
    "driverSpanSamples",
    "driverOverrideSpanSamples",
    "driverSmoothInfluences",
    "driverOverrideSmoothInfluences",
    "driverWrapMode",
)

# Driver meshes are added again with add_proximity_wrap_drivers
CONNECTION_EXCLUDE = deformer_io.GEOMETRY_PIPELINE_ATTRS + (
    "driverGeometry",
    "driverBindGeometry",
)


def _driver(node, index):
    """Return the plug of a driver element.

    Args:
        node (str): proximityWrap name.
        index (int): Driver index.

    Returns:
        str: ``node.drivers[index]``.
    """
    return "{}.drivers[{}]".format(node, index)


# =============================================================================
# SCENE QUERIES
# =============================================================================


def get_proximitywrap_nodes():
    """Return all the proximityWrap deformers in the scene.

    Returns:
        list: proximityWrap node names.
    """
    return cmds.ls(type=NODE_TYPE) or []


def get_drivers(node):
    """Return the driver meshes of a proximityWrap.

    Args:
        node (str): proximityWrap name.

    Returns:
        list: ``(index, transform, shape)`` tuples with long names.
    """
    return deformer.get_proximity_wrap_drivers(node)


def find_proximitywrap_nodes(nodes):
    """Find the proximityWraps related to arbitrary nodes.

    Accepts proximityWrap nodes, deformed geometry or components
    (searching their history), driver meshes and controls driving them.

    Args:
        nodes (list): Node or component names.

    Returns:
        list: Unique proximityWrap names.
    """
    return deformer.find_deformer_nodes(nodes, NODE_TYPE, drivers=True)


# =============================================================================
# SERIALIZE
# =============================================================================


def get_proximitywrap_config(node, order=ORDER_CURRENT):
    """Collect the full configuration of a proximityWrap setup.

    Args:
        node (str): proximityWrap name.
        order (str, optional): Deformer order mode stored for the import.

    Returns:
        dict: Serializable configuration.

    Raises:
        RuntimeError: If the proximityWrap has no driver.
    """
    drivers = []
    for index, transform, shape in get_drivers(node):
        element = _driver(node, index)
        drivers.append(
            {
                "index": index,
                "transform": transform,
                "shape": shape,
                "attrs": deformer_io.get_attrs(element, DRIVER_ATTRS),
                "falloff_ramp": attribute.get_ramp(element, "driverFalloffRamp"),
            }
        )
    if not drivers:
        raise RuntimeError("'{}' has no driver mesh, skipped.".format(node))

    return {
        "proximitywrap": {
            "name": node_remap.leaf_name(node),
            "attrs": deformer_io.get_attrs(node, PROXIMITYWRAP_ATTRS),
            "falloff_ramp": attribute.get_ramp(node, "falloffRamp"),
        },
        "order": order,
        "drivers": drivers,
        "connections": deformer_io.get_input_connections(
            node, exclude=CONNECTION_EXCLUDE
        ),
        "members": deformer.get_deformer_set_members(node),
        "geometry": deformer_io.get_geometry_data(node),
    }


def export_proximitywraps(nodes, path, order=ORDER_CURRENT):
    """Export proximityWrap configurations to a ``.pxw`` file.

    The ``.pxw`` extension is added when the path has no extension.

    Args:
        nodes (list): proximityWrap names.
        path (str): Output file path.
        order (str, optional): Deformer order mode stored for every
            proximity wrap: ``"current"``, ``"front"`` or ``"last"``.

    Returns:
        dict: The exported data.

    Raises:
        ValueError: If the order mode is not valid.
    """
    return FORMAT.export(nodes, path, order)


# =============================================================================
# DESERIALIZE
# =============================================================================


def load_file(path):
    """Load and validate a proximity wrap configuration file.

    Args:
        path (str): File path.

    Returns:
        dict: The loaded data.

    Raises:
        ValueError: If the file is not a proximity wrap configuration.
    """
    return FORMAT.load(path)


def _resolve_drivers(config, name):
    """Find the scene shapes of the stored drivers.

    Args:
        config (dict): Proximity wrap configuration.
        name (str): Stored proximityWrap name, for messages.

    Returns:
        list: ``(stored driver, shape)`` pairs of the drivers found.
    """
    resolved = []
    for driver in config.get("drivers") or []:
        shape = deformer_io.resolve_shape(driver)
        if shape:
            resolved.append((driver, shape))
        else:
            logger.warning(
                "Driver '%s' of '%s' not found, skipped.",
                deformer_io.entry_label(driver),
                name,
            )
    return resolved


def build_proximitywrap(config, replace=True, order=None):
    """Rebuild a proximityWrap setup from a configuration.

    Args:
        config (dict): Proximity wrap configuration.
        replace (bool, optional): Delete an existing local proximityWrap
            with the same name first. A referenced one is kept. Driver
            and driven meshes are kept.
        order (str or dict, optional): Deformer order override. None uses
            the mode stored in the configuration.

    Returns:
        str: The created proximityWrap name, or None if nothing was built.
    """
    name = config["proximitywrap"]["name"]
    mode = FORMAT.resolve_order(config, order)
    if replace:
        deformer_io.delete_existing(name, NODE_TYPE, logger)

    drivers = _resolve_drivers(config, name)
    if not drivers:
        logger.warning("No driver found for '%s', skipped.", name)
        return None

    targets, geo_map = deformer_io.resolve_geometry(
        config["geometry"], config.get("members")
    )
    if not targets:
        logger.warning("No geometry found for '%s', skipped.", name)
        return None
    positions, front_of_chain = deformer_io.resolve_placements(name, geo_map, mode)

    node = cmds.deformer(
        targets,
        type=NODE_TYPE,
        name=deformer_io.new_node_name(name),
        frontOfChain=front_of_chain,
    )[0]

    # Drivers get new indices: remap their settings and connections
    new_indices = deformer.add_proximity_wrap_drivers(
        node, [shape for _, shape in drivers]
    )
    pairs = [(driver, index) for (driver, _), index in zip(drivers, new_indices)]
    connected = deformer_io.restore_input_connections(
        node,
        config.get("connections") or [],
        remap={"drivers": {driver["index"]: index for driver, index in pairs}},
    )

    for driver, index in pairs:
        prefix = "drivers[{}].".format(index)
        deformer_io.set_attrs(
            _driver(node, index),
            driver.get("attrs") or {},
            DRIVER_ATTRS,
            skip={c[len(prefix) :] for c in connected if c.startswith(prefix)},
        )
        if driver.get("falloff_ramp"):
            attribute.set_ramp(
                _driver(node, index), "driverFalloffRamp", driver["falloff_ramp"]
            )

    deformer_io.apply_geometry_data(node, geo_map)
    deformer_io.apply_placements(node, positions)

    data = config["proximitywrap"]
    deformer_io.set_attrs(node, data["attrs"], PROXIMITYWRAP_ATTRS, skip=connected)
    if data.get("falloff_ramp"):
        attribute.set_ramp(node, "falloffRamp", data["falloff_ramp"])

    logger.info(
        "Built '%s' with %d driver(s) on %d geometry (%s order).",
        node,
        len(new_indices),
        len(geo_map),
        mode,
    )
    return node


def import_proximitywraps(
    path, names=None, replace=True, order=None, check_bind_pose=True
):
    """Import proximityWrap configurations from a file.

    The whole import is a single undo step. Drivers are bound again at
    their current shape, so import with the rig at bind pose: a warning is
    shown when the skinned meshes involved are not.

    Args:
        path (str): ``.pxw`` file path.
        names (list, optional): proximityWrap names to import. All if None.
        replace (bool, optional): Delete existing proximityWraps with the
            same names first.
        order (str or dict, optional): Deformer order override. None uses
            the mode stored for each proximity wrap, a str (``"current"``,
            ``"front"`` or ``"last"``) applies to every proximity wrap and
            a ``{name: mode}`` dict applies per proximity wrap.
        check_bind_pose (bool, optional): Warn when the deformed meshes or
            the drivers are skinned and not at their bind pose.

    Returns:
        list: Created proximityWrap names.

    Raises:
        ValueError: If the file is not valid or an order mode is unknown.
    """
    if check_bind_pose:
        warn_off_bind_pose(path)
    return FORMAT.import_file(path, names, replace, order)


def warn_off_bind_pose(path):
    """Warn when the skinned meshes of a file are not at their bind pose.

    Args:
        path (str): ``.pxw`` file path.

    Returns:
        list: The influences off their bind pose.
    """
    from mgear.core import skin

    off_pose = skin.get_off_bind_pose_influences(get_skinned_meshes(path))
    if off_pose:
        msg = (
            "Proximity wraps imported off the bind pose ({} moved, i.e. {}). "
            "The result depends on the current pose".format(len(off_pose), off_pose[0])
        )
        cmds.warning(msg)
        if not cmds.about(batch=True):
            cmds.inViewMessage(assistMessage=msg, position="topCenter", fade=True)
    return off_pose


FORMAT = deformer_io.DeformerFormat(
    file_type=FILE_TYPE,
    ext=PROXIMITYWRAP_FILE_EXT,
    items_key=ITEMS_KEY,
    name_key="proximitywrap",
    label="proximity wrap",
    collect=get_proximitywrap_config,
    build=build_proximitywrap,
    schema_version=SCHEMA_VERSION,
    log=logger,
)


def get_skinned_meshes(path):
    """Return the scene meshes of a file's deformed geometry and drivers.

    Args:
        path (str): ``.pxw`` file path.

    Returns:
        list: Transforms found in the scene, without duplicates.
    """
    meshes = []
    for config in load_file(path)[ITEMS_KEY]:
        entries = list(config.get("geometry") or [])
        entries += list(config.get("drivers") or [])
        for entry in entries:
            shape = deformer_io.resolve_shape(entry)
            if not shape:
                continue
            transform = deformer_io.get_parent(shape)
            if transform and transform not in meshes:
                meshes.append(transform)
    return meshes


def get_skinned_meshes(path):
    """Return the scene meshes of a file's deformed geometry and drivers.

    Args:
        path (str): ``.pxw`` file path.

    Returns:
        list: Transforms found in the scene, without duplicates.
    """
    entries = {}
    for config in load_file(path)[ITEMS_KEY]:
        for entry in (config.get("geometry") or []) + (config.get("drivers") or []):
            entries[(entry.get("shape"), entry.get("transform"))] = entry
    meshes = []
    for entry in entries.values():
        shape = deformer_io.resolve_shape(entry)
        transform = deformer_io.get_parent(shape) if shape else None
        if transform and transform not in meshes:
            meshes.append(transform)
    return meshes
