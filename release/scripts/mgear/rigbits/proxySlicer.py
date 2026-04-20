"""Rigbits proxy mesh slicer.

Creates proxy geometry for a skinned object by splitting its faces
into groups based on dominant skinCluster influence weights.  Uses
OpenMaya2 for batch weight queries (5-10x faster than per-vertex
cmds.skinPercent on production meshes).
"""

import datetime
import logging

import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as oma2
import maya.cmds as cmds

import mgear
from mgear.core import applyop
from mgear.core import node

log = logging.getLogger("mgear.rigbits.proxySlicer")

TRANSFORM_ATTRS = (
    "translateX",
    "translateY",
    "translateZ",
    "rotateX",
    "rotateY",
    "rotateZ",
    "scaleX",
    "scaleY",
    "scaleZ",
)


# =================================================================
# HELPERS
# =================================================================


def _get_dag_path(name):
    """Get an MDagPath from a node name.

    Args:
        name (str): Maya node name.

    Returns:
        om2.MDagPath: The DAG path.
    """
    sel = om2.MSelectionList()
    sel.add(name)
    return sel.getDagPath(0)


def _get_depend_node(name):
    """Get an MObject from a node name.

    Args:
        name (str): Maya node name.

    Returns:
        om2.MObject: The dependency node.
    """
    sel = om2.MSelectionList()
    sel.add(name)
    return sel.getDependNode(0)


def _get_skin_weights(shape_path, skin_cluster_name):
    """Batch-query all skin weights using OpenMaya2.

    Args:
        shape_path (str): Full path to the mesh shape node.
        skin_cluster_name (str): Name of the skinCluster node.

    Returns:
        tuple: (weights, num_influences, influence_names) where
            weights is a flat list of length num_verts *
            num_influences.
    """
    dag = _get_dag_path(shape_path)
    skin_obj = _get_depend_node(skin_cluster_name)
    skin_fn = oma2.MFnSkinCluster(skin_obj)

    # Get influence names in weight-array order
    inf_dag_paths = skin_fn.influenceObjects()
    inf_names = [p.partialPathName() for p in inf_dag_paths]
    num_inf = len(inf_names)

    # Build all-vertex component
    mesh_fn = om2.MFnMesh(dag)
    num_verts = mesh_fn.numVertices
    comp_fn = om2.MFnSingleIndexedComponent()
    vert_comp = comp_fn.create(om2.MFn.kMeshVertComponent)
    comp_fn.setCompleteData(num_verts)

    # Single API call for all weights
    weights, _ = skin_fn.getWeights(dag, vert_comp)

    return weights, num_inf, inf_names


def _get_face_vertex_map(shape_path):
    """Get face-to-vertex mapping using OpenMaya2.

    Args:
        shape_path (str): Full path to the mesh shape node.

    Returns:
        tuple: (vert_counts, vert_indices) from MFnMesh.getVertices().
    """
    dag = _get_dag_path(shape_path)
    mesh_fn = om2.MFnMesh(dag)
    return mesh_fn.getVertices()


def _group_faces_by_influence(
    n_faces, weights, num_inf, vert_counts, vert_indices
):
    """Group faces by their dominant skin influence.

    For each face, sums the weight vectors of all its vertices
    and assigns the face to the influence with the highest sum.

    Args:
        n_faces (int): Total number of faces.
        weights (MDoubleArray): Flat weight array.
        num_inf (int): Number of influences.
        vert_counts (MIntArray): Vertex count per face.
        vert_indices (MIntArray): Flat vertex index array.

    Returns:
        list: List of lists, one per influence, containing
            face indices assigned to that influence.
    """
    face_groups = [[] for _ in range(num_inf)]
    vi_offset = 0

    for face_idx in range(n_faces):
        n_verts = vert_counts[face_idx]

        # Sum weights across all vertices of this face
        sums = [0.0] * num_inf
        for v in range(n_verts):
            vtx = vert_indices[vi_offset + v]
            w_offset = vtx * num_inf
            for inf in range(num_inf):
                sums[inf] += weights[w_offset + inf]

        vi_offset += n_verts

        # Find dominant influence
        max_val = -1.0
        max_idx = 0
        for inf in range(num_inf):
            if sums[inf] > max_val:
                max_val = sums[inf]
                max_idx = inf
        face_groups[max_idx].append(face_idx)

        if face_idx % 10000 == 0 and face_idx > 0:
            log.info(
                "Grouping faces: %d / %d", face_idx, n_faces
            )

    return face_groups


def _save_lock_state(node_name):
    """Save the lock state of transform attributes.

    Args:
        node_name (str): Transform node name.

    Returns:
        dict: Attribute name to lock state mapping.
    """
    return {
        attr: cmds.getAttr(
            "{}.{}".format(node_name, attr), lock=True
        )
        for attr in TRANSFORM_ATTRS
    }


def _unlock_transforms(node_name):
    """Unlock all transform attributes on a node.

    Args:
        node_name (str): Transform node name.
    """
    for attr in TRANSFORM_ATTRS:
        cmds.setAttr(
            "{}.{}".format(node_name, attr), lock=False
        )


def _restore_locks(node_name, lock_state):
    """Re-lock transform attributes based on saved state.

    Args:
        node_name (str): Transform node name.
        lock_state (dict): Saved lock state from _save_lock_state.
    """
    for attr, locked in lock_state.items():
        if locked:
            cmds.setAttr(
                "{}.{}".format(node_name, attr), lock=True
            )


def _match_world_transform(source, target):
    """Match target's world transform to source.

    Args:
        source (str): Source transform name.
        target (str): Target transform name.
    """
    m = cmds.xform(source, query=True, worldSpace=True, matrix=True)
    cmds.xform(target, worldSpace=True, matrix=m)


# =================================================================
# MAIN
# =================================================================


def slice(parent=False, oSel=None, *args):
    """Create proxy geometry from skinned objects.

    Splits each mesh into pieces based on dominant skinCluster
    influence per face.  Each piece is either parented directly
    under its influence joint or placed under a ProxyGeo group
    with a matrix constraint.

    Supports multiple selection.  If ``oSel`` is a list, all
    meshes are processed.  If None, uses the current selection.

    Args:
        parent (bool): If True, parent proxies under their
            influence joints.  If False, keep under ProxyGeo
            group with world-space matrix constraints.
        oSel (str or list): Name(s) of the object(s) to
            process.  If None, uses the current selection.
    """
    start_time = datetime.datetime.now()

    # Build mesh list from argument or selection
    if oSel:
        meshes = [oSel] if isinstance(oSel, str) else list(oSel)
    else:
        meshes = cmds.ls(selection=True, long=True)

    if not meshes:
        cmds.warning("未选择任何对象。")
        return

    for mesh in meshes:
        _slice_single(mesh, parent)

    elapsed = datetime.datetime.now() - start_time
    log.info(
        "切片 %d 个网格完成 [ %s ]", len(meshes), str(elapsed)
    )


def _slice_single(oSel, parent=False):
    """Slice a single skinned mesh into proxy pieces.

    Args:
        oSel (str): Mesh transform name.
        parent (bool): Parent mode flag.
    """
    log.info("Processing: %s", oSel)

    # Get shape and skinCluster via history (works even when
    # other deformers sit between skin and shape)
    shapes = cmds.listRelatives(
        oSel, shapes=True, fullPath=True, type="mesh"
    )
    if not shapes:
        cmds.warning(
            "'{}' 未找到网格形状，跳过".format(oSel)
        )
        return
    shape = shapes[0]

    skin_clusters = cmds.ls(
        cmds.listHistory(oSel) or [], type="skinCluster"
    )
    if not skin_clusters:
        cmds.warning(
            "'{}' 未找到皮肤簇，跳过".format(oSel)
        )
        return
    skin_name = skin_clusters[0]

    n_faces = cmds.polyEvaluate(oSel, face=True)

    # Batch query weights and face topology via OpenMaya2
    weights, num_inf, inf_names = _get_skin_weights(
        shape, skin_name
    )
    # Convert MDoubleArray to list for faster Python indexing
    weights = list(weights)
    vert_counts, vert_indices = _get_face_vertex_map(shape)

    log.info(
        "Mesh: %d faces, %d influences", n_faces, num_inf
    )

    # Group faces by dominant influence
    face_groups = _group_faces_by_influence(
        n_faces, weights, num_inf, vert_counts, vert_indices
    )

    # Save original lock state before slicing
    original_locks = _save_lock_state(oSel)

    # Create parent group for world-space mode
    parent_grp = None
    if not parent:
        if cmds.objExists("ProxyGeo"):
            parent_grp = "ProxyGeo"
        else:
            parent_grp = cmds.createNode(
                "transform", name="ProxyGeo"
            )

    if cmds.objExists("rig_proxyGeo_grp"):
        proxy_set = "rig_proxyGeo_grp"
    else:
        proxy_set = cmds.sets(
            empty=True, name="rig_proxyGeo_grp"
        )

    # Process each face group
    for idx, bone_faces in enumerate(face_groups):
        if not bone_faces:
            continue

        proxy_name = "{}_Proxy".format(inf_names[idx])
        dup = cmds.duplicate(
            oSel, returnRootsOnly=True, name=proxy_name
        )
        new_obj = dup[0]

        # Unlock transforms for operations
        _unlock_transforms(new_obj)

        # Delete faces NOT in this group (set-based)
        keep = set(bone_faces)
        faces_to_del = [
            "{}.f[{}]".format(new_obj, i)
            for i in range(n_faces)
            if i not in keep
        ]
        cmds.delete(faces_to_del)

        if parent:
            cmds.parent(new_obj, inf_names[idx])
            # Re-lock attributes that were locked on original
            _restore_locks(new_obj, original_locks)
        else:
            cmds.parent(new_obj, parent_grp)

            # Transfer shape to a transform matched to the
            # influence, then constrain via matrix nodes.
            proxy_shapes = cmds.listRelatives(
                new_obj, shapes=True, fullPath=True
            )
            if proxy_shapes:
                # Reparent shape under a fresh transform at
                # the influence position
                dummy = cmds.duplicate(
                    new_obj, returnRootsOnly=True
                )[0]
                old_shapes = cmds.listRelatives(
                    new_obj, shapes=True, fullPath=True
                )
                if old_shapes:
                    cmds.delete(old_shapes)

                _match_world_transform(inf_names[idx], new_obj)

                dummy_shapes = cmds.listRelatives(
                    dummy, shapes=True, fullPath=True
                )
                if dummy_shapes:
                    cmds.parent(
                        dummy_shapes[0],
                        new_obj,
                        shape=True,
                        relative=True,
                    )
                cmds.delete(dummy)

                new_shape = cmds.listRelatives(
                    new_obj, shapes=True, fullPath=True
                )
                if new_shape:
                    cmds.rename(
                        new_shape[0],
                        "{}_offset".format(new_obj),
                    )

            # Matrix constraint: influence → proxy
            mulmat_node = applyop.gear_mulmatrix_op(
                "{}.worldMatrix".format(inf_names[idx]),
                "{}.parentInverseMatrix".format(new_obj),
            )
            dm_node = node.createDecomposeMatrixNode(
                "{}.output".format(mulmat_node)
            )
            cmds.connectAttr(
                "{}.outputTranslate".format(dm_node),
                "{}.translate".format(new_obj),
            )
            cmds.connectAttr(
                "{}.outputRotate".format(dm_node),
                "{}.rotate".format(new_obj),
            )
            cmds.connectAttr(
                "{}.outputScale".format(dm_node),
                "{}.scale".format(new_obj),
            )
            # Don't re-lock — attributes are driven by
            # matrix constraint connections

        log.info("Created proxy: %s", proxy_name)
        cmds.sets(new_obj, addElement=proxy_set)
