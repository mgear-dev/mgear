"""Blendshape utilities and tools.

Functions for querying, creating, connecting, and managing
blendShape and morph deformer nodes. Also provides constants
and helpers for working with blendShape target attributes.
"""

from maya import cmds

import mgear.pymaya as pm
from mgear.core import deformer

from mgear.vendor.Qt.six import string_types

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
    if isinstance(obj, string_types):
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
    if isinstance(mesh, string_types):
        mesh = pm.PyNode(mesh)
    if isinstance(bst, string_types):
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
    if isinstance(mesh, string_types):
        mesh = pm.PyNode(mesh)
    if isinstance(bst, string_types):
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
