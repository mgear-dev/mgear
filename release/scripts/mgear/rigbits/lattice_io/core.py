"""Lattice IO - Core functions.

Export and import ffd lattice setups so they can be rebuilt exactly when a
rig is regenerated. The following data is serialized:

* ffd deformer settings (local influence, outside lattice, envelope...).
* Lattice and base lattice transforms (world matrix, parent, visibility).
* Lattice divisions and the object space position of every lattice point.
* Affected geometry, deformer membership (component tag expression or
  legacy deformer set members), per-geometry sparse weight maps and the
  deformer stack of each geometry.
* The deformer order mode used to place the ffd on import.

The generic parts (file envelope, geometry data, order modes, import
loop) come from :mod:`mgear.core.deformer_io`.

Example:
    >>> from mgear.rigbits import lattice_io
    >>> lattice_io.export_lattices(["ffd1"], "C:/tmp/face.lat")
    >>> lattice_io.import_lattices("C:/tmp/face.lat")
"""

import logging

from maya import cmds

from mgear.core import deformer
from mgear.core import deformer_io
from mgear.core import node_remap
from mgear.core.deformer_io import ORDER_CURRENT
from mgear.core.node import is_referenced

logger = logging.getLogger(__name__)

LOGGER_NAME = "mgear.rigbits.lattice_io"
LATTICE_FILE_EXT = ".lat"
FILE_TYPE = "lattice_config"
SCHEMA_VERSION = 1
ITEMS_KEY = "lattices"

# Order matters: freezeGeometry and envelope are applied last.
FFD_ATTRS = (
    "local",
    "localInfluenceS",
    "localInfluenceT",
    "localInfluenceU",
    "outsideLattice",
    "outsideFalloffDist",
    "usePartialResolution",
    "partialResolution",
    "bindToOriginalGeometry",
    "freezeGeometry",
    "envelope",
)


def lattice_file_path(path):
    """Return a file path with the ``.lat`` extension when it has none.

    Args:
        path (str): File path.

    Returns:
        str: The path, with ``.lat`` added if it had no extension.
    """
    return FORMAT.file_path(path)


def resolve_order(config, order=None):
    """Return the deformer order mode to use for a lattice configuration.

    Args:
        config (dict): Lattice configuration.
        order (str or dict, optional): Override. None uses the stored mode,
            a str applies to every lattice and a ``{ffd_name: mode}`` dict
            applies per lattice.

    Returns:
        str: The order mode.

    Raises:
        ValueError: If the resolved mode is not valid.
    """
    return FORMAT.resolve_order(config, order)


# =============================================================================
# SERIALIZE
# =============================================================================


def get_lattice_config(ffd, order=ORDER_CURRENT):
    """Collect the full configuration of an ffd lattice setup.

    Args:
        ffd (str): ffd deformer name.
        order (str, optional): Deformer order mode stored for the import.

    Returns:
        dict: Serializable configuration.

    Raises:
        RuntimeError: If the lattice nodes can't be found.
    """
    lat_tfm, lat_shape, base_tfm, _ = deformer.get_lattice_nodes(ffd)
    if not lat_tfm or not base_tfm:
        raise RuntimeError("Can't find lattice nodes for '{}'".format(ffd))

    divisions = deformer.get_lattice_divisions(lat_shape)
    points = deformer.get_lattice_points(lat_shape, divisions)
    return {
        "ffd": {
            "name": node_remap.leaf_name(ffd),
            "attrs": deformer_io.get_attrs(ffd, FFD_ATTRS),
        },
        "order": order,
        "lattice": {
            "name": node_remap.leaf_name(lat_tfm),
            "shape": node_remap.leaf_name(lat_shape),
            "parent": deformer_io.get_parent(lat_tfm),
            "world_matrix": deformer_io.round_list(
                cmds.xform(lat_tfm, query=True, worldSpace=True, matrix=True)
            ),
            "divisions": divisions,
            "points": [deformer_io.round_list(p) for p in points],
            "visibility": cmds.getAttr(lat_tfm + ".visibility"),
        },
        "base": {
            "name": node_remap.leaf_name(base_tfm),
            "parent": deformer_io.get_parent(base_tfm),
            "world_matrix": deformer_io.round_list(
                cmds.xform(base_tfm, query=True, worldSpace=True, matrix=True)
            ),
            "visibility": cmds.getAttr(base_tfm + ".visibility"),
        },
        "members": deformer.get_deformer_set_members(ffd),
        "geometry": deformer_io.get_geometry_data(ffd),
    }


def export_lattices(ffds, path, order=ORDER_CURRENT):
    """Export lattice configurations to a ``.lat`` file.

    The ``.lat`` extension is added when the path has no extension.

    Args:
        ffds (list): ffd deformer names.
        path (str): Output file path.
        order (str, optional): Deformer order mode stored for every
            lattice: ``"current"``, ``"front"`` or ``"last"``.

    Returns:
        dict: The exported data.

    Raises:
        ValueError: If the order mode is not valid.
    """
    return FORMAT.export(ffds, path, order)


# =============================================================================
# DESERIALIZE
# =============================================================================


def load_file(path):
    """Load and validate a lattice configuration file.

    Accepts ``.lat`` files and legacy ``.json`` files with the same
    content.

    Args:
        path (str): File path.

    Returns:
        dict: The loaded data.

    Raises:
        ValueError: If the file is not a lattice configuration.
    """
    return FORMAT.load(path)


def _rename_in_place(node, name, shape_type, replace):
    """Rename a placed lattice or base transform to its stored name.

    The stored namespace is dropped, see ``deformer_io.new_node_name``.
    With replace, a local orphan transform (a lattice or base that drives
    no ffd) already using the name next to the node is deleted first, so
    the node keeps its exact name. Nodes with that name anywhere else are
    left alone: they can't clash.

    Args:
        node (str): Long name of the placed transform.
        name (str): Stored leaf name.
        shape_type (str): "lattice" or "baseLattice".
        replace (bool): Delete an orphan that holds the name.

    Returns:
        str: Long name of the renamed node.
    """
    name = deformer_io.new_node_name(name)
    parent = cmds.listRelatives(node, parent=True, fullPath=True)
    target = "{}|{}".format(parent[0] if parent else "", name)
    if (
        replace
        and target != node
        and cmds.objExists(target)
        and not is_referenced(target)
    ):
        shapes = cmds.listRelatives(target, shapes=True, type=shape_type, fullPath=True)
        if shapes and not cmds.listConnections(shapes[0], type="ffd"):
            cmds.delete(target)
            logger.warning("Removed orphan %s '%s'.", shape_type, name)
    return cmds.ls(cmds.rename(node, name), long=True)[0]


def _place(node, parent, matrix):
    """Parent a transform and set its world matrix.

    Args:
        node (str): Transform name.
        parent (str): Stored parent name, can be None.
        matrix (list): World matrix (16 floats).

    Returns:
        str: Long name of the node after parenting.
    """
    if parent:
        parent_node = node_remap.find_node(parent)
        if parent_node:
            node = cmds.parent(node, parent_node)[0]
        else:
            logger.warning(
                "Parent '%s' not found, '%s' stays in world.",
                parent,
                node_remap.leaf_name(node),
            )
    node = cmds.ls(node, long=True)[0]
    cmds.xform(node, worldSpace=True, matrix=matrix)
    return node


def build_lattice(config, replace=True, order=None):
    """Rebuild a lattice setup from a configuration.

    Args:
        config (dict): Lattice configuration.
        replace (bool, optional): Delete a previous build with the same
            names first.
        order (str or dict, optional): Deformer order override. None uses
            the mode stored in the configuration.

    Returns:
        str: The created ffd name, or None if nothing was built.
    """
    name = config["ffd"]["name"]
    mode = resolve_order(config, order)
    if replace:
        # A local ffd with the stored name (or its name without namespace)
        # goes with its lattice and base. A referenced ffd is kept.
        deformer_io.delete_existing(name, "ffd", logger, delete=deformer.delete_lattice)

    targets, geo_map = deformer_io.resolve_geometry(
        config["geometry"], config.get("members")
    )
    if not targets:
        logger.warning("No geometry found for '%s', skipped.", name)
        return None
    positions, front_of_chain = deformer_io.resolve_placements(name, geo_map, mode)

    lat_data = config["lattice"]
    base_data = config["base"]
    divisions = lat_data["divisions"]
    ffd = cmds.lattice(
        targets,
        divisions=divisions,
        objectCentered=True,
        frontOfChain=front_of_chain,
        name=deformer_io.new_node_name(name),
    )[0]
    # Long names: cmds.lattice returns short names, which can be ambiguous
    lat_tfm, _, base_tfm, _ = deformer.get_lattice_nodes(ffd)
    # Renamed once placed, so only a node next to the final place can clash
    base_tfm = _place(base_tfm, base_data["parent"], base_data["world_matrix"])
    lat_tfm = _place(lat_tfm, lat_data["parent"], lat_data["world_matrix"])
    base_tfm = _rename_in_place(base_tfm, base_data["name"], "baseLattice", replace)
    lat_tfm = _rename_in_place(lat_tfm, lat_data["name"], "lattice", replace)
    lat_shape = cmds.listRelatives(lat_tfm, shapes=True, fullPath=True)
    if lat_shape and lat_data.get("shape"):
        cmds.rename(lat_shape[0], deformer_io.new_node_name(lat_data["shape"]))
    deformer.set_lattice_points(lat_tfm, divisions, lat_data["points"])
    for node, data in ((lat_tfm, lat_data), (base_tfm, base_data)):
        if "visibility" in data:
            deformer_io.set_attr(node + ".visibility", data["visibility"])

    deformer_io.apply_geometry_data(ffd, geo_map)
    deformer_io.apply_placements(ffd, positions)
    deformer_io.set_attrs(ffd, config["ffd"]["attrs"], FFD_ATTRS)

    logger.info("Built '%s' on %d geometry (%s order).", ffd, len(geo_map), mode)
    return ffd


def import_lattices(path, names=None, replace=True, order=None):
    """Import lattice configurations from a file.

    The whole import is a single undo step.

    Args:
        path (str): ``.lat`` (or legacy ``.json``) file path.
        names (list, optional): ffd names to import. All if None.
        replace (bool, optional): Delete previous builds with the same
            names first.
        order (str or dict, optional): Deformer order override. None uses
            the mode stored for each lattice, a str (``"current"``,
            ``"front"`` or ``"last"``) applies to every lattice and a
            ``{ffd_name: mode}`` dict applies per lattice.

    Returns:
        list: Created ffd names.

    Raises:
        ValueError: If the file is not valid or an order mode is unknown.
    """
    return FORMAT.import_file(path, names, replace, order)


FORMAT = deformer_io.DeformerFormat(
    file_type=FILE_TYPE,
    ext=LATTICE_FILE_EXT,
    items_key=ITEMS_KEY,
    name_key="ffd",
    label="lattice",
    collect=get_lattice_config,
    build=build_lattice,
    schema_version=SCHEMA_VERSION,
    log=logger,
)
