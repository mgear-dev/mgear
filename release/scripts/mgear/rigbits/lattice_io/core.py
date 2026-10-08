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

Example:
    >>> from mgear.rigbits import lattice_io
    >>> lattice_io.export_lattices(["ffd1"], "C:/tmp/face.lat")
    >>> lattice_io.import_lattices("C:/tmp/face.lat")
"""

import json
import logging
import os

from maya import cmds

from mgear.core import deformer
from mgear.core import node_remap
from mgear.core import utils

logger = logging.getLogger(__name__)

LOGGER_NAME = "mgear.rigbits.lattice_io"
LATTICE_FILE_EXT = ".lat"
FILE_TYPE = "lattice_config"
SCHEMA_VERSION = 1
PRECISION = 6

# Deformer order modes
ORDER_CURRENT = "current"
ORDER_FRONT = "front"
ORDER_LAST = "last"
ORDER_MODES = (ORDER_CURRENT, ORDER_FRONT, ORDER_LAST)
# Placement kind: directly after a given deformer
_AFTER = "after"

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


# =============================================================================
# HELPERS
# =============================================================================


def _short(node):
    """Return the leaf name of a DAG path.

    Args:
        node (str): Node name or DAG path.

    Returns:
        str: Leaf name.
    """
    return node.split("|")[-1]


def _parent(node):
    """Return the long name of the parent of a DAG node.

    Args:
        node (str): DAG node name.

    Returns:
        str: Parent long name, or None if parented to the world.
    """
    parents = cmds.listRelatives(node, parent=True, fullPath=True)
    return parents[0] if parents else None


def _resolve_node(name):
    """Find the scene node for a stored name, tolerant to path changes.

    Args:
        name (str): Stored node name or DAG path.

    Returns:
        str: Long name of the node, or None if not found or ambiguous.
    """
    if not name:
        return None
    hits = node_remap.find_node_candidates(name)
    if len(hits) > 1:
        logger.warning("Ambiguous name '%s' (%d matches).", name, len(hits))
    return hits[0] if len(hits) == 1 else None


def _round_list(values):
    """Round a list of floats to the serialization precision.

    Args:
        values (list): Float values.

    Returns:
        list: Rounded values.
    """
    return [round(v, PRECISION) for v in values]


def _set_attr(plug, value):
    """Set an attribute value when the plug is settable.

    Args:
        plug (str): Plug name ``node.attr``.
        value (object): Value to set.

    Returns:
        bool: True if the value was set.
    """
    if not cmds.objExists(plug) or not cmds.getAttr(plug, settable=True):
        return False
    cmds.setAttr(plug, value)
    return True


def lattice_file_path(path):
    """Return a file path with the ``.lat`` extension when it has none.

    Args:
        path (str): File path.

    Returns:
        str: The path, with ``.lat`` added if it had no extension.
    """
    if not os.path.splitext(path)[1]:
        path += LATTICE_FILE_EXT
    return path


def validate_order(order):
    """Check that a deformer order mode is valid.

    Args:
        order (str): Order mode.

    Raises:
        ValueError: If the mode is not one of ``ORDER_MODES``.
    """
    if order not in ORDER_MODES:
        raise ValueError(
            "Invalid deformer order '{}'. Use one of: {}".format(
                order, ", ".join(ORDER_MODES)
            )
        )


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
    stored = config.get("order") or ORDER_CURRENT
    if order is None:
        mode = stored
    elif isinstance(order, dict):
        mode = order.get(config["ffd"]["name"]) or stored
    else:
        mode = order
    validate_order(mode)
    return mode


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
        ValueError: If the order mode is not valid.
    """
    validate_order(order)
    lat_tfm, lat_shape, base_tfm, _ = deformer.get_lattice_nodes(ffd)
    if not lat_tfm or not base_tfm:
        raise RuntimeError("Can't find lattice nodes for '{}'".format(ffd))

    ffd_attrs = {}
    for attr in FFD_ATTRS:
        if cmds.attributeQuery(attr, node=ffd, exists=True):
            ffd_attrs[attr] = cmds.getAttr("{}.{}".format(ffd, attr))

    geometry = []
    for index, shape in deformer.get_deformer_geometry(ffd):
        weights = deformer.get_deformer_weights(ffd, index, shape=shape)
        geometry.append(
            {
                "index": index,
                "transform": _parent(shape),
                "shape": shape,
                "point_count": utils.get_point_count(shape),
                "component_tag_expression": deformer.get_component_tag_expression(
                    ffd, index
                ),
                "weights": {i: round(w, PRECISION) for i, w in weights.items()},
                "deformer_stack": deformer.get_deformer_stack(shape),
            }
        )

    divisions = deformer.get_lattice_divisions(lat_shape)
    points = deformer.get_lattice_points(lat_shape, divisions)
    return {
        "ffd": {"name": _short(ffd), "attrs": ffd_attrs},
        "order": order,
        "lattice": {
            "name": _short(lat_tfm),
            "shape": _short(lat_shape),
            "parent": _parent(lat_tfm),
            "world_matrix": _round_list(
                cmds.xform(lat_tfm, query=True, worldSpace=True, matrix=True)
            ),
            "divisions": divisions,
            "points": [_round_list(p) for p in points],
            "visibility": cmds.getAttr(lat_tfm + ".visibility"),
        },
        "base": {
            "name": _short(base_tfm),
            "parent": _parent(base_tfm),
            "world_matrix": _round_list(
                cmds.xform(base_tfm, query=True, worldSpace=True, matrix=True)
            ),
            "visibility": cmds.getAttr(base_tfm + ".visibility"),
        },
        "members": deformer.get_deformer_set_members(ffd),
        "geometry": geometry,
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
    path = lattice_file_path(path)

    configs = []
    with utils.main_progress_bar("Exporting lattices", len(ffds)) as step:
        for ffd in ffds:
            step("Exporting {}".format(ffd))
            try:
                configs.append(get_lattice_config(ffd, order))
                logger.info("Collected '%s'.", ffd)
            except RuntimeError as err:
                logger.warning(str(err))

    data = {
        "type": FILE_TYPE,
        "schema_version": SCHEMA_VERSION,
        "maya_version": cmds.about(version=True),
        "scene": cmds.file(query=True, sceneName=True),
        "lattices": configs,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Exported %d lattice(s) to: %s", len(configs), path)
    return data


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
    with open(path, "r") as f:
        data = json.load(f)
    if not isinstance(data, dict) or data.get("type") != FILE_TYPE:
        raise ValueError("Not a lattice configuration file: " + path)
    return data


def _remove_existing(config):
    """Delete a previous build of a lattice configuration.

    Deletes the ffd with the stored name, with its lattice and base, and
    any orphan lattice or base transform using the stored names, so the
    rebuilt nodes keep their exact names.

    Args:
        config (dict): Lattice configuration.
    """
    name = config["ffd"]["name"]
    if cmds.objExists(name) and cmds.nodeType(name) == "ffd":
        deformer.delete_lattice(name)
        logger.info("Replaced existing '%s'.", name)

    for key, shape_type in (("lattice", "lattice"), ("base", "baseLattice")):
        for node in cmds.ls(config[key]["name"], long=True) or []:
            shapes = cmds.listRelatives(
                node, shapes=True, type=shape_type, fullPath=True
            )
            if not shapes:
                continue
            if cmds.listConnections(shapes[0], type="ffd"):
                continue
            cmds.delete(node)
            logger.warning("Removed orphan %s '%s'.", key, _short(node))


def _resolve_shape(entry):
    """Find the scene shape for a stored geometry entry.

    Args:
        entry (dict): Stored geometry entry.

    Returns:
        str: Shape long name, or None.
    """
    shape = _resolve_node(entry.get("shape"))
    if shape and cmds.nodeType(shape) != "transform":
        return shape
    transform = shape or _resolve_node(entry.get("transform"))
    if not transform:
        return None
    shapes = cmds.listRelatives(
        transform, shapes=True, noIntermediate=True, fullPath=True
    )
    return shapes[0] if shapes else None


def _resolve_targets(config):
    """Find the scene geometry for a lattice configuration.

    Args:
        config (dict): Lattice configuration.

    Returns:
        tuple: ``(targets, geo_map)``. Targets are the shapes or
            components to deform. geo_map maps resolved shape long names
            to their stored geometry entries.
    """
    geo_map = {}
    for entry in config["geometry"]:
        shape = _resolve_shape(entry)
        if not shape:
            logger.warning(
                "Geometry '%s' not found, skipped.",
                _short(entry.get("shape") or entry.get("transform") or "?"),
            )
            continue
        geo_map[shape] = entry

    # Legacy set members: one entry per component range, resolve each
    # node once
    resolved = []
    nodes = {}
    for member in config.get("members") or []:
        node, _, comp = member.partition(".")
        if node not in nodes:
            nodes[node] = _resolve_node(node)
        if nodes[node]:
            resolved.append(nodes[node] + ("." + comp if comp else ""))
    return resolved or list(geo_map), geo_map


def _match_name(name, candidates):
    """Find a stored node name in a list of scene names.

    Args:
        name (str): Stored name.
        candidates (list): Scene names.

    Returns:
        str: The matching candidate, or None.
    """
    if name in candidates:
        return name
    bare = node_remap.short_name(name)
    for candidate in candidates:
        if node_remap.short_name(candidate) == bare:
            return candidate
    return None


def _current_position(ffd_name, entry, shape):
    """Resolve where an ffd goes in a geometry stack for the current mode.

    Args:
        ffd_name (str): Stored ffd name.
        entry (dict): Stored geometry entry.
        shape (str): Scene shape, before the ffd is created.

    Returns:
        tuple: ``(ORDER_FRONT, None)``, ``(ORDER_LAST, None)`` or
            ``(_AFTER, deformer_name)``.
    """
    stack = entry.get("deformer_stack") or []
    position = None
    for i, name in enumerate(stack):
        if node_remap.short_name(name) == node_remap.short_name(ffd_name):
            position = i
            break

    if position is not None:
        below = stack[position + 1 :]
        if not below:
            return ORDER_FRONT, None
        current = deformer.get_deformer_stack(shape)
        for name in below:
            match = _match_name(name, current)
            if match:
                return _AFTER, match

    logger.info(
        "Stored deformer order of '%s' on '%s' not found, added last.",
        ffd_name,
        _short(shape),
    )
    return ORDER_LAST, None


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
        parent_node = _resolve_node(parent)
        if parent_node:
            node = cmds.parent(node, parent_node)[0]
        else:
            logger.warning(
                "Parent '%s' not found, '%s' stays in world.",
                parent,
                _short(node),
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
        _remove_existing(config)

    targets, geo_map = _resolve_targets(config)
    if not targets:
        logger.warning("No geometry found for '%s', skipped.", name)
        return None

    # Placement is resolved on the stacks before the ffd is created
    positions = {}
    for shape, entry in geo_map.items():
        if mode == ORDER_CURRENT:
            positions[shape] = _current_position(name, entry, shape)
        else:
            positions[shape] = (mode, None)
    front_of_chain = all(p[0] == ORDER_FRONT for p in positions.values())

    lat_data = config["lattice"]
    base_data = config["base"]
    divisions = lat_data["divisions"]
    ffd, lat_tfm, base_tfm = cmds.lattice(
        targets,
        divisions=divisions,
        objectCentered=True,
        frontOfChain=front_of_chain,
        name=name,
    )
    lat_tfm = cmds.rename(lat_tfm, lat_data["name"])
    base_tfm = cmds.rename(base_tfm, base_data["name"])
    lat_shape = cmds.listRelatives(lat_tfm, shapes=True, fullPath=True)
    if lat_shape and lat_data.get("shape"):
        cmds.rename(lat_shape[0], lat_data["shape"])

    base_tfm = _place(base_tfm, base_data["parent"], base_data["world_matrix"])
    lat_tfm = _place(lat_tfm, lat_data["parent"], lat_data["world_matrix"])
    deformer.set_lattice_points(lat_tfm, divisions, lat_data["points"])
    for node, data in ((lat_tfm, lat_data), (base_tfm, base_data)):
        if "visibility" in data:
            _set_attr(node + ".visibility", data["visibility"])

    for index, shape in deformer.get_deformer_geometry(ffd):
        entry = geo_map.get(shape)
        if not entry:
            continue

        tag_expr = entry.get("component_tag_expression")
        if (
            tag_expr
            and tag_expr != "*"
            and deformer.set_component_tag_expression(ffd, index, tag_expr)
        ):
            logger.info(
                "'%s' uses component tag expression '%s'. Make sure the "
                "tag exists on the rebuilt geometry.",
                _short(shape),
                tag_expr,
            )

        if entry.get("weights"):
            deformer.set_deformer_weights(
                ffd,
                index,
                entry["weights"],
                point_count=entry.get("point_count"),
                shape=shape,
            )

        if front_of_chain:
            continue
        kind, after = positions[shape]
        try:
            if kind == ORDER_FRONT:
                deformer.move_deformer(ffd, shape)
            elif kind == _AFTER:
                deformer.move_deformer(ffd, shape, after=after)
        except (RuntimeError, ValueError) as err:
            logger.warning("Can't reorder '%s' on '%s': %s", ffd, _short(shape), err)

    for attr in FFD_ATTRS:
        if attr in config["ffd"]["attrs"]:
            _set_attr("{}.{}".format(ffd, attr), config["ffd"]["attrs"][attr])

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
    data = load_file(path)
    configs = [
        c for c in data.get("lattices", []) if not names or c["ffd"]["name"] in names
    ]
    # Validate every mode before building anything
    for config in configs:
        resolve_order(config, order)

    created = []
    with utils.undo_chunk("importLattices"):
        with utils.main_progress_bar("Importing lattices", len(configs)) as step:
            for config in configs:
                step("Importing {}".format(config["ffd"]["name"]))
                ffd = build_lattice(config, replace, order)
                if ffd:
                    created.append(ffd)
    logger.info("Imported %d lattice(s).", len(created))
    return created
