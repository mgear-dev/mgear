"""Shading utilities: per-face shader assignment and simple shaders.

Capture and restore the shading group assignment of a mesh, including
per-face multi-material assignments, and create flat, lighting
independent shaders.

Example:
    >>> from mgear.core import shading
    >>> mapping = shading.get_face_shader_mapping("body_geoShape")
    >>> shading.apply_face_shader_mapping("body_copyShape", mapping)
"""

from maya import cmds
import maya.api.OpenMaya as om2

#############################################
# FACE SHADER MAPPING
#############################################


def index_ranges(indices):
    """Collapse a sorted list of integers into inclusive ranges.

    Args:
        indices (list): Sorted integers, e.g. face ids.

    Returns:
        list: ``(start, end)`` tuples, inclusive. Empty for empty input.

    Example:
        >>> index_ranges([0, 1, 2, 5, 7, 8])
        [(0, 2), (5, 5), (7, 8)]
    """
    ranges = []
    if not indices:
        return ranges
    start = prev = indices[0]
    for index in indices[1:]:
        if index == prev + 1:
            prev = index
            continue
        ranges.append((start, prev))
        start = prev = index
    ranges.append((start, prev))
    return ranges


def get_face_shader_mapping(shape):
    """Return the shading groups of a mesh and the faces assigned to each.

    Per-face (multi-material) assignments are captured, not only the first
    shader. A mesh with one shading group takes a fast path without
    walking its faces.

    Args:
        shape (str): Mesh shape, or a transform with a single mesh shape.

    Returns:
        list: ``(shading_group, [(start, end), ...])`` pairs with inclusive
        face ranges. Empty when no shading group is assigned.
    """
    sel = om2.MSelectionList()
    sel.add(shape)
    dag = sel.getDagPath(0)
    dag.extendToShape()
    fn_mesh = om2.MFnMesh(dag)
    shaders, face_shader = fn_mesh.getConnectedShaders(dag.instanceNumber())
    if not shaders:
        return []

    names = [om2.MFnDependencyNode(s).name() for s in shaders]
    if len(names) == 1:
        return [(names[0], [(0, fn_mesh.numPolygons - 1)])]

    faces_by_index = {}
    for face, shader_index in enumerate(face_shader):
        if 0 <= shader_index < len(names):
            faces_by_index.setdefault(shader_index, []).append(face)
    return [
        (names[i], index_ranges(faces)) for i, faces in sorted(faces_by_index.items())
    ]


def apply_face_shader_mapping(shape, mapping):
    """Assign faces of a mesh to shading groups from a captured mapping.

    Shading groups that no longer exist are skipped.

    Args:
        shape (str): Mesh shape to assign. Must have the same face count
            as the mesh the mapping was captured from.
        mapping (list): As returned by :func:`get_face_shader_mapping`.
    """
    shape = cmds.ls(shape, long=True)[0]
    for shading_group, ranges in mapping:
        if not ranges or not cmds.objExists(shading_group):
            continue
        components = ["{}.f[{}:{}]".format(shape, start, end) for start, end in ranges]
        cmds.sets(components, edit=True, forceElement=shading_group)


#############################################
# SHADERS
#############################################


def create_flat_shader(name, color, transparency=0.0):
    """Create or update a flat, lighting independent blinn shader.

    Diffuse is disabled and the color is driven through incandescence,
    so scene lights do not shade it. Specular is removed. Existing nodes
    named ``name`` and ``name + "SG"`` are reused and updated.

    Args:
        name (str): Shader node name. The shading group is ``name + "SG"``.
        color (tuple): RGB color, 0-1 range.
        transparency (float, optional): 0 opaque to 1 fully transparent.

    Returns:
        tuple: ``(shader, shading_group)`` node names.
    """
    shader = name
    if not cmds.objExists(shader):
        shader = cmds.shadingNode("blinn", asShader=True, name=name)

    shading_group = name + "SG"
    if not cmds.objExists(shading_group):
        shading_group = cmds.sets(
            renderable=True,
            noSurfaceShader=True,
            empty=True,
            name=shading_group,
        )
    if not cmds.isConnected(shader + ".outColor", shading_group + ".surfaceShader"):
        cmds.connectAttr(
            shader + ".outColor", shading_group + ".surfaceShader", force=True
        )

    cmds.setAttr(shader + ".color", *color, type="double3")
    cmds.setAttr(shader + ".incandescence", *color, type="double3")
    cmds.setAttr(shader + ".diffuse", 0.0)
    cmds.setAttr(shader + ".specularColor", 0.0, 0.0, 0.0, type="double3")
    set_shader_transparency(shader, transparency)
    return shader, shading_group


def set_shader_transparency(shader, transparency):
    """Set a uniform transparency on a shader.

    Args:
        shader (str): Shader node with a ``transparency`` color attribute.
        transparency (float): 0 opaque to 1 fully transparent.
    """
    cmds.setAttr(
        shader + ".transparency",
        transparency,
        transparency,
        transparency,
        type="double3",
    )
