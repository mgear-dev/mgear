"""Blendshape utilities and tools.

Functions for querying, creating, connecting, and managing
blendShape and morph deformer nodes. Also provides constants
and helpers for working with blendShape target attributes.
"""

import re

from maya import cmds

import mgear.pymaya as pm
from mgear.core import deformer

# =============================================================================
# BLENDSHAPE TARGET CONSTANTS
# =============================================================================

BS_TARGET_ITEM_ATTR = (
    "{}.inputTarget[0].inputTargetGroup[{}].inputTargetItem"
)


def bs_target_weight(item_index):
    """Convert a blendShape target item index to a weight value.

    Maya stores blendShape in-between targets using item
    indices where 6000 = weight 1.0, 5500 = weight 0.5,
    5000 = weight 0.0, etc.

    Args:
        item_index (int): The target item index (e.g. 6000).

    Returns:
        float: The corresponding weight value.
    """
    return float((item_index - 5000) / 1000.0)


# =============================================================================
# BLENDSHAPE QUERIES
# =============================================================================


def getDeformerNode(obj, lv=2, dtype="blendShape"):
    """Get a deformer node of the specified type from an object.

    Args:
        obj (str or PyNode): The object to query.
        lv (int, optional): History traversal depth.
        dtype (str, optional): Deformer node type.

    Returns:
        PyNode: The deformer node, or None if not found.
    """
    if isinstance(obj, str):
        obj = pm.PyNode(obj)

    try:
        if pm.nodeType(obj.getShape()) in [
            "mesh",
            "nurbsSurface",
            "nurbsCurve",
        ]:
            deformer_node = pm.listHistory(
                obj.getShape(), type=dtype, lv=lv
            )[0]
    except Exception:
        deformer_node = None

    return deformer_node


def getBlendShape(obj, lv=2):
    """Get the blendShape node of an object.

    Args:
        obj (str or PyNode): The object with the blendshape node.
        lv (int, optional): History traversal depth.

    Returns:
        PyNode: The blendshape node, or None if not found.
    """
    return getDeformerNode(obj, lv=lv)


def getMorph(obj, lv=2):
    """Get the morph node of an object.

    Args:
        obj (str or PyNode): The object with the morph node.
        lv (int, optional): History traversal depth.

    Returns:
        PyNode: The morph node, or None if not found.
    """
    return getDeformerNode(obj, lv=lv, dtype="morph")


# =============================================================================
# BLENDSHAPE / MORPH CONNECTIONS
# =============================================================================


def connectWithBlendshape(mesh, bst, wgt=1.0, ffoc=False):
    """Connect two geometries using a blendShape node.

    Args:
        mesh (str or PyNode): The object to apply the
            blendshape target to.
        bst (str or PyNode): The blendshape target geometry.
        wgt (float, optional): Target weight value.
        ffoc (bool, optional): Force Front of Chain. Moves
            the blendshape node after creation.

    Returns:
        PyNode: The blendshape node.
    """
    if isinstance(mesh, str):
        mesh = pm.PyNode(mesh)
    if isinstance(bst, str):
        bst = pm.PyNode(bst)
    bsnode = getBlendShape(mesh)
    if bsnode:
        wc = pm.blendShape(bsnode, q=True, wc=True)
        pm.blendShape(
            bsnode, edit=True, t=(mesh, wc, bst, 1.0)
        )
        bsnode.attr(bst.name()).set(wgt)
        bs = bsnode
    else:
        if ffoc:
            foc = False
        else:
            foc = True
        bs = pm.blendShape(
            bst,
            mesh,
            name="_".join([mesh.name(), "blendShape"]),
            foc=foc,
            w=[(0, 1.0)],
        )
        if ffoc:
            blendshape_foc(mesh)

    return bs


def connectWithMorph(mesh, bst, wgt=1.0, ffoc=True):
    """Connect two geometries using a morph node.

    Args:
        mesh (str or PyNode): The object to apply the morph to.
        bst (str or PyNode): The morph target geometry.
        wgt (float, optional): Envelope weight.
        ffoc (bool, optional): Force Front of Chain. Moves
            the morph node after creation.

    Returns:
        PyNode: The morph deformer node.
    """
    if isinstance(mesh, str):
        mesh = pm.PyNode(mesh)
    if isinstance(bst, str):
        bst = pm.PyNode(bst)
    morph_deformer = pm.deformer(mesh, type="morph")[0]
    pm.rename(morph_deformer, mesh.name() + "_morph")
    # relative mode
    morph_deformer.morphMode.set(1)
    pm.connectAttr(
        bst.worldMesh[0],
        morph_deformer.morphTarget[0],
        force=True,
    )
    if ffoc:
        morph_foc(mesh, morph_deformer)
    return morph_deformer


# =============================================================================
# DEFORMER REORDERING
# =============================================================================


def blendshape_foc(deformed_obj):
    """Move existing blendShape node to the front of chain.

    Args:
        deformed_obj (PyNode): Object with deformation history
            including a blendShape node.
    """
    meshShape = deformed_obj.getShape()

    history = pm.listHistory(
        meshShape,
        gl=True,
        pdo=True,
        lf=True,
        f=False,
        il=2,
    )
    history = deformer.filter_deformers(history)
    blendShape_node = None
    deformers = []
    for h in history:
        object_type = pm.objectType(h)
        if object_type == "blendShape":
            blendShape_node = h
        else:
            deformers.append(h)
    if blendShape_node:
        deformers.append(blendShape_node)
        deformers.append(meshShape)
        pm.reorderDeformers(*deformers)


def morph_foc(deformed_obj, morph_deformer):
    """Move existing morph node to the front of chain.

    Args:
        deformed_obj (PyNode): Object with deformation history
            including a morph node.
        morph_deformer (PyNode): The morph deformer to move.
    """
    meshShape = deformed_obj.getShape()

    history = pm.listHistory(
        meshShape,
        gl=True,
        pdo=True,
        lf=True,
        f=False,
        il=2,
    )
    history = deformer.filter_deformers(history)

    # remove the first one that is the new morph
    history_check = history[1:]

    # Insert the new element before the blendShape
    # or at the end of the list
    insert_index = len(history_check)
    start_slice = -2
    for i, element in enumerate(history_check):
        if isinstance(element, pm.nodetypes.BlendShape):
            insert_index = i
            start_slice = -3
            break

    history_check.insert(insert_index, morph_deformer)

    result = history_check[start_slice:]
    if len(result) > 1:
        result.append(meshShape)
        pm.reorderDeformers(*result)


# =============================================================================
# BLENDSHAPE ATTRIBUTE HELPERS
# =============================================================================
# TODO: refactor rigbits.evaluation_partition to use these shared
# helpers instead of its local copies.


def _has_live_target(attr_name, target_items):
    """Check if any target item has a live geometry input.

    A live target has an active mesh connection on
    ``inputGeomTarget`` which cannot be captured via the
    connect/disconnect bake pattern.

    Args:
        attr_name (str): The inputTargetItem base attribute
            (e.g. ``"bs.inputTarget[0].inputTargetGroup[0]
            .inputTargetItem"``).
        target_items (list): List of target item indices.

    Returns:
        bool: True if any target has a live connection.
    """
    for t_item in target_items:
        geom_attr = "{}[{}].inputGeomTarget".format(
            attr_name, t_item
        )
        conns = cmds.listConnections(
            geom_attr, destination=False
        )
        if conns:
            return True
    return False


def _unlock_and_disconnect_attr(attr):
    """Temporarily unlock and disconnect an attribute.

    Returns a state dict for restoration via ``_restore_attr``.

    Args:
        attr (str): Full attribute path
            (e.g. ``"blendShape1.weight[0]"``).

    Returns:
        dict: Saved state with keys ``"locked"`` (bool) and
            ``"connection"`` (str or None).
    """
    state = {"locked": False, "connection": None}

    if cmds.getAttr(attr, lock=True):
        state["locked"] = True
        cmds.setAttr(attr, lock=False)

    conns = cmds.listConnections(
        attr, source=True, destination=False, plugs=True
    )
    if conns:
        state["connection"] = conns[0]
        cmds.disconnectAttr(conns[0], attr)

    return state


def _restore_attr(attr, state):
    """Restore attribute lock and connection state.

    Args:
        attr (str): Full attribute path.
        state (dict): State dict from
            ``_unlock_and_disconnect_attr``.
    """
    if state["connection"]:
        try:
            cmds.connectAttr(
                state["connection"], attr, force=True
            )
        except RuntimeError:
            cmds.warning(
                "Failed to restore connection: {} -> {}".format(
                    state["connection"], attr
                )
            )

    if state["locked"]:
        cmds.setAttr(attr, lock=True)


# =============================================================================
# BLENDSHAPE TRANSFER
# =============================================================================
# TODO: refactor rigbits.evaluation_partition to use
# transfer_blendshapes instead of its local _transfer_bs_to_partition.


def transfer_blendshapes(
    sources, target, bs_node_name=None, reconnect=True
):
    """Transfer blendshapes from multiple sources into one node.

    Creates a single blendShape node on the target mesh and
    stacks all targets from all source meshes into it.  Uses a
    wrap-based capture approach: for each source, a temporary
    duplicate of the target is wrapped to the source, then each
    blendshape target is baked via connect/disconnect.

    Args:
        sources (list): List of source mesh transform names.
            Each may have zero or more blendShape nodes.
        target (str): Target mesh transform name.
        bs_node_name (str, optional): Name for the created
            blendShape node.  Defaults to ``"<target>_BS"``.
        reconnect (bool, optional): If True, replicate input
            connections from source BS weights to the new BS
            node.  Defaults to True.

    Returns:
        str: The created blendShape node name, or None if no
            targets were transferred.
    """
    # Collect source BS nodes
    source_bs_map = {}
    for src in sources:
        bs_nodes = deformer.get_deformers(src, "blendShape")
        if bs_nodes:
            source_bs_map[src] = bs_nodes

    if not source_bs_map:
        return None

    # Create empty blendShape at front of chain
    target_short = target.split("|")[-1].split(":")[-1]
    node_name = bs_node_name or "{}_BS".format(target_short)
    new_bs = cmds.deformer(
        target,
        type="blendShape",
        name=node_name,
        frontOfChain=True,
    )[0]

    next_idx = 0
    alias_set = set()
    index_map = {}

    for src, bs_nodes in source_bs_map.items():
        saved_env = deformer.disable_deformer_envelopes(
            src, exclude_types={"blendShape"}
        )

        try:
            next_idx = _transfer_source(
                src,
                target,
                bs_nodes,
                new_bs,
                next_idx,
                alias_set,
                index_map,
            )
        finally:
            deformer.restore_deformer_envelopes(saved_env)

    # No targets transferred
    if next_idx == 0:
        cmds.delete(new_bs)
        return None

    # NOTE: Zero-delta targets are now skipped during capture
    # (inside _transfer_bs_node) so no post-cleanup needed.
    # _purge_stale_bs_nodes disabled — can delete nodes
    # referenced by SHAPES combo system.

    # Reconnect input connections
    if reconnect:
        _reconnect_bs_inputs(index_map, new_bs)

    return new_bs


def _transfer_source(
    source,
    target,
    bs_nodes,
    new_bs,
    next_idx,
    alias_set,
    index_map,
):
    """Transfer all BS targets from one source mesh.

    Args:
        source (str): Source mesh name.
        target (str): Target mesh name.
        bs_nodes (list): BlendShape nodes on the source.
        new_bs (str): Destination blendShape node on target.
        next_idx (int): Next available target index.
        alias_set (set): Used alias names (mutated in place).
        index_map (dict): Source-to-dest index map (mutated).

    Returns:
        int: Updated next_idx after adding targets.
    """
    temp_name = "{}_xfer_temp".format(
        target.split("|")[-1].split(":")[-1]
    )
    temp_dup = cmds.duplicate(
        target,
        returnRootsOnly=True,
        inputConnections=False,
        name=temp_name,
    )[0]

    wrap_node, base_dup = deformer.create_wrap_deformer(
        temp_dup, source, use_base_duplicate=True
    )

    temp_shapes = cmds.listRelatives(
        temp_dup, shapes=True, type="mesh", noIntermediate=True
    )
    if not temp_shapes:
        cmds.delete(temp_dup)
        return next_idx
    temp_shape = temp_shapes[0]

    source_short = (
        source.split("|")[-1].split(":")[-1]
    )

    try:
        for src_bs in bs_nodes:
            next_idx = _transfer_bs_node(
                src_bs,
                new_bs,
                temp_shape,
                target,
                next_idx,
                alias_set,
                index_map,
                source_short,
            )
    finally:
        if wrap_node and cmds.objExists(wrap_node):
            cmds.delete(wrap_node)
        if base_dup and cmds.objExists(base_dup):
            cmds.delete(base_dup)
        if cmds.objExists(temp_dup):
            cmds.delete(temp_dup)

    return next_idx


def _transfer_bs_node(
    src_bs,
    new_bs,
    temp_shape,
    target_mesh,
    next_idx,
    alias_set,
    index_map,
    source_short,
):
    """Transfer targets from a single BS node.

    Args:
        src_bs (str): Source blendShape node.
        new_bs (str): Destination blendShape node.
        temp_shape (str): Temp wrapped shape for capture.
        target_mesh (str): Target mesh transform name.
        next_idx (int): Next available target index.
        alias_set (set): Used alias names (mutated).
        index_map (dict): Source-to-dest map (mutated).
        source_short (str): Source mesh short name for
            collision prefixing.

    Returns:
        int: Updated next_idx.
    """
    targets_idx = cmds.getAttr(
        "{}.weight".format(src_bs), multiIndices=True
    )
    if not targets_idx:
        return next_idx

    # Build alias lookup from all aliases on the node.
    # cmds.aliasAttr returns flat list: [alias, attr, ...]
    alias_lookup = {}
    raw_aliases = cmds.aliasAttr(src_bs, query=True) or []
    for i in range(0, len(raw_aliases), 2):
        alias_lookup[raw_aliases[i + 1]] = raw_aliases[i]

    # Pre-compute base positions once for zero-delta checks
    base_pos = _get_base_positions(target_mesh)

    # Phase 1: Capture all targets via wrap bake.
    # Process one at a time — disconnect, set, capture,
    # reconnect immediately to preserve combo networks.
    pending_aliases = []

    for src_idx in targets_idx:
        attr_name = BS_TARGET_ITEM_ATTR.format(
            src_bs, src_idx
        )
        target_items = cmds.getAttr(
            attr_name, multiIndices=True
        )
        if not target_items:
            continue

        weight_key = "weight[{}]".format(src_idx)
        target_name = alias_lookup.get(weight_key)

        if _has_live_target(attr_name, target_items):
            cmds.warning(
                "Skipping live target: {}".format(
                    target_name
                )
            )
            continue

        dst_idx = next_idx
        next_idx += 1
        index_map[(src_bs, src_idx)] = dst_idx

        weight_attr = "{}.weight[{}]".format(
            src_bs, src_idx
        )

        # Snapshot and disconnect this weight only
        was_locked = cmds.getAttr(weight_attr, lock=True)
        if was_locked:
            cmds.setAttr(weight_attr, lock=False)

        source_plug = None
        conns = cmds.listConnections(
            weight_attr,
            source=True,
            destination=False,
            plugs=True,
        )
        if conns:
            source_plug = conns[0]
            try:
                cmds.disconnectAttr(source_plug, weight_attr)
            except RuntimeError:
                cmds.warning(
                    "Could not disconnect: {} -> {}".format(
                        source_plug, weight_attr
                    )
                )

        try:
            for t_item in target_items:
                weight = bs_target_weight(t_item)
                cmds.setAttr(weight_attr, weight)

                dest_attr = (
                    "{}.inputTarget[0]"
                    ".inputTargetGroup[{}]"
                    ".inputTargetItem[{}]"
                    ".inputGeomTarget"
                ).format(new_bs, dst_idx, t_item)

                cmds.connectAttr(
                    "{}.outMesh".format(temp_shape),
                    dest_attr,
                    force=True,
                )
                cmds.disconnectAttr(
                    "{}.outMesh".format(temp_shape),
                    dest_attr,
                )

            cmds.setAttr(weight_attr, 0)
        finally:
            if source_plug:
                try:
                    cmds.connectAttr(
                        source_plug, weight_attr, force=True
                    )
                except RuntimeError:
                    cmds.warning(
                        "Failed to restore: {} -> {}".format(
                            source_plug, weight_attr
                        )
                    )
            if was_locked:
                cmds.setAttr(weight_attr, lock=True)

        # Check if this target actually deforms the mesh.
        # If not, remove it now (avoids ghost weight entries
        # from post-cleanup removeMultiInstance).
        if not _target_has_delta(
            target_mesh, new_bs, dst_idx, base_pos
        ):
            tgt_grp = (
                "{}.inputTarget[0]"
                ".inputTargetGroup[{}]"
            ).format(new_bs, dst_idx)
            cmds.removeMultiInstance(tgt_grp, b=True)
            cmds.removeMultiInstance(
                "{}.weight[{}]".format(new_bs, dst_idx),
                b=True,
            )
            del index_map[(src_bs, src_idx)]
            next_idx -= 1
            continue

        # Queue alias for phase 2
        if target_name:
            final_name = _resolve_alias(
                target_name,
                alias_set,
                source_short,
                dst_idx,
            )
        else:
            final_name = "{}_{}".format(
                source_short, src_idx
            )
            final_name = _resolve_alias(
                final_name,
                alias_set,
                source_short,
                dst_idx,
            )
        alias_set.add(final_name)
        pending_aliases.append((dst_idx, final_name))

    # Phase 2: Set all aliases after all connections are done.
    # This avoids any interference from the connect/disconnect
    # operations on alias resolution.
    for dst_idx, final_name in pending_aliases:
        dst_weight = "{}.weight[{}]".format(new_bs, dst_idx)
        cmds.setAttr(dst_weight, 0)
        try:
            cmds.aliasAttr(final_name, dst_weight)
        except RuntimeError:
            cmds.warning(
                "Failed to set alias '{}' on {}".format(
                    final_name, dst_weight
                )
            )

    # Phase 3: Verify all aliases were set
    verify_aliases = cmds.aliasAttr(new_bs, query=True) or []
    set_aliases = set()
    for i in range(0, len(verify_aliases), 2):
        set_aliases.add(verify_aliases[i])
    for dst_idx, final_name in pending_aliases:
        if final_name not in set_aliases:
            cmds.warning(
                "Alias '{}' missing on {}.weight[{}]".format(
                    final_name, new_bs, dst_idx
                )
            )

    return next_idx




def _resolve_alias(name, alias_set, source_short, dst_idx):
    """Resolve alias name collisions.

    Args:
        name (str): Original alias name.
        alias_set (set): Already-used alias names.
        source_short (str): Source mesh short name for prefix.
        dst_idx (int): Destination index for final fallback.

    Returns:
        str: Unique alias name.
    """
    if name not in alias_set:
        return name

    prefixed = "{}_{}".format(source_short, name)
    if prefixed not in alias_set:
        return prefixed

    return "{}_{}".format(prefixed, dst_idx)


def _get_base_positions(mesh):
    """Get the base vertex positions of a mesh.

    Args:
        mesh (str): Mesh transform name.

    Returns:
        list: Flat list of [x, y, z, x, y, z, ...] floats.
    """
    num_verts = cmds.polyEvaluate(mesh, vertex=True)
    return cmds.xform(
        "{}.vtx[0:{}]".format(mesh, num_verts - 1),
        query=True,
        worldSpace=True,
        translation=True,
    )


def _target_has_delta(
    mesh, bs_node, idx, base_pos, threshold=0.0001
):
    """Check if a BS target produces visible deformation.

    Args:
        mesh (str): Mesh transform name.
        bs_node (str): BlendShape node name.
        idx (int): Target weight index.
        base_pos (list): Pre-computed base vertex positions
            from ``_get_base_positions``.
        threshold (float): Min vertex displacement.

    Returns:
        bool: True if the target deforms the mesh.
    """
    weight_attr = "{}.weight[{}]".format(bs_node, idx)
    num_verts = cmds.polyEvaluate(mesh, vertex=True)

    cmds.setAttr(weight_attr, 1.0)
    deformed_pos = cmds.xform(
        "{}.vtx[0:{}]".format(mesh, num_verts - 1),
        query=True,
        worldSpace=True,
        translation=True,
    )
    cmds.setAttr(weight_attr, 0.0)

    threshold_sq = threshold * threshold
    for i in range(0, len(base_pos), 3):
        dx = deformed_pos[i] - base_pos[i]
        dy = deformed_pos[i + 1] - base_pos[i + 1]
        dz = deformed_pos[i + 2] - base_pos[i + 2]
        if dx * dx + dy * dy + dz * dz >= threshold_sq:
            return True
    return False



def get_mult_node_type():
    """Get the correct multiply node type for this Maya version.

    Maya 2026+ uses ``multDL``, older versions use
    ``multDoubleLinear``.

    Returns:
        str: Node type name.
    """
    version = int(cmds.about(version=True))
    if version >= 2026:
        return "multDL"
    return "multDoubleLinear"


def _reconnect_bs_inputs(index_map, new_bs):
    """Replicate input connections from source to new BS.

    For simple connections (animCurves, direct drivers),
    connects the same driver to the new BS weight.
    For combo connections (multDL networks where weights
    on the same BS drive other weights), rebuilds an
    equivalent multiply network on the new BS.

    Args:
        index_map (dict): Maps ``(src_bs, src_idx)`` to
            ``dst_idx`` on the new blendShape node.
        new_bs (str): The destination blendShape node.
    """
    mult_type = get_mult_node_type()

    # Build reverse map: src_bs → {src_idx: dst_idx}
    bs_idx_map = {}
    for (src_bs, src_idx), dst_idx in index_map.items():
        if src_bs not in bs_idx_map:
            bs_idx_map[src_bs] = {}
        bs_idx_map[src_bs][src_idx] = dst_idx

    combos = []

    for (src_bs, src_idx), dst_idx in index_map.items():
        src_attr = "{}.weight[{}]".format(src_bs, src_idx)
        dst_attr = "{}.weight[{}]".format(new_bs, dst_idx)

        conns = cmds.listConnections(
            src_attr,
            source=True,
            destination=False,
            plugs=True,
        )
        if not conns:
            val = cmds.getAttr(src_attr)
            cmds.setAttr(dst_attr, val)
            continue

        src_node = conns[0].split(".")[0]
        src_type = cmds.nodeType(src_node)

        if src_type in (mult_type, "multDoubleLinear", "multDL"):
            # Combo target — defer to phase 2
            combo_sources = trace_combo_inputs(
                src_node, src_bs, mult_type
            )
            combos.append(
                (src_bs, dst_idx, combo_sources)
            )
        else:
            # Simple driver (animCurve, etc.) — connect
            try:
                cmds.connectAttr(
                    conns[0], dst_attr, force=True
                )
            except RuntimeError:
                cmds.warning(
                    "Could not connect {} -> {}".format(
                        conns[0], dst_attr
                    )
                )

    # Phase 2: Build combo networks on the new BS
    for src_bs, dst_combo_idx, combo_sources in combos:
        src_to_dst = bs_idx_map.get(src_bs, {})
        dst_inputs = []
        for src_weight_idx in combo_sources:
            mapped = src_to_dst.get(src_weight_idx)
            if mapped is not None:
                dst_inputs.append(mapped)

        if dst_inputs:
            build_combo_network(
                new_bs, dst_combo_idx, dst_inputs, mult_type
            )


def trace_combo_inputs(master_mult, src_bs, mult_type):
    """Trace which source BS weights feed a combo network.

    Walks upstream through the multDL chain to find the
    blendShape weight attributes that are the ultimate
    inputs to the combo.

    Args:
        master_mult (str): The master multDL node.
        src_bs (str): The source blendShape node name.
        mult_type (str): The multDL node type name.

    Returns:
        list: Source weight indices that drive this combo.
    """
    source_indices = []
    visited = set()
    nodes_to_check = [master_mult]

    while nodes_to_check:
        node = nodes_to_check.pop(0)
        if node in visited:
            continue
        visited.add(node)

        # Check all source connections on this node
        conns = cmds.listConnections(
            node,
            source=True,
            destination=False,
            plugs=True,
            connections=True,
        ) or []

        for i in range(0, len(conns), 2):
            dst_plug = conns[i]
            src_plug = conns[i + 1]
            src_node = src_plug.split(".")[0]
            src_node_type = cmds.nodeType(src_node)

            if src_node == src_bs:
                # Direct connection from a BS weight
                idx = parse_weight_index(src_plug)
                if idx is not None:
                    source_indices.append(idx)
            elif src_node_type in (
                mult_type,
                "multDoubleLinear",
                "multDL",
            ):
                # Another mult node — keep walking upstream
                nodes_to_check.append(src_node)

    return source_indices


def parse_weight_index(plug):
    """Extract weight index from a blendShape weight plug.

    Handles both indexed form (``node.weight[5]``) and alias
    form (``node.L_wide``).  When an alias is used, queries
    the node's alias list to resolve the actual index.

    Args:
        plug (str): Full plug path.

    Returns:
        int: The weight index, or None if not parseable.
    """
    # Try indexed form first: "node.weight[5]"
    match = re.search(r"weight\[(\d+)\]", plug)
    if match:
        return int(match.group(1))

    # Alias form: "node.L_wide" — resolve via aliasAttr
    parts = plug.split(".", 1)
    if len(parts) != 2:
        return None

    node = parts[0]
    attr_name = parts[1]

    aliases = cmds.aliasAttr(node, query=True) or []
    for i in range(0, len(aliases), 2):
        if aliases[i] == attr_name:
            idx_match = re.search(
                r"weight\[(\d+)\]", aliases[i + 1]
            )
            if idx_match:
                return int(idx_match.group(1))

    return None


def build_combo_network(
    new_bs, dst_combo_idx, input_dst_indices, mult_type
):
    """Build a multiply network for a combo target.

    Creates ``multDL`` nodes that multiply the input
    weights together and connect the result to the combo
    weight on the new blendShape node.

    Args:
        new_bs (str): Destination blendShape node.
        dst_combo_idx (int): Destination weight index for
            the combo target.
        input_dst_indices (list): Destination weight indices
            of the input weights that drive this combo.
        mult_type (str): Node type (``multDL`` or
            ``multDoubleLinear``).
    """
    dst_combo_attr = "{}.weight[{}]".format(
        new_bs, dst_combo_idx
    )
    combo_alias = cmds.aliasAttr(dst_combo_attr, query=True)
    base_name = combo_alias or "combo_{}".format(dst_combo_idx)

    if len(input_dst_indices) == 1:
        # Single input combo — pass through (input2=1.0
        # so output = input1 * 1.0 = input1)
        mult = cmds.createNode(
            mult_type, name="{}_mult".format(base_name)
        )
        cmds.setAttr("{}.input2".format(mult), 1.0)
        cmds.connectAttr(
            "{}.weight[{}]".format(
                new_bs, input_dst_indices[0]
            ),
            "{}.input1".format(mult),
        )
        cmds.connectAttr(
            "{}.output".format(mult),
            dst_combo_attr,
            force=True,
        )

    elif len(input_dst_indices) == 2:
        # Two-input combo: A * B
        mult = cmds.createNode(
            mult_type, name="{}_mult".format(base_name)
        )
        cmds.connectAttr(
            "{}.weight[{}]".format(
                new_bs, input_dst_indices[0]
            ),
            "{}.input1".format(mult),
        )
        cmds.connectAttr(
            "{}.weight[{}]".format(
                new_bs, input_dst_indices[1]
            ),
            "{}.input2".format(mult),
        )
        cmds.connectAttr(
            "{}.output".format(mult),
            dst_combo_attr,
            force=True,
        )

    else:
        # N-input combo: chain multiplies
        # A * B → mult1, mult1 * C → mult2, etc.
        prev_output = "{}.weight[{}]".format(
            new_bs, input_dst_indices[0]
        )
        for i, dst_idx in enumerate(input_dst_indices[1:]):
            mult = cmds.createNode(
                mult_type,
                name="{}_{}_mult".format(base_name, i),
            )
            cmds.connectAttr(
                prev_output, "{}.input1".format(mult)
            )
            cmds.connectAttr(
                "{}.weight[{}]".format(new_bs, dst_idx),
                "{}.input2".format(mult),
            )
            prev_output = "{}.output".format(mult)

        cmds.connectAttr(
            prev_output, dst_combo_attr, force=True
        )
