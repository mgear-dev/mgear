"""
Given a universal mesh, record the placements of guide nodes as it relative to
universal mesh. And then repoisition guides to that relative position should
the universal mesh change from character to character.

from mgear.shifter import relativeGuidePlacement
reload(relativeGuidePlacement)

Execute the following chunk to record initial placement ----------------------
relativeGuidePlacement.exportGuidePlacement(filepath="Y:/tmp/exampleFile.json",
                                            skip_strings=["hair"])


Load new universal guide mesh with new proportions

Execute the following lines to move the guides to their new position ---------
relativeGuidePlacement.importGuidePlacement(filepath="Y:/tmp/exampleFile.json")

Attributes:
    GUIDE_ROOT (str): name of the root guide node
    SKIP_CONTAINS (list): nodes to skip if they contain the string
    SKIP_CRAWL_NODES (list): nodes to skip crawling hierarchy
    SKIP_NODETYPES (list): skip the query of certain node types
    SKIP_PLACEMENT_NODES (TYPE): nodes to skip updating their positions
    SKIP_SUFFIX (list): skip if node ends with
    UNIVERSAL_MESH_NAME (str): default name of the universal mesh
"""
# python
import json
import math

# dcc
import maya.cmds as mc
import mgear.pymaya as pm
import maya.OpenMaya as om
import maya.api.OpenMaya as om2

# mgear
from mgear.core import utils
from mgear.core import vector
from mgear.core import transform
from mgear.core import meshNavigation

from mgear.shifter._rgp_accel import HAS_ACCEL
if HAS_ACCEL:
    from mgear.shifter._rgp_accel import record_primary
    from mgear.shifter._rgp_accel import record_mirror
    from mgear.shifter._rgp_accel import reposition_all_guides


# constants -------------------------------------------------------------------

# Designate the root of the hierarchy to crawl
GUIDE_ROOT = "guide"


# Nodes to avoid checking the hierarchy
DEFAULT_SKIP_CRAWL_NODES = ("controllers_org",
                            "spineUI_C0_root",
                            "faceUI_C0_root",
                            "legUI_R0_root",
                            "armUI_L0_root",
                            "legUI_L0_root",
                            "armUI_R0_root")

# nodes that will not have their positions updated
DEFAULT_SKIP_PLACEMENT_NODES = ("controllers_org",
                                "global_C0_root",
                                "spineUI_C0_root",
                                "faceUI_C0_root",
                                "legUI_R0_root",
                                "armUI_L0_root",
                                "legUI_L0_root",
                                "armUI_R0_root")

# nodes that will update position only, preserving orientation
DEFAULT_SKIP_ORIENTATION_NODES = ()


try:
    SKIP_CRAWL_NODES
    SKIP_PLACEMENT_NODES
    SKIP_ORIENTATION_NODES
except NameError:
    SKIP_CRAWL_NODES = list(DEFAULT_SKIP_CRAWL_NODES)
    SKIP_PLACEMENT_NODES = list(DEFAULT_SKIP_PLACEMENT_NODES)
    SKIP_ORIENTATION_NODES = list(DEFAULT_SKIP_ORIENTATION_NODES)


# skip the node if it even contains the characters in the list
# eg SKIP_CONTAINS = ["hair"]
SKIP_CONTAINS = []

# Avoid nodes of a specified suffix
SKIP_SUFFIX = ["sizeRef", "crv", "crvRef", "blade"]

# Types of nodes to avoid
SKIP_NODETYPES = ["aimConstraint", "pointConstraint", "parentConstraint"]

UNIVERSAL_MESH_NAME = "skin_geo_setup"

# Number of nearby vertices to sample per guide node for multi-vertex mode
DEFAULT_SAMPLE_COUNT = 32


# C++ acceleration helpers ---------------------------------------------------

def _extract_mesh_data(mesh_name):
    """Bulk-extract mesh data using maya.api.OpenMaya (OM2).

    Extracts vertex positions, face topology, and per-face normals
    in a single pass. Returns flat lists suitable for passing to C++.

    Args:
        mesh_name (str): Name of the mesh node or shape.

    Returns:
        tuple: (points, face_normals, face_vert_counts,
                face_vert_indices, num_verts) where all are flat lists.
    """
    sel = om2.MSelectionList()
    sel.add(mesh_name)
    dag = sel.getDagPath(0)
    fn_mesh = om2.MFnMesh(dag)

    # Vertex positions (flat N*3)
    raw_points = fn_mesh.getPoints(om2.MSpace.kWorld)
    num_verts = len(raw_points)
    points = []
    for i in range(num_verts):
        p = raw_points[i]
        points.append(p.x)
        points.append(p.y)
        points.append(p.z)

    # Face topology
    face_vert_counts_arr, face_vert_indices_arr = fn_mesh.getVertices()
    face_vert_counts = list(face_vert_counts_arr)
    face_vert_indices = list(face_vert_indices_arr)

    # Per-face normals (flat F*3)
    num_faces = fn_mesh.numPolygons
    face_normals = []
    for f in range(num_faces):
        n = fn_mesh.getPolygonNormal(f, om2.MSpace.kWorld)
        face_normals.append(n.x)
        face_normals.append(n.y)
        face_normals.append(n.z)

    return (points, face_normals, face_vert_counts,
            face_vert_indices, num_verts)


def _get_seed_face_verts(mesh_name, positions):
    """Get seed polygon vertices for each position via getClosestPoint.

    For each position, finds the closest polygon on the mesh and returns
    that polygon's vertex indices as seed vertices for BFS flood-fill.

    Args:
        mesh_name (str): Name of the mesh node or shape.
        positions (list): Flat list of N*3 world positions.

    Returns:
        tuple: (seed_vert_ids, seed_offsets) where seed_vert_ids is a
            flat list of vertex indices and seed_offsets[i] is the start
            index for position i (len = num_positions + 1).
    """
    sel = om2.MSelectionList()
    sel.add(mesh_name)
    dag = sel.getDagPath(0)
    fn_mesh = om2.MFnMesh(dag)

    num_positions = len(positions) // 3
    seed_vert_ids = []
    seed_offsets = [0]

    for i in range(num_positions):
        pt = om2.MPoint(positions[i * 3],
                        positions[i * 3 + 1],
                        positions[i * 3 + 2])
        _, face_id = fn_mesh.getClosestPoint(pt, om2.MSpace.kWorld)
        face_verts = fn_mesh.getPolygonVertices(face_id)
        seed_vert_ids.extend(face_verts)
        seed_offsets.append(len(seed_vert_ids))

    return seed_vert_ids, seed_offsets


def _mesh_shape_name(mesh_name):
    """Get the shape node name from a transform or shape name.

    Args:
        mesh_name (str): Transform or shape name.

    Returns:
        str: Shape node name.
    """
    if mc.objectType(mesh_name) == "transform":
        shapes = mc.listRelatives(mesh_name, shapes=True,
                                  noIntermediate=True) or []
        if shapes:
            return shapes[0]
    return mesh_name


# general functions -----------------------------------------------------------

def crawlHierarchy(parentNode,
                   ordered_hierarchy,
                   skip_crawl_nodes,
                   skip_strings=None):
    """recursive function to crawl a hierarchy of nodes to return decendents

    Args:
        parentNode (str): node to query
        ordered_hierarchy (str): list to continuesly pass itself
        skip_crawl_nodes (list): nodes to skip crawl
    """
    if not skip_strings:
        skip_strings = []
    for node in mc.listRelatives(parentNode, type="transform") or []:
        if node in skip_crawl_nodes or node in ordered_hierarchy:
            continue
        if node.endswith(tuple(SKIP_SUFFIX)):
            continue
        if mc.objectType(node) in SKIP_NODETYPES:
            continue
        if [True for skip_str in skip_strings
                if skip_str.lower() in node.lower()]:
            continue
        ordered_hierarchy.append(node)
        crawlHierarchy(node,
                       ordered_hierarchy,
                       skip_crawl_nodes,
                       skip_strings=skip_strings)


def getPostionFromLoop(vertList):
    """Get the center position from the list of edge ids provided

    Args:
        vertList (list): list of edge ids

    Returns:
        list: of translate XYZ, world space
    """
    bb = mc.exactWorldBoundingBox(vertList)
    pos = ((bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2)
    return pos


def getVertMatrix(closestVert):
    """create a matrix from the closestVert and the normals of the surrounding
    faces for later comparison

    Args:
        node (str): guide node to query
        closestVert (str): closest vert to guide

    Returns:
        list: of matrices
    """
    closestVert = pm.PyNode(closestVert)
    faces = closestVert.connectedFaces()
    normalVector = faces.getNormal("world")
    pm.select(faces)
    faces_str = mc.ls(sl=True, fl=True)
    pm.select(cl=True)
    face_pos = pm.dt.Vector(getPostionFromLoop(faces_str))
    normal_rot = getOrient([normalVector.x, normalVector.y, normalVector.z],
                           [0, 1, 0],
                           ro=0)
    orig_ref_matrix = pm.dt.TransformationMatrix()
    orig_ref_matrix.setTranslation(face_pos, pm.dt.Space.kWorld)
    orig_ref_matrix.setRotation(normal_rot)

    return orig_ref_matrix


def getMultiVertexReferenceMatrix(vertices):
    """Build a reference matrix from multiple vertices.

    Computes centroid position and averaged face normal from all
    sampled vertices to create a more stable reference frame than
    the single-vertex approach.

    Args:
        vertices (list): Of vertex PyNodes.

    Returns:
        pm.dt.TransformationMatrix: Reference matrix with centroid
            position and averaged normal orientation.
    """
    centroid = pm.dt.Vector(0, 0, 0)
    avg_normal = pm.dt.Vector(0, 0, 0)
    face_set = set()

    for vtx in vertices:
        centroid += vtx.getPosition(space="world")
        for face in vtx.connectedFaces():
            face_idx = face.index()
            if face_idx not in face_set:
                face_set.add(face_idx)
                avg_normal += face.getNormal(space="world")

    count = len(vertices)
    centroid /= count
    avg_normal.normalize()

    normal_rot = getOrient(
        [avg_normal.x, avg_normal.y, avg_normal.z],
        [0, 1, 0],
        ro=0,
    )
    ref_matrix = pm.dt.TransformationMatrix()
    ref_matrix.setTranslation(centroid, pm.dt.Space.kWorld)
    ref_matrix.setRotation(normal_rot)

    return ref_matrix


def getCentroidFromVertexNames(vertex_names):
    """Compute centroid position from a list of vertex name strings.

    Args:
        vertex_names (list): Of vertex name strings (e.g. "meshShape.vtx[5]").

    Returns:
        pm.dt.Vector: World-space centroid position.
    """
    centroid = pm.dt.Vector(0, 0, 0)
    for name in vertex_names:
        vtx = pm.PyNode(name)
        centroid += vtx.getPosition(space="world")
    centroid /= len(vertex_names)
    return centroid


def getOrient(normal, tangent, ro=0):
    """convert normal direction into euler rotations

    Args:
        normal (list): of nomel values
        ro (int, optional): rotate order

    Returns:
        list: of euler rotations
    """
    kRotateOrders = [om.MEulerRotation.kXYZ, om.MEulerRotation.kYZX,
                     om.MEulerRotation.kZXY, om.MEulerRotation.kXZY,
                     om.MEulerRotation.kYXZ, om.MEulerRotation.kZYX, ]
    cross = [normal[1] * tangent[2] - normal[2] * tangent[1],
             normal[2] * tangent[0] - normal[0] * tangent[2],
             normal[0] * tangent[1] - normal[1] * tangent[0]]
    tMatrix = normal + [0] + tangent + [0] + cross + [0, 0, 0, 0, 1]
    mMatrix = om.MMatrix()
    om.MScriptUtil.createMatrixFromList(tMatrix, mMatrix)
    tmMatrix = om.MTransformationMatrix(mMatrix)
    rotate = tmMatrix.eulerRotation().reorder(kRotateOrders[ro])
    RAD_to_DEG = (180 / math.pi)
    return [rotate[0] * RAD_to_DEG,
            rotate[1] * RAD_to_DEG,
            rotate[2] * RAD_to_DEG]


def getRepositionMatrix(node_matrix,
                        orig_ref_matrix,
                        mr_orig_ref_matrix,
                        closestVerts,
                        mr_closestVerts=None):
    """Get the delta matrix from the original position and multiply by the
    new vert position. Add the rotations from the face normals.

    Supports both legacy single-vertex format (closestVerts is a list of
    two vertex name strings) and multi-vertex format (closestVerts is a
    list of N vertex names with separate mr_closestVerts).

    Args:
        node_matrix (pm.dt.Matrix): Matrix of the guide.
        orig_ref_matrix (pm.dt.Matrix): Matrix from the original vert
            position.
        mr_orig_ref_matrix (pm.dt.Matrix): Mirror reference matrix.
        closestVerts (list): Vertex name strings for the primary
            reference. In legacy mode, index 0 is primary and index 1
            is mirror.
        mr_closestVerts (list, optional): Mirror vertex name strings.
            When provided, enables multi-vertex centroid mode.

    Returns:
        pm.dt.Matrix: Matrix of the new offset position, worldSpace.
    """
    if mr_closestVerts is not None:
        # Multi-vertex path: compute centroids from vertex lists
        current_pos = getCentroidFromVertexNames(closestVerts)
        mr_current_pos = getCentroidFromVertexNames(mr_closestVerts)
    else:
        # Legacy single-vertex path
        current_pos = pm.PyNode(closestVerts[0]).getPosition("world")
        mr_current_pos = pm.PyNode(closestVerts[1]).getPosition("world")

    current_length = vector.getDistance(current_pos, mr_current_pos)

    orig_length = vector.getDistance(orig_ref_matrix.translate,
                                     mr_orig_ref_matrix.translate)
    orig_center = vector.linearlyInterpolate(orig_ref_matrix.translate,
                                             mr_orig_ref_matrix.translate)
    orig_center_matrix = pm.dt.Matrix()
    orig_center_matrix = transform.setMatrixPosition(
        orig_center_matrix, orig_center)

    current_center = vector.linearlyInterpolate(current_pos, mr_current_pos)

    length_percentage = 1
    if current_length != 0 or orig_length != 0:
        length_percentage = current_length / orig_length
    refPosition_matrix = pm.dt.Matrix()
    refPosition_matrix = transform.setMatrixPosition(
        refPosition_matrix, current_center)
    deltaMatrix = node_matrix * orig_center_matrix.inverse()
    deltaMatrix = deltaMatrix * length_percentage
    deltaMatrix = transform.setMatrixScale(deltaMatrix)
    refPosition_matrix = deltaMatrix * refPosition_matrix

    return refPosition_matrix


def getRepositionMatrixSingleRef(node_matrix,
                                 orig_ref_matrix,
                                 mr_orig_ref_matrix,
                                 closestVerts):
    """Get the delta matrix from the original position and multiply by the
    new vert position. Add the rotations from the face normals.

    Args:
        node_matrix (pm.dt.Matrix): matrix of the guide
        orig_ref_matrix (pm.dt.Matrix): matrix from the original vert position
        closestVerts (str): name of the closest vert

    Returns:
        mmatrix: matrix of the new offset position, worldSpace
    """
    closestVerts = pm.PyNode(closestVerts[0])
    faces = closestVerts.connectedFaces()
    normalVector = faces.getNormal("world")
    pm.select(faces)
    faces_str = mc.ls(sl=True, fl=True)
    pm.select(cl=True)
    face_pos = pm.dt.Vector(getPostionFromLoop(faces_str))
    normal_rot = getOrient([normalVector.x, normalVector.y, normalVector.z],
                           [0, 1, 0],
                           ro=0)
    refPosition_matrix = pm.dt.TransformationMatrix()
    refPosition_matrix.setTranslation(face_pos, pm.dt.Space.kWorld)
    refPosition_matrix.setRotation(normal_rot)

    deltaMatrix = node_matrix * orig_ref_matrix.inverse()
    refPosition_matrix = deltaMatrix * refPosition_matrix

    return refPosition_matrix


@utils.viewport_off
@utils.one_undo
def getGuideRelativeDictionaryLegacy(mesh, guideOrder):
    """create a dictionary of guide:[[shape.vtx[int]], relativeMatrix]

    Args:
        mesh (string): name of the mesh
        guideOrder (list): the order to query the guide hierarchy

    Returns:
        dictionary: create a dictionary of guide:[[edgeIDs], relativeMatrix]
    """
    relativeGuide_dict = {}
    mesh = pm.PyNode(mesh)
    for guide in guideOrder:
        guide = pm.PyNode(guide)
        # slow function A
        clst_vert = meshNavigation.getClosestVertexFromTransform(mesh, guide)
        vertexIds = [clst_vert.name()]
        # slow function B
        orig_ref_matrix = getVertMatrix(clst_vert.name())
        #  --------------------------------------------------------------------
        a_mat = guide.getMatrix(worldSpace=True)

        mm = ((orig_ref_matrix - a_mat) * -1) + a_mat
        pos = mm[3][:3]

        mr_vert = meshNavigation.getClosestVertexFromTransform(mesh, pos)
        mr_orig_ref_matrix = getVertMatrix(mr_vert.name())
        vertexIds.append(mr_vert.name())

        node_matrix = guide.getMatrix(worldSpace=True)
        relativeGuide_dict[guide.name()] = [vertexIds,
                                            node_matrix.get(),
                                            orig_ref_matrix.get(),
                                            mr_orig_ref_matrix.get()]
    mc.select(cl=True)
    return relativeGuide_dict


@utils.viewport_off
@utils.one_undo
def yieldGuideRelativeDictionary(mesh, guideOrder, relativeGuide_dict,
                                  sample_count=None):
    """Create a dictionary of guide:[[shape.vtx[int]], relativeMatrix].

    When sample_count > 1, uses multi-vertex sampling for more stable
    reference positions. Falls back to single-vertex when sample_count
    is 1 or None.

    Uses C++ acceleration when available (HAS_ACCEL) and sample_count > 1
    for significantly faster bulk processing. Falls back to Python
    automatically when the C++ module is not built.

    Args:
        mesh (string): Name of the mesh.
        guideOrder (list): The order to query the guide hierarchy.
        relativeGuide_dict (dict): Dictionary to populate with results.
        sample_count (int, optional): Number of vertices to sample per
            guide. Defaults to DEFAULT_SAMPLE_COUNT.

    Returns:
        dictionary: guide:[[vertexIDs], matrices] via yield.
    """
    if sample_count is None:
        sample_count = DEFAULT_SAMPLE_COUNT

    mesh_name = str(mesh)
    shape_name = _mesh_shape_name(mesh_name)

    if HAS_ACCEL and sample_count > 1:
        # ---- C++ accelerated path ----
        yield from _yield_guide_relative_accel(
            shape_name, mesh_name, guideOrder, relativeGuide_dict,
            sample_count)
    else:
        # ---- Pure Python path ----
        yield from _yield_guide_relative_python(
            mesh, guideOrder, relativeGuide_dict, sample_count)


def _yield_guide_relative_accel(shape_name, mesh_name, guideOrder,
                                 relativeGuide_dict, sample_count):
    """C++ accelerated recording path.

    Extracts mesh data once via OM2, then delegates BFS + matrix
    construction to C++ in batch.

    Args:
        shape_name (str): Mesh shape node name.
        mesh_name (str): Mesh transform or shape name.
        guideOrder (list): Guide names to process.
        relativeGuide_dict (dict): Dictionary to populate.
        sample_count (int): Number of vertices to sample.
    """
    # 1. Bulk extract mesh data (single OM2 pass)
    (points, face_normals, face_vert_counts,
     face_vert_indices, num_verts) = _extract_mesh_data(shape_name)

    # 2. Gather guide positions and matrices
    guide_positions = []
    guide_matrices = []
    guide_names = []
    for guide_name in guideOrder:
        guide = pm.PyNode(guide_name)
        pos = guide.getTranslation(space="world")
        guide_positions.extend([pos.x, pos.y, pos.z])
        mat = guide.getMatrix(worldSpace=True)
        # Flatten nested 4x4 tuple to flat 16 doubles for C++
        for row in mat.get():
            guide_matrices.extend(row)
        guide_names.append(guide.name())

    # 3. Get seed polygon verts for each guide position (OM2)
    seed_vert_ids, seed_offsets = _get_seed_face_verts(
        shape_name, guide_positions)

    # 4. C++ record_primary: BFS + ref matrices + mirror positions
    primary_result = record_primary(
        guide_positions,
        guide_matrices,
        seed_vert_ids,
        seed_offsets,
        sample_count,
        points,
        face_normals,
        face_vert_counts,
        face_vert_indices,
        num_verts,
    )

    p_vert_ids = primary_result["vert_ids"]
    p_ref_matrices = primary_result["ref_matrices"]
    p_mirror_positions = primary_result["mirror_positions"]

    # 5. Get seed polygon verts for mirror positions (OM2)
    mr_seed_vert_ids, mr_seed_offsets = _get_seed_face_verts(
        shape_name, p_mirror_positions)

    # 6. C++ record_mirror: BFS + ref matrices for mirror side
    #    Pass mirror_positions so C++ uses the reflected guide position
    #    (not seed polygon centroid) as the distance reference for BFS.
    mirror_result = record_mirror(
        mr_seed_vert_ids,
        mr_seed_offsets,
        sample_count,
        points,
        face_normals,
        face_vert_counts,
        face_vert_indices,
        num_verts,
        p_mirror_positions,
    )

    mr_vert_ids = mirror_result["vert_ids"]
    mr_ref_matrices = mirror_result["ref_matrices"]

    # 7. Package results into relativeGuide_dict format
    guide_count = len(guide_names)
    for g in range(guide_count):
        # Vertex IDs as name strings (e.g. "meshShape.vtx[5]")
        vert_names = []
        for i in range(sample_count):
            vid = p_vert_ids[g * sample_count + i]
            vert_names.append("{}.vtx[{}]".format(shape_name, vid))

        mr_vert_names = []
        for i in range(sample_count):
            vid = mr_vert_ids[g * sample_count + i]
            mr_vert_names.append("{}.vtx[{}]".format(shape_name, vid))

        # Node matrix (flat 16 -> nested 4x4 list for JSON)
        node_mat_flat = guide_matrices[g * 16:(g + 1) * 16]
        node_mat_nested = [
            node_mat_flat[r * 4:(r + 1) * 4] for r in range(4)
        ]

        # Reference matrix (flat 16 -> nested 4x4)
        ref_mat_flat = p_ref_matrices[g * 16:(g + 1) * 16]
        ref_mat_nested = [
            ref_mat_flat[r * 4:(r + 1) * 4] for r in range(4)
        ]

        # Mirror reference matrix (flat 16 -> nested 4x4)
        mr_mat_flat = mr_ref_matrices[g * 16:(g + 1) * 16]
        mr_mat_nested = [
            mr_mat_flat[r * 4:(r + 1) * 4] for r in range(4)
        ]

        relativeGuide_dict[guide_names[g]] = [
            vert_names,
            node_mat_nested,
            ref_mat_nested,
            mr_mat_nested,
            mr_vert_names,
        ]
        yield relativeGuide_dict


def _yield_guide_relative_python(mesh, guideOrder, relativeGuide_dict,
                                  sample_count):
    """Pure Python recording path (fallback).

    Args:
        mesh (pm.PyNode): Mesh node.
        guideOrder (list): Guide names to process.
        relativeGuide_dict (dict): Dictionary to populate.
        sample_count (int): Number of vertices to sample.
    """
    for guide in guideOrder:
        guide = pm.PyNode(guide)

        if sample_count > 1:
            # Multi-vertex sampling path
            vertices = meshNavigation.getClosestNVerticesFromTransform(
                mesh, guide, count=sample_count
            )
            vertexIds = [v.name() for v in vertices]
            orig_ref_matrix = getMultiVertexReferenceMatrix(vertices)
            # Mirror reference: reflect guide through ref matrix
            a_mat = guide.getMatrix(worldSpace=True)
            ref_mat = pm.dt.Matrix(orig_ref_matrix)
            mm = pm.dt.Matrix(((ref_mat - a_mat) * -1) + a_mat)
            mr_pos = mm[3][:3]
            mr_vertices = meshNavigation.getClosestNVerticesFromTransform(
                mesh, mr_pos, count=sample_count
            )
            mr_vertexIds = [v.name() for v in mr_vertices]
            mr_orig_ref_matrix = getMultiVertexReferenceMatrix(mr_vertices)

            node_matrix = guide.getMatrix(worldSpace=True)
            relativeGuide_dict[guide.name()] = [
                vertexIds,
                node_matrix.get(),
                orig_ref_matrix.get(),
                mr_orig_ref_matrix.get(),
                mr_vertexIds,
            ]
        else:
            # Legacy single-vertex path
            clst_vert = meshNavigation.getClosestVertexFromTransform(
                mesh, guide
            )
            vertexIds = [clst_vert.name()]
            orig_ref_matrix = getVertMatrix(clst_vert.name())
            a_mat = guide.getMatrix(worldSpace=True)
            mm = ((orig_ref_matrix - a_mat) * -1) + a_mat
            pos = mm[3][:3]
            mr_vert = meshNavigation.getClosestVertexFromTransform(
                mesh, pos
            )
            mr_orig_ref_matrix = getVertMatrix(mr_vert.name())
            vertexIds.append(mr_vert.name())

            node_matrix = guide.getMatrix(worldSpace=True)
            relativeGuide_dict[guide.name()] = [
                vertexIds,
                node_matrix.get(),
                orig_ref_matrix.get(),
                mr_orig_ref_matrix.get(),
            ]
        yield relativeGuide_dict


@utils.viewport_off
@utils.one_undo
def getGuideRelativeDictionary(mesh, guideOrder, sample_count=None):
    """Create a dictionary of guide:[[shape.vtx[int]], relativeMatrix].

    Args:
        mesh (string): Name of the mesh.
        guideOrder (list): The order to query the guide hierarchy.
        sample_count (int, optional): Number of vertices to sample per
            guide. Defaults to DEFAULT_SAMPLE_COUNT.

    Returns:
        dict: guide:[[vertexIDs], matrices].
    """
    relativeGuide_dict = {}
    mesh = pm.PyNode(mesh)
    for result in yieldGuideRelativeDictionary(
            mesh, guideOrder, relativeGuide_dict,
            sample_count=sample_count):
        pass
    return relativeGuide_dict


@utils.viewport_off
@utils.one_undo
def updateGuidePlacementLegacy(guideOrder, guideDictionary,
                               reference_mesh=None,
                               skip_orientation_nodes=None):
    """update the guides based on new universal mesh, in the provided order

    Args:
        guideOrder (list): of the hierarchy to crawl
        guideDictionary (dictionary): dict of the guide:edge, matrix position
        reference_mesh (str, optional): Override mesh to use instead of the
            one embedded in the vertex ID strings. When ``None`` the
            original mesh name is used.
        skip_orientation_nodes (list, optional): Nodes that update position
            only, preserving their current orientation. When ``None``
            defaults to the module-level ``SKIP_ORIENTATION_NODES``.
    """
    if skip_orientation_nodes is None:
        skip_orientation_nodes = SKIP_ORIENTATION_NODES
    if reference_mesh is not None:
        _remap_mesh_in_guide_dict(guideDictionary, reference_mesh)
    for guide in guideOrder:
        if guide not in guideDictionary or not mc.objExists(guide):
            continue
        elif guide in SKIP_PLACEMENT_NODES:
            continue
        (vertexIds,
         node_matrix,
         orig_ref_matrix,
         mr_orig_ref_matrix) = guideDictionary[guide]

        guideNode = pm.PyNode(guide)
        repoMatrix = getRepositionMatrix(pm.dt.Matrix(node_matrix),
                                         pm.dt.Matrix(orig_ref_matrix),
                                         pm.dt.Matrix(mr_orig_ref_matrix),
                                         vertexIds)
        if guide in skip_orientation_nodes:
            pos = pm.dt.TransformationMatrix(
                repoMatrix).getTranslation("world")
            guideNode.setTranslation(pos, space="world")
        else:
            guideNode.setMatrix(repoMatrix, worldSpace=True, preserve=True)


@utils.viewport_off
@utils.one_undo
def yieldUpdateGuidePlacement(guideOrder, guideDictionary):
    """Update the guides based on new universal mesh, in the provided order.

    Automatically detects legacy (4-element) vs multi-vertex (5-element)
    data entries per guide. Uses C++ acceleration when available and all
    entries are multi-vertex format.

    Args:
        guideOrder (list): Of the hierarchy to crawl.
        guideDictionary (dict): Dict of the guide:edge, matrix position.
    """
    # Filter to valid guides
    valid_guides = []
    for guide in guideOrder:
        if guide not in guideDictionary or not mc.objExists(guide):
            continue
        if guide in SKIP_PLACEMENT_NODES:
            continue
        valid_guides.append(guide)

    if not valid_guides:
        return

    # Check if all entries are multi-vertex (5-element)
    all_multi = all(
        len(guideDictionary[g]) == 5 for g in valid_guides
    )

    if HAS_ACCEL and all_multi:
        yield from _yield_update_accel(valid_guides, guideDictionary)
    else:
        yield from _yield_update_python(valid_guides, guideDictionary)


def _yield_update_accel(valid_guides, guideDictionary):
    """C++ accelerated update/repositioning path.

    Extracts new mesh data once, batches all repositioning in C++.

    Args:
        valid_guides (list): Filtered guide names.
        guideDictionary (dict): Guide data dictionary.
    """
    guide_count = len(valid_guides)

    # Determine mesh name and sample_count from first entry
    first_entry = guideDictionary[valid_guides[0]]
    first_vert_name = first_entry[0][0]  # e.g. "meshShape.vtx[5]"
    mesh_name = first_vert_name.split(".vtx[")[0]
    sample_count = len(first_entry[0])

    shape_name = _mesh_shape_name(mesh_name)

    # Extract new mesh positions (single OM2 call)
    (new_points, _, _, _, _) = _extract_mesh_data(shape_name)

    # Collect all data into flat arrays for C++
    all_node_matrices = []
    all_ref_matrices = []
    all_mr_ref_matrices = []
    all_vert_ids = []
    all_mr_vert_ids = []

    for guide in valid_guides:
        (vertexIds, node_matrix, orig_ref_matrix,
         mr_orig_ref_matrix, mr_vertexIds) = guideDictionary[guide]

        # Flatten nested 4x4 matrix to 16 doubles
        for row in node_matrix:
            all_node_matrices.extend(row)
        for row in orig_ref_matrix:
            all_ref_matrices.extend(row)
        for row in mr_orig_ref_matrix:
            all_mr_ref_matrices.extend(row)

        # Extract vertex indices from name strings
        for vname in vertexIds:
            vid = int(vname.split("[")[1].rstrip("]"))
            all_vert_ids.append(vid)
        for vname in mr_vertexIds:
            vid = int(vname.split("[")[1].rstrip("]"))
            all_mr_vert_ids.append(vid)

    # C++ batch repositioning
    result_matrices = reposition_all_guides(
        all_node_matrices,
        all_ref_matrices,
        all_mr_ref_matrices,
        all_vert_ids,
        all_mr_vert_ids,
        sample_count,
        new_points,
    )

    # Yield each result matrix as pm.dt.Matrix
    for g in range(guide_count):
        flat_mat = result_matrices[g * 16:(g + 1) * 16]
        # Convert flat 16 to nested 4x4 tuple for pm.dt.Matrix
        nested = (
            tuple(flat_mat[0:4]),
            tuple(flat_mat[4:8]),
            tuple(flat_mat[8:12]),
            tuple(flat_mat[12:16]),
        )
        yield pm.dt.Matrix(nested)


def _yield_update_python(valid_guides, guideDictionary):
    """Pure Python update/repositioning path (fallback).

    Args:
        valid_guides (list): Filtered guide names.
        guideDictionary (dict): Guide data dictionary.
    """
    for guide in valid_guides:
        entry = guideDictionary[guide]
        if len(entry) == 5:
            # Multi-vertex format
            (vertexIds,
             node_matrix,
             orig_ref_matrix,
             mr_orig_ref_matrix,
             mr_vertexIds) = entry
            repoMatrix = getRepositionMatrix(
                pm.dt.Matrix(node_matrix),
                pm.dt.Matrix(orig_ref_matrix),
                pm.dt.Matrix(mr_orig_ref_matrix),
                vertexIds,
                mr_closestVerts=mr_vertexIds,
            )
        else:
            # Legacy single-vertex format
            (vertexIds,
             node_matrix,
             orig_ref_matrix,
             mr_orig_ref_matrix) = entry
            repoMatrix = getRepositionMatrix(
                pm.dt.Matrix(node_matrix),
                pm.dt.Matrix(orig_ref_matrix),
                pm.dt.Matrix(mr_orig_ref_matrix),
                vertexIds,
            )
        yield repoMatrix


@utils.viewport_off
@utils.one_undo
def updateGuidePlacement(guideOrder, guideDictionary, reset_scale=False,
                         reference_mesh=None, skip_orientation_nodes=None):
    """update the guides based on new universal mesh, in the provided order

    Args:
        guideOrder (list): of the hierarchy to crawl
        guideDictionary (dictionary): dict of the guide:edge, matrix position
        reset_scale (bool): Reset guide scale to default [1, 1, 1].
        reference_mesh (str, optional): Override mesh to use instead of the
            one embedded in the vertex ID strings. When ``None`` the
            original mesh name is used.
        skip_orientation_nodes (list, optional): Nodes that update position
            only, preserving their current orientation. When ``None``
            defaults to the module-level ``SKIP_ORIENTATION_NODES``.
    """
    if skip_orientation_nodes is None:
        skip_orientation_nodes = SKIP_ORIENTATION_NODES
    if reference_mesh is not None:
        _remap_mesh_in_guide_dict(guideDictionary, reference_mesh)
    updateGen = yieldUpdateGuidePlacement(guideOrder, guideDictionary)
    for guide in guideOrder:
        if guide not in guideDictionary or not mc.objExists(guide):
            continue
        elif guide in SKIP_PLACEMENT_NODES:
            continue
        guideNode = pm.PyNode(guide)
        scl = guideNode.getScale()
        repoMatrix = next(updateGen)
        if guide in skip_orientation_nodes:
            pos = pm.dt.TransformationMatrix(
                repoMatrix).getTranslation("world")
            guideNode.setTranslation(pos, space="world")
        else:
            guideNode.setMatrix(repoMatrix, worldSpace=True, preserve=True)
        if reset_scale:
            guideNode.setScale([1, 1, 1])
        else:
            guideNode.setScale(scl)
        yield guide


# ==============================================================================
# Data export, still testing
# ==============================================================================
def _importData(filepath):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(e)


def _exportData(data, filepath):
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, sort_keys=False, indent=4)
    except Exception as e:
        print(e)


def exportGuidePlacement(filepath=None,
                         reference_mesh=UNIVERSAL_MESH_NAME,
                         root_node=GUIDE_ROOT,
                         skip_crawl_nodes=SKIP_CRAWL_NODES,
                         skip_strings=None,
                         sample_count=None):
    """Export the position of the supplied root node to a file.

    Args:
        filepath (str, optional): Path to export to.
        reference_mesh (str, optional): Mesh to query verts.
        root_node (str, optional): Name of node to query against.
        skip_crawl_nodes (list, optional): Nodes not to crawl.
        skip_strings (list, optional): Strings to check to skip node.
        sample_count (int, optional): Number of vertices to sample per
            guide. Defaults to DEFAULT_SAMPLE_COUNT.

    Returns:
        tuple: relativeGuide_dict, ordered_hierarchy, filepath.
    """
    if skip_strings is None:
        skip_strings = []
    if sample_count is None:
        sample_count = DEFAULT_SAMPLE_COUNT
    if filepath is None:
        filepath = pm.fileDialog2(fileMode=0,
                                  startingDirectory="/",
                                  fileFilter="Export position(*.json)")
        if filepath:
            filepath = filepath[0]
    (relativeGuide_dict,
     ordered_hierarchy) = recordInitialGuidePlacement(
        reference_mesh=reference_mesh,
        root_node=root_node,
        skip_crawl_nodes=skip_crawl_nodes,
        skip_strings=skip_strings,
        sample_count=sample_count)
    data = {}
    data["version"] = 2
    data["sample_count"] = sample_count
    data["relativeGuide_dict"] = relativeGuide_dict
    data["ordered_hierarchy"] = ordered_hierarchy
    data["skip_crawl_nodes"] = list(SKIP_CRAWL_NODES)
    data["skip_placement_nodes"] = list(SKIP_PLACEMENT_NODES)
    data["skip_orientation_nodes"] = list(SKIP_ORIENTATION_NODES)
    _exportData(data, filepath)
    print("Guide position exported: {}".format(filepath))
    return relativeGuide_dict, ordered_hierarchy, filepath


def _remap_mesh_in_guide_dict(guide_dict, new_mesh_name):
    """Remap vertex ID strings in a guide dictionary to a different mesh.

    Replaces the mesh name portion of each vertex string
    (e.g. ``"oldMeshShape.vtx[5]"`` becomes ``"newMeshShape.vtx[5]"``).

    Args:
        guide_dict (dict): The relativeGuide_dict loaded from file.
        new_mesh_name (str): The new mesh shape (or transform) name to use.

    Returns:
        dict: The same dictionary with vertex strings remapped in place.
    """
    shape_name = _mesh_shape_name(new_mesh_name)
    for guide, entry in guide_dict.items():
        vertex_ids = entry[0]
        entry[0] = [
            "{}.vtx[{}]".format(shape_name, v.split("[")[1].rstrip("]"))
            for v in vertex_ids
        ]
        if len(entry) == 5:
            mr_vertex_ids = entry[4]
            entry[4] = [
                "{}.vtx[{}]".format(
                    shape_name, v.split("[")[1].rstrip("]")
                )
                for v in mr_vertex_ids
            ]
    return guide_dict


@utils.one_undo
def importGuidePlacement(filepath, reference_mesh=None,
                         skip_orientation_nodes=None):
    """Import the position from the provided file.

    Automatically detects legacy (v1) vs multi-vertex (v2) format
    and routes to the appropriate update path. When the file contains
    skip configuration, the module-level ``SKIP_CRAWL_NODES``,
    ``SKIP_PLACEMENT_NODES`` and ``SKIP_ORIENTATION_NODES`` are updated
    from the file data.

    Args:
        filepath (str): Path to the json file.
        reference_mesh (str, optional): Override mesh to use instead of the
            one embedded in the file. When ``None`` the original mesh name
            stored in the vertex IDs is used.
        skip_orientation_nodes (list, optional): Nodes that update position
            only, preserving their current orientation. When ``None``
            defaults to the module-level ``SKIP_ORIENTATION_NODES``.

    Returns:
        tuple: relativeGuide_dict, ordered_hierarchy.
    """
    global SKIP_CRAWL_NODES, SKIP_PLACEMENT_NODES, SKIP_ORIENTATION_NODES
    data = _importData(filepath)
    if not data:
        return {}, []
    # Restore skip configuration from file when present
    if "skip_crawl_nodes" in data:
        SKIP_CRAWL_NODES = list(data["skip_crawl_nodes"])
    if "skip_placement_nodes" in data:
        SKIP_PLACEMENT_NODES = list(data["skip_placement_nodes"])
    if "skip_orientation_nodes" in data:
        SKIP_ORIENTATION_NODES = list(data["skip_orientation_nodes"])
    if reference_mesh is not None:
        _remap_mesh_in_guide_dict(data["relativeGuide_dict"], reference_mesh)
    version = data.get("version", 1)
    if version >= 2:
        # Consume the generator to apply all guide updates
        for _ in updateGuidePlacement(
                data["ordered_hierarchy"], data["relativeGuide_dict"],
                skip_orientation_nodes=skip_orientation_nodes):
            pass
    else:
        # Legacy format: use the legacy update path
        updateGuidePlacementLegacy(
            data["ordered_hierarchy"], data["relativeGuide_dict"],
            skip_orientation_nodes=skip_orientation_nodes
        )
    return data["relativeGuide_dict"], data["ordered_hierarchy"]


def recordInitialGuidePlacement(reference_mesh=UNIVERSAL_MESH_NAME,
                                root_node=GUIDE_ROOT,
                                skip_crawl_nodes=SKIP_CRAWL_NODES,
                                skip_strings=None,
                                sample_count=None):
    """Record the relative guide placement against a reference mesh.

    Args:
        reference_mesh (str, optional): The mesh to query against.
        root_node (str, optional): Root node to crawl.
        skip_crawl_nodes (list, optional): Nodes to avoid.
        skip_strings (list, optional): Strings to check if skip.
        sample_count (int, optional): Number of vertices to sample per
            guide. Defaults to DEFAULT_SAMPLE_COUNT.

    Returns:
        tuple: relativeGuide_dict, ordered_hierarchy.
    """
    ordered_hierarchy = []
    relativeGuide_dict = {}
    crawlHierarchy(root_node,
                   ordered_hierarchy,
                   skip_crawl_nodes,
                   skip_strings=skip_strings)
    relativeGuide_dict = getGuideRelativeDictionary(
        reference_mesh, ordered_hierarchy, sample_count=sample_count
    )
    return relativeGuide_dict, ordered_hierarchy
