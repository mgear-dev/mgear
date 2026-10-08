"""Shrink Wrap IO - Core functions.

Export and import Maya shrinkWrap deformers so they can be rebuilt when a
rig is regenerated. The following data is serialized:

* Every settable shrinkWrap setting (projection, offset, falloff, shape
  preservation, target smoothing...).
* The target mesh, and every other incoming connection except the
  geometry pipeline: optional inner mesh, target smooth attributes and
  rig controls driving attributes such as ``envelope``.
* Affected geometry, deformer membership (component tag expression or
  legacy deformer set members), per-geometry sparse weight maps and the
  deformer stack of each geometry.
* The deformer order mode used to place the shrinkWrap on import.

The generic parts come from :mod:`mgear.core.deformer_io`.

Example:
    >>> from mgear.rigbits import shrinkwrap_io
    >>> shrinkwrap_io.export_shrinkwraps(["shrinkWrap1"], "C:/tmp/cloth.shw")
    >>> shrinkwrap_io.import_shrinkwraps("C:/tmp/cloth.shw")
"""

import logging

from maya import cmds

from mgear.core import deformer
from mgear.core import deformer_io
from mgear.core import node_remap
from mgear.core.deformer_io import ORDER_CURRENT

logger = logging.getLogger(__name__)

LOGGER_NAME = "mgear.rigbits.shrinkwrap_io"
SHRINKWRAP_FILE_EXT = ".shw"
FILE_TYPE = "shrinkwrap_config"
SCHEMA_VERSION = 1
ITEMS_KEY = "shrinkwraps"
NODE_TYPE = "shrinkWrap"

# Order matters: envelope is applied last. Attributes missing in older
# Maya versions are skipped.
SHRINKWRAP_ATTRS = (
    "targetSmoothLevel",
    "continuity",
    "smoothUVs",
    "keepBorder",
    "boundaryRule",
    "keepHardEdge",
    "propagateEdgeHardness",
    "keepMapBorders",
    "innerGroupId",
    "projection",
    "closestIfNoIntersection",
    "reverse",
    "bidirectional",
    "boundingBoxCenter",
    "axisReference",
    "alongX",
    "alongY",
    "alongZ",
    "offset",
    "targetInflation",
    "falloff",
    "falloffIterations",
    "shapePreservationEnable",
    "shapePreservationSteps",
    "shapePreservationIterations",
    "shapePreservationReprojection",
    "shapePreservationMethod",
    "envelope",
)


# =============================================================================
# SCENE QUERIES
# =============================================================================


def get_shrinkwrap_nodes():
    """Return all the shrinkWrap deformers in the scene.

    Returns:
        list: shrinkWrap node names.
    """
    return cmds.ls(type=NODE_TYPE) or []


def get_target(node):
    """Return the target mesh of a shrinkWrap.

    Args:
        node (str): shrinkWrap name.

    Returns:
        tuple: ``(transform, shape)`` long names, or ``(None, None)`` when
            no target is connected.
    """
    source = cmds.connectionInfo(node + ".targetGeom", sourceFromDestination=True)
    if not source:
        return None, None
    shape = cmds.ls(source.split(".")[0], long=True)[0]
    return deformer_io.get_parent(shape), shape


def find_shrinkwrap_nodes(nodes):
    """Find the shrinkWraps related to arbitrary nodes.

    Accepts shrinkWrap nodes, deformed geometry or components (searching
    their history), target or inner meshes and controls driving them.

    Args:
        nodes (list): Node or component names.

    Returns:
        list: Unique shrinkWrap names.
    """
    return deformer.find_deformer_nodes(nodes, NODE_TYPE, drivers=True)


# =============================================================================
# SERIALIZE
# =============================================================================


def get_shrinkwrap_config(node, order=ORDER_CURRENT):
    """Collect the full configuration of a shrinkWrap setup.

    Args:
        node (str): shrinkWrap name.
        order (str, optional): Deformer order mode stored for the import.

    Returns:
        dict: Serializable configuration.

    Raises:
        RuntimeError: If the shrinkWrap has no target mesh.
    """
    transform, shape = get_target(node)
    if not shape:
        raise RuntimeError("'{}' has no target mesh, skipped.".format(node))
    return {
        "shrinkwrap": {
            "name": node_remap.leaf_name(node),
            "attrs": deformer_io.get_attrs(node, SHRINKWRAP_ATTRS),
        },
        "order": order,
        "target": {"transform": transform, "shape": shape},
        "connections": deformer_io.get_input_connections(node),
        "members": deformer.get_deformer_set_members(node),
        "geometry": deformer_io.get_geometry_data(node),
    }


def export_shrinkwraps(nodes, path, order=ORDER_CURRENT):
    """Export shrinkWrap configurations to a ``.shw`` file.

    The ``.shw`` extension is added when the path has no extension.

    Args:
        nodes (list): shrinkWrap names.
        path (str): Output file path.
        order (str, optional): Deformer order mode stored for every
            shrink wrap: ``"current"``, ``"front"`` or ``"last"``.

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
    """Load and validate a shrink wrap configuration file.

    Args:
        path (str): File path.

    Returns:
        dict: The loaded data.

    Raises:
        ValueError: If the file is not a shrink wrap configuration.
    """
    return FORMAT.load(path)


def build_shrinkwrap(config, replace=True, order=None):
    """Rebuild a shrinkWrap setup from a configuration.

    Args:
        config (dict): Shrink wrap configuration.
        replace (bool, optional): Delete an existing shrinkWrap with the
            same name first. Target and driven meshes are kept.
        order (str or dict, optional): Deformer order override. None uses
            the mode stored in the configuration.

    Returns:
        str: The created shrinkWrap name, or None if nothing was built.
    """
    name = config["shrinkwrap"]["name"]
    mode = FORMAT.resolve_order(config, order)
    if replace and cmds.objExists(name) and cmds.nodeType(name) == NODE_TYPE:
        cmds.delete(name)
        logger.info("Replaced existing '%s'.", name)

    target = deformer_io.resolve_shape(config["target"])
    if not target:
        logger.warning(
            "Target '%s' of '%s' not found, skipped.",
            deformer_io.entry_label(config["target"]),
            name,
        )
        return None

    targets, geo_map = deformer_io.resolve_geometry(
        config["geometry"], config.get("members")
    )
    if not targets:
        logger.warning("No geometry found for '%s', skipped.", name)
        return None
    positions, front_of_chain = deformer_io.resolve_placements(name, geo_map, mode)

    node = cmds.deformer(
        targets, type=NODE_TYPE, name=name, frontOfChain=front_of_chain
    )[0]
    connected = deformer_io.restore_input_connections(
        node, config.get("connections") or []
    )
    if "targetGeom" not in connected:
        logger.warning("Can't connect the target of '%s', skipped.", name)
        cmds.delete(node)
        return None

    deformer_io.apply_geometry_data(node, geo_map)
    deformer_io.apply_placements(node, positions)
    deformer_io.set_attrs(
        node, config["shrinkwrap"]["attrs"], SHRINKWRAP_ATTRS, skip=connected
    )

    logger.info("Built '%s' on %d geometry (%s order).", node, len(geo_map), mode)
    return node


def import_shrinkwraps(path, names=None, replace=True, order=None):
    """Import shrinkWrap configurations from a file.

    The whole import is a single undo step.

    Args:
        path (str): ``.shw`` file path.
        names (list, optional): shrinkWrap names to import. All if None.
        replace (bool, optional): Delete existing shrinkWraps with the
            same names first.
        order (str or dict, optional): Deformer order override. None uses
            the mode stored for each shrink wrap, a str (``"current"``,
            ``"front"`` or ``"last"``) applies to every shrink wrap and a
            ``{name: mode}`` dict applies per shrink wrap.

    Returns:
        list: Created shrinkWrap names.

    Raises:
        ValueError: If the file is not valid or an order mode is unknown.
    """
    return FORMAT.import_file(path, names, replace, order)


FORMAT = deformer_io.DeformerFormat(
    file_type=FILE_TYPE,
    ext=SHRINKWRAP_FILE_EXT,
    items_key=ITEMS_KEY,
    name_key="shrinkwrap",
    label="shrink wrap",
    collect=get_shrinkwrap_config,
    build=build_shrinkwrap,
    schema_version=SCHEMA_VERSION,
    log=logger,
)
