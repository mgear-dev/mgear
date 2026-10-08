"""Generic deformer IO: serialize and rebuild deformer setups.

Building blocks shared by the deformer IO tools (Lattice IO, Shrink Wrap
IO, ...). No Qt.

* :class:`DeformerFormat`: a tool's file format (extension, type, layout)
  plus its ``collect`` and ``build`` functions. It provides the export,
  load and import pipeline, the per-deformer order modes and the file
  name rules, so a tool only writes how to read and rebuild one deformer.
* Deformer order modes: ``current`` (as exported), ``front`` and ``last``,
  resolved per geometry and applied with ``deformer.move_deformer``.
* Geometry data: affected shapes, sparse weights, component tag
  expressions, legacy set members and deformer stacks.
* Attributes and incoming connections.

Messages go to this module's logger. Tool windows show them by attaching
their log handler to it (see ``pyqt.QtLogHandler.attach``).

Example:
    >>> from mgear.core import deformer_io
    >>> geometry = deformer_io.get_geometry_data("cluster1")
    >>> targets, geo_map = deformer_io.resolve_geometry(geometry)
"""

import json
import logging
import os
import re

from maya import cmds

from mgear.core import deformer
from mgear.core import node_remap
from mgear.core import utils

logger = logging.getLogger(__name__)

PRECISION = 6

# Deformer order modes
ORDER_CURRENT = "current"
ORDER_FRONT = "front"
ORDER_LAST = "last"
ORDER_MODES = (ORDER_CURRENT, ORDER_FRONT, ORDER_LAST)

# Placement kind: directly after a given deformer
AFTER = "after"

# Incoming connections that belong to the deformer geometry pipeline
GEOMETRY_PIPELINE_ATTRS = (
    "inputGeometry",
    "groupId",
    "originalGeometry",
    "weightList",
    "message",
)


# =============================================================================
# HELPERS
# =============================================================================


def get_parent(node):
    """Return the long name of the parent of a DAG node.

    Args:
        node (str): DAG node name.

    Returns:
        str: Parent long name, or None if parented to the world.
    """
    parents = cmds.listRelatives(node, parent=True, fullPath=True)
    return parents[0] if parents else None


def entry_label(entry):
    """Return the short label of a stored ``{transform, shape}`` entry.

    Args:
        entry (dict): Stored entry with ``transform`` and/or ``shape``.

    Returns:
        str: Leaf name of the transform, else of the shape.
    """
    return node_remap.leaf_name(entry.get("transform") or entry.get("shape") or "")


def round_list(values, precision=PRECISION):
    """Round a list of floats.

    Args:
        values (list): Float values.
        precision (int, optional): Number of decimals.

    Returns:
        list: Rounded values.
    """
    return [round(v, precision) for v in values]


# =============================================================================
# ORDER MODES
# =============================================================================


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


def resolve_order(stored, name, order=None):
    """Return the deformer order mode to use for one deformer.

    Args:
        stored (str): Mode stored in the file. None means ``"current"``.
        name (str): Stored deformer name, used for dict overrides.
        order (str or dict, optional): Override. None uses the stored
            mode, a str applies to every deformer and a ``{name: mode}``
            dict applies per deformer.

    Returns:
        str: The order mode.

    Raises:
        ValueError: If the resolved mode is not valid.
    """
    stored = stored or ORDER_CURRENT
    if order is None:
        mode = stored
    elif isinstance(order, dict):
        mode = order.get(name) or stored
    else:
        mode = order
    validate_order(mode)
    return mode


# =============================================================================
# FILES
# =============================================================================


def file_path(path, ext):
    """Return a file path with an extension when it has none.

    Args:
        path (str): File path.
        ext (str): Extension with the dot, e.g. ``".lat"``.

    Returns:
        str: The path, with ``ext`` added if it had no extension.
    """
    if not os.path.splitext(path)[1]:
        path += ext
    return path


def write_file(path, file_type, schema_version, items_key, items):
    """Write a deformer configuration file.

    Args:
        path (str): Output file path.
        file_type (str): File type id, checked by :func:`load_file`.
        schema_version (int): Schema version of the items.
        items_key (str): Key of the items list, e.g. ``"lattices"``.
        items (list): Serializable deformer configurations.

    Returns:
        dict: The written data.
    """
    data = {
        "type": file_type,
        "schema_version": schema_version,
        "maya_version": cmds.about(version=True),
        "scene": cmds.file(query=True, sceneName=True),
        items_key: items,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return data


def load_file(path, file_type, label=None):
    """Load and validate a deformer configuration file.

    Args:
        path (str): File path.
        file_type (str): Expected file type id.
        label (str, optional): Readable file kind for the error message.

    Returns:
        dict: The loaded data.

    Raises:
        ValueError: If the file is not of the expected type.
    """
    with open(path, "r") as f:
        data = json.load(f)
    if not isinstance(data, dict) or data.get("type") != file_type:
        raise ValueError("Not a {} file: {}".format(label or file_type, path))
    return data


# =============================================================================
# FORMAT
# =============================================================================


class DeformerFormat(object):
    """A deformer IO file format and its export / import pipeline.

    A tool describes its format and passes two functions:

    * ``collect(node, order)`` returns the configuration of one deformer
      (raise RuntimeError to skip it with a warning).
    * ``build(config, replace, order)`` rebuilds one deformer and returns
      its name, or None when nothing was built.

    Each configuration stores the deformer name in
    ``config[name_key]["name"]`` and its order mode in ``config["order"]``.

    Example:
        >>> FORMAT = DeformerFormat(
        ...     file_type="cluster_config",
        ...     ext=".clu",
        ...     items_key="clusters",
        ...     name_key="cluster",
        ...     label="cluster",
        ...     collect=get_cluster_config,
        ...     build=build_cluster,
        ...     log=logger,
        ... )
        >>> FORMAT.export(["cluster1"], "C:/tmp/clusters")
    """

    def __init__(
        self,
        file_type,
        ext,
        items_key,
        name_key,
        label,
        collect,
        build,
        schema_version=1,
        log=None,
    ):
        """Initialize the format.

        Args:
            file_type (str): File type id stored and checked in the file.
            ext (str): File extension with the dot, e.g. ``".lat"``.
            items_key (str): Key of the deformer list, e.g. ``"lattices"``.
            name_key (str): Key of the ``{"name": ...}`` dict in each
                configuration, e.g. ``"ffd"``.
            label (str): Singular readable name, e.g. ``"lattice"``.
            collect (callable): ``collect(node, order)``.
            build (callable): ``build(config, replace, order)``.
            schema_version (int, optional): Schema version written.
            log (logging.Logger, optional): Tool logger for the export /
                import summaries.
        """
        self.file_type = file_type
        self.ext = ext
        self.items_key = items_key
        self.name_key = name_key
        self.label = label
        self.collect = collect
        self.build = build
        self.schema_version = schema_version
        self.log = log or logger

    def name(self, config):
        """Return the stored deformer name of a configuration.

        Args:
            config (dict): Deformer configuration.

        Returns:
            str: Name.
        """
        return config[self.name_key]["name"]

    def file_path(self, path):
        """Return a file path with the format extension when it has none.

        Args:
            path (str): File path.

        Returns:
            str: The path.
        """
        return file_path(path, self.ext)

    def resolve_order(self, config, order=None):
        """Return the deformer order mode to use for a configuration.

        Args:
            config (dict): Deformer configuration.
            order (str or dict, optional): Override, see
                :func:`resolve_order`.

        Returns:
            str: The order mode.

        Raises:
            ValueError: If the resolved mode is not valid.
        """
        return resolve_order(config.get("order"), self.name(config), order)

    def load(self, path):
        """Load and validate a file of this format.

        Args:
            path (str): File path.

        Returns:
            dict: The loaded data.

        Raises:
            ValueError: If the file is not of this format.
        """
        return load_file(path, self.file_type, self.label + " configuration")

    def items(self, data):
        """Return the deformer configurations of loaded file data.

        Args:
            data (dict): File data.

        Returns:
            list: Configurations.
        """
        return data.get(self.items_key, [])

    def export(self, nodes, path, order=ORDER_CURRENT):
        """Export deformers to a file.

        The format extension is added when the path has none. Deformers
        whose ``collect`` raises RuntimeError are skipped with a warning.

        Args:
            nodes (list): Deformer names.
            path (str): Output file path.
            order (str, optional): Deformer order mode stored for every
                deformer: ``"current"``, ``"front"`` or ``"last"``.

        Returns:
            dict: The exported data.

        Raises:
            ValueError: If the order mode is not valid.
        """
        validate_order(order)
        path = self.file_path(path)
        label = "Exporting {}s".format(self.label)
        configs = []
        with utils.main_progress_bar(label, len(nodes)) as step:
            for node in nodes:
                step("{} {}".format(label, node))
                try:
                    configs.append(self.collect(node, order))
                    self.log.info("Collected '%s'.", node)
                except RuntimeError as err:
                    self.log.warning(str(err))
        data = write_file(
            path, self.file_type, self.schema_version, self.items_key, configs
        )
        self.log.info("Exported %d %s(s) to: %s", len(configs), self.label, path)
        return data

    def import_file(self, path, names=None, replace=True, order=None):
        """Import deformers from a file in one undo step.

        Args:
            path (str): File path.
            names (list, optional): Stored names to import. All if None.
            replace (bool, optional): Passed to ``build``.
            order (str or dict, optional): Order override, see
                :func:`resolve_order`.

        Returns:
            list: Created deformer names.

        Raises:
            ValueError: If the file is not valid or an order mode is
                unknown. Every mode is checked before anything is built.
        """
        configs = [
            c for c in self.items(self.load(path)) if not names or self.name(c) in names
        ]
        for config in configs:
            self.resolve_order(config, order)

        label = "Importing {}s".format(self.label)
        created = []
        with utils.undo_chunk(label):
            with utils.main_progress_bar(label, len(configs)) as step:
                for config in configs:
                    step("{} {}".format(label, self.name(config)))
                    result = self.build(config, replace, order)
                    if result:
                        created.append(result)
        self.log.info("Imported %d %s(s).", len(created), self.label)
        return created


# =============================================================================
# GEOMETRY DATA
# =============================================================================


def get_geometry_data(deformer_node, precision=PRECISION):
    """Collect the per-geometry data of a deformer.

    Args:
        deformer_node (str): Deformer name.
        precision (int, optional): Number of decimals for the weights.

    Returns:
        list: One dict per geometry with ``index``, ``transform``,
            ``shape``, ``point_count``, ``component_tag_expression``,
            ``weights`` (sparse) and ``deformer_stack``.
    """
    geometry = []
    for index, shape in deformer.get_deformer_geometry(deformer_node):
        weights = deformer.get_deformer_weights(deformer_node, index, shape=shape)
        geometry.append(
            {
                "index": index,
                "transform": get_parent(shape),
                "shape": shape,
                "point_count": utils.get_point_count(shape),
                "component_tag_expression": deformer.get_component_tag_expression(
                    deformer_node, index
                ),
                "weights": {i: round(w, precision) for i, w in weights.items()},
                "deformer_stack": deformer.get_deformer_stack(shape),
            }
        )
    return geometry


def resolve_shape(entry):
    """Find the scene shape for a stored ``{shape, transform}`` entry.

    The shape is found by name, tolerant to hierarchy and namespace
    changes. If it is missing, the first visible shape of the transform
    is used.

    Args:
        entry (dict): Stored entry with ``shape`` and/or ``transform``.

    Returns:
        str: Shape long name, or None.
    """
    shape = node_remap.find_node(entry.get("shape"))
    if shape and cmds.nodeType(shape) != "transform":
        return shape
    transform = shape or node_remap.find_node(entry.get("transform"))
    if not transform:
        return None
    shapes = cmds.listRelatives(
        transform, shapes=True, noIntermediate=True, fullPath=True
    )
    return shapes[0] if shapes else None


def resolve_geometry(entries, members=None):
    """Find the scene geometry for stored geometry entries.

    Args:
        entries (list): Stored geometry entries.
        members (list, optional): Stored legacy deformer set members.
            When some resolve, they are the deformer targets.

    Returns:
        tuple: ``(targets, geo_map)``. Targets are the shapes or
            components to deform. geo_map maps resolved shape long names
            to their stored entries.
    """
    geo_map = {}
    for entry in entries:
        shape = resolve_shape(entry)
        if not shape:
            logger.warning("Geometry '%s' not found, skipped.", entry_label(entry))
            continue
        geo_map[shape] = entry

    # Legacy set members: one entry per component range, resolve each
    # node once
    resolved = []
    nodes = {}
    for member in members or []:
        node, _, comp = member.partition(".")
        if node not in nodes:
            nodes[node] = node_remap.find_node(node)
        if nodes[node]:
            resolved.append(nodes[node] + ("." + comp if comp else ""))
    return resolved or list(geo_map), geo_map


def apply_geometry_data(deformer_node, geo_map):
    """Restore weights and component tag expressions on a new deformer.

    Weights are written sparsely: only the stored (non default) values.

    Args:
        deformer_node (str): Deformer name, freshly created.
        geo_map (dict): ``{shape: stored entry}`` from
            :func:`resolve_geometry`.
    """
    for index, shape in deformer.get_deformer_geometry(deformer_node):
        entry = geo_map.get(shape)
        if not entry:
            continue

        tag_expr = entry.get("component_tag_expression")
        if (
            tag_expr
            and tag_expr != "*"
            and deformer.set_component_tag_expression(deformer_node, index, tag_expr)
        ):
            logger.info(
                "'%s' uses component tag expression '%s'. Make sure the "
                "tag exists on the rebuilt geometry.",
                node_remap.leaf_name(shape),
                tag_expr,
            )

        if entry.get("weights"):
            deformer.set_deformer_weights(
                deformer_node,
                index,
                entry["weights"],
                point_count=entry.get("point_count"),
                shape=shape,
                sparse=True,
            )


# =============================================================================
# PLACEMENT
# =============================================================================


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


def _current_position(name, entry, shape):
    """Resolve where a deformer goes in a geometry stack for ``current``.

    Args:
        name (str): Stored deformer name.
        entry (dict): Stored geometry entry.
        shape (str): Scene shape, before the deformer is created.

    Returns:
        tuple: ``(ORDER_FRONT, None)``, ``(ORDER_LAST, None)`` or
            ``(AFTER, deformer_name)``.
    """
    stack = entry.get("deformer_stack") or []
    position = None
    for i, stored in enumerate(stack):
        if node_remap.short_name(stored) == node_remap.short_name(name):
            position = i
            break

    if position is not None:
        below = stack[position + 1 :]
        if not below:
            return ORDER_FRONT, None
        current = deformer.get_deformer_stack(shape)
        for stored in below:
            match = _match_name(stored, current)
            if match:
                return AFTER, match

    logger.info(
        "Stored deformer order of '%s' on '%s' not found, added last.",
        name,
        node_remap.leaf_name(shape),
    )
    return ORDER_LAST, None


def resolve_placements(name, geo_map, mode):
    """Resolve, before creation, where a deformer goes on each geometry.

    Args:
        name (str): Stored deformer name.
        geo_map (dict): ``{shape: stored entry}``.
        mode (str): Order mode.

    Returns:
        tuple: ``(positions, front_of_chain)``. positions maps each shape
            to ``(kind, after)``. front_of_chain is True when every shape
            resolves to the front, so the deformer can be created with
            ``frontOfChain``.
    """
    positions = {}
    for shape, entry in geo_map.items():
        if mode == ORDER_CURRENT:
            positions[shape] = _current_position(name, entry, shape)
        else:
            positions[shape] = (mode, None)
    front_of_chain = all(p[0] == ORDER_FRONT for p in positions.values())
    return positions, front_of_chain


def apply_placements(deformer_node, positions):
    """Move a new deformer to its resolved position on each geometry.

    The deformer must have been created last (or at the front of the
    chain when every position is front).

    Args:
        deformer_node (str): Deformer name.
        positions (dict): ``{shape: (kind, after)}`` from
            :func:`resolve_placements`.
    """
    for shape, (kind, after) in positions.items():
        try:
            if kind == ORDER_FRONT:
                deformer.move_deformer(deformer_node, shape)
            elif kind == AFTER:
                deformer.move_deformer(deformer_node, shape, after=after)
        except (RuntimeError, ValueError) as err:
            logger.warning(
                "Can't reorder '%s' on '%s': %s",
                deformer_node,
                node_remap.leaf_name(shape),
                err,
            )


# =============================================================================
# ATTRIBUTES AND CONNECTIONS
# =============================================================================


def set_attr(plug, value):
    """Set an attribute value when the plug exists and is settable.

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


def get_attrs(node, attrs):
    """Read attribute values, skipping attributes the node doesn't have.

    Args:
        node (str): Node name, or an element plug such as
            ``pw1.drivers[0]`` to read the children of a multi element.
        attrs (list): Attribute names.

    Returns:
        dict: ``{attr: value}``.
    """
    values = {}
    for attr in attrs:
        plug = "{}.{}".format(node, attr)
        if cmds.objExists(plug):
            values[attr] = cmds.getAttr(plug)
    return values


def set_attrs(node, values, attrs=None, skip=None):
    """Set attribute values on the settable plugs of a node.

    Args:
        node (str): Node name, or an element plug such as
            ``pw1.drivers[0]``.
        values (dict): ``{attr: value}``.
        attrs (list, optional): Attribute order. Only these attributes
            are set. Defaults to the keys of ``values``.
        skip (set, optional): Attributes to leave untouched, e.g. the
            ones restored as connections.

    Stored attributes the node doesn't have (e.g. a file from a newer
    Maya version) are skipped and listed in one info message.
    """
    skip = skip or ()
    missing = []
    for attr in attrs or list(values):
        if attr not in values or attr in skip:
            continue
        plug = "{}.{}".format(node, attr)
        if not cmds.objExists(plug):
            missing.append(attr)
        elif cmds.getAttr(plug, settable=True):
            cmds.setAttr(plug, values[attr])
    if missing:
        logger.info(
            "'%s' has no %s, skipped.",
            node_remap.leaf_name(node),
            ", ".join(missing),
        )


def get_input_connections(node, exclude=GEOMETRY_PIPELINE_ATTRS):
    """Return the incoming connections of a node.

    Args:
        node (str): Node name.
        exclude (tuple, optional): Attribute names to skip when any part
            of the destination plug path uses them. Defaults to the
            deformer geometry pipeline.

    Returns:
        list: ``{"source": "<node long name>.<plug>", "destination":
            "<attr path>"}`` dicts, source plugs with multi indices. When
            the source is a shape, ``source_parent`` stores its transform
            so the shape can be found again if it was renamed.
    """
    pairs = (
        cmds.listConnections(
            node, source=True, destination=False, plugs=True, connections=True
        )
        or []
    )
    connections = []
    for destination in pairs[::2]:
        attr = destination.split(".", 1)[1]
        parts = [p.split("[")[0] for p in attr.split(".")]
        if any(p in exclude for p in parts):
            continue
        # connectionInfo keeps the multi index (worldMesh[0])
        source = cmds.connectionInfo(destination, sourceFromDestination=True)
        if not source:
            continue
        src_node, _, src_plug = source.partition(".")
        src_node = (cmds.ls(src_node, long=True) or [src_node])[0]
        connection = {
            "source": "{}.{}".format(src_node, src_plug),
            "destination": attr,
        }
        if cmds.objectType(src_node, isAType="shape"):
            connection["source_parent"] = get_parent(src_node)
        if connection not in connections:
            connections.append(connection)
    return connections


def _remap_destination(attr, remap):
    """Rewrite the multi index of a destination attribute path.

    Args:
        attr (str): Destination attribute path, e.g. ``drivers[3].x``.
        remap (dict): ``{multi: {old_index: new_index}}``, or None.

    Returns:
        str: The remapped path, or None if its element is not mapped.
    """
    match = re.match(r"(\w+)\[(\d+)\](.*)$", attr)
    if not remap or not match or match.group(1) not in remap:
        return attr
    index = remap[match.group(1)].get(int(match.group(2)))
    if index is None:
        return None
    return "{}[{}]{}".format(match.group(1), index, match.group(3))


def restore_input_connections(node, connections, remap=None):
    """Reconnect stored incoming connections to a node.

    Source nodes are found by name, tolerant to hierarchy and namespace
    changes; a source shape is also found through its stored parent
    transform. Missing sources and failed connections are logged.

    Args:
        node (str): Node name.
        connections (list): Dicts from :func:`get_input_connections`.
        remap (dict, optional): ``{multi: {old_index: new_index}}`` for
            destinations under a multi attribute whose indices changed on
            rebuild, e.g. ``{"drivers": {3: 0}}``. Connections to an
            index missing from the mapping (the element is gone) are
            skipped with an info message.

    Returns:
        set: Destination attributes that are connected (remapped).
    """
    connected = set()
    for connection in connections:
        src_node, _, src_plug = connection["source"].partition(".")
        attr = _remap_destination(connection["destination"], remap)
        if attr is None:
            logger.info(
                "'%s' is not rebuilt, its connection is skipped.",
                connection["destination"],
            )
            continue
        destination = "{}.{}".format(node, attr)
        if connection.get("source_parent"):
            found = resolve_shape(
                {"shape": src_node, "transform": connection["source_parent"]}
            )
        else:
            found = node_remap.find_node(src_node)
        if not found:
            logger.warning(
                "Source '%s' not found, '%s' keeps its stored value.",
                node_remap.leaf_name(connection["source"]),
                attr,
            )
            continue
        source = "{}.{}".format(found, src_plug)
        try:
            if not cmds.isConnected(source, destination):
                cmds.connectAttr(source, destination, force=True)
        except RuntimeError as err:
            logger.warning("Can't connect '%s' to '%s': %s", source, destination, err)
            continue
        connected.add(attr)
    return connected
