"""Matcap Viewer - Core Logic.

Shader graph creation, material assignment, viewport texture
management, and scene cleanup. No Qt code.
"""

import logging
import os

from maya import cmds

logger = logging.getLogger("mgear.utilbits.matcap_viewer")

# Node names
SHADER_NAME = "mgear_matcap_shader"
SG_NAME = "mgear_matcap_SG"
ENVBALL_NAME = "mgear_matcap_envBall"
FILE_NAME = "mgear_matcap_file"
PLACE2D_NAME = "mgear_matcap_place2d"
PLACE3D_NAME = "mgear_matcap_place3d"

ALL_NODE_NAMES = (
    SG_NAME,
    SHADER_NAME,
    ENVBALL_NAME,
    FILE_NAME,
    PLACE2D_NAME,
    PLACE3D_NAME,
)

IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".exr",
    ".bmp",
)

# Place2dTexture attributes to connect to the file node
_PLACE2D_ATTRS = (
    "coverage",
    "translateFrame",
    "rotateFrame",
    "mirrorU",
    "mirrorV",
    "stagger",
    "wrapU",
    "wrapV",
    "repeatUV",
    "offset",
    "rotateUV",
    "noiseUV",
    "vertexUvOne",
    "vertexUvTwo",
    "vertexUvThree",
    "vertexCameraOne",
)

# Module-level state
_original_assignments = {}
_matcap_active = False
_tracked_meshes = []
_viewport_texture_states = {}


# ================================================================
# Shader Graph
# ================================================================


def shader_graph_exists():
    """Check whether the matcap shader graph exists in the scene.

    Returns:
        bool: True if the shader node exists.
    """
    return cmds.objExists(SHADER_NAME)


def create_shader_graph():
    """Create the matcap shader graph if it does not exist.

    Graph: surfaceShader <- envBall (eyeSpace=1) <- file (filterType=0)
    with place2dTexture and place3dTexture helpers.

    Returns:
        tuple: (shader, shading_group, file_node) names.
    """
    if shader_graph_exists():
        return SHADER_NAME, SG_NAME, FILE_NAME

    shader = cmds.shadingNode(
        "surfaceShader", name=SHADER_NAME, asShader=True
    )
    sg = cmds.sets(
        renderable=True,
        noSurfaceShader=True,
        empty=True,
        name=SG_NAME,
    )
    cmds.connectAttr(
        "{}.outColor".format(shader),
        "{}.surfaceShader".format(sg),
        force=True,
    )

    envball = cmds.shadingNode(
        "envBall", name=ENVBALL_NAME, asTexture=True
    )
    place3d = cmds.shadingNode(
        "place3dTexture", name=PLACE3D_NAME, asUtility=True
    )
    place2d = cmds.shadingNode(
        "place2dTexture", name=PLACE2D_NAME, asUtility=True
    )
    file_node = cmds.shadingNode(
        "file", name=FILE_NAME, asTexture=True
    )

    # place3d -> envBall
    cmds.connectAttr(
        "{}.worldInverseMatrix".format(place3d),
        "{}.placementMatrix".format(envball),
        force=True,
    )

    # envBall -> shader
    cmds.connectAttr(
        "{}.outColor".format(envball),
        "{}.outColor".format(shader),
        force=True,
    )

    # place2d -> file
    for attr in _PLACE2D_ATTRS:
        src = "{}.{}".format(place2d, attr)
        dst = "{}.{}".format(file_node, attr)
        if cmds.objExists(src) and cmds.objExists(dst):
            cmds.connectAttr(src, dst, force=True)
    cmds.connectAttr(
        "{}.outUV".format(place2d),
        "{}.uv".format(file_node),
        force=True,
    )
    cmds.connectAttr(
        "{}.outUvFilterSize".format(place2d),
        "{}.uvFilterSize".format(file_node),
        force=True,
    )

    # file -> envBall
    cmds.connectAttr(
        "{}.outColor".format(file_node),
        "{}.image".format(envball),
        force=True,
    )

    cmds.setAttr("{}.filterType".format(file_node), 0)
    cmds.setAttr("{}.eyeSpace".format(envball), 1)

    # Hide the place3dTexture node in the viewport
    cmds.hide(place3d)

    logger.info("Created matcap shader graph")
    return shader, sg, file_node


def set_texture(image_path):
    """Set the matcap texture image on the file node.

    Args:
        image_path (str): Full path to the image file.
    """
    if not cmds.objExists(FILE_NAME):
        logger.warning("Matcap file node does not exist")
        return
    cmds.setAttr(
        "{}.fileTextureName".format(FILE_NAME),
        str(image_path),
        type="string",
    )
    logger.debug("Set matcap texture: %s", image_path)


def get_current_texture():
    """Get the current matcap texture path.

    Returns:
        str: Image path, or None if no graph exists.
    """
    if not cmds.objExists(FILE_NAME):
        return None
    return cmds.getAttr("{}.fileTextureName".format(FILE_NAME))


# ================================================================
# Folder Scanning
# ================================================================


def scan_folders(folder_paths):
    """Scan folders for matcap image files.

    Args:
        folder_paths (list): List of directory paths to scan.

    Returns:
        list: Sorted list of dicts with keys name, path, folder.
    """
    entries = []
    seen = set()
    for folder in folder_paths:
        if not os.path.isdir(folder):
            continue
        for filename in os.listdir(folder):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            full_path = os.path.join(folder, filename)
            if full_path in seen:
                continue
            seen.add(full_path)
            entries.append(
                {
                    "name": os.path.splitext(filename)[0],
                    "path": full_path,
                    "folder": folder,
                }
            )
    entries.sort(key=lambda e: e["name"].lower())
    return entries


# ================================================================
# Mesh Utilities
# ================================================================


def get_all_mesh_transforms():
    """Get all mesh transform nodes in the scene.

    Intermediate shapes (e.g. blendshape target caches, orig shapes)
    are skipped since they are not visible and can live under
    hidden/locked transforms that raise on listRelatives.

    Returns:
        list: Deduplicated list of mesh transform long names.
    """
    shapes = cmds.ls(type="mesh", noIntermediate=True, long=True) or []
    transforms = set()
    for shape in shapes:
        parents = cmds.listRelatives(
            shape, parent=True, fullPath=True
        )
        if parents:
            transforms.add(parents[0])
    return sorted(transforms)


# ================================================================
# Material Assignment Tracking
# ================================================================


def store_original_assignments(meshes):
    """Store the current shading group assignments for meshes.

    Handles per-face multi-material assignments.

    Args:
        meshes (list): Mesh transform long names.
    """
    global _original_assignments

    for transform in meshes:
        if not cmds.objExists(transform):
            continue
        shapes = cmds.listRelatives(
            transform,
            shapes=True,
            fullPath=True,
            type="mesh",
            noIntermediate=True,
        )
        if not shapes:
            continue
        short_transform = transform.rsplit("|", 1)[-1]
        for shape in shapes:
            if shape in _original_assignments:
                continue
            short_shape = shape.rsplit("|", 1)[-1]
            # Any of these prefixes in an SG member list means
            # the member belongs to this shape.  cmds.sets can
            # return the member using the shape OR the transform
            # name (short or long) with an optional component
            # suffix like ".f[0:3]".
            prefixes = (shape, short_shape, transform, short_transform)
            sgs = cmds.listSets(type=1, object=shape) or []
            assignments = []
            for sg in sgs:
                members = cmds.sets(sg, query=True) or []
                shape_members = []
                for member in members:
                    # Normalize every matched member to the
                    # shape's full DAG path so the restore pass
                    # always resolves correctly.
                    for prefix in prefixes:
                        if member == prefix:
                            shape_members.append(shape)
                            break
                        if member.startswith(prefix + "."):
                            suffix = member[len(prefix):]
                            shape_members.append(shape + suffix)
                            break
                if shape_members:
                    assignments.append((sg, shape_members))
                elif not assignments:
                    assignments.append((sg, None))
            if assignments:
                _original_assignments[shape] = assignments


def _restore_assignments():
    """Restore all stored shading group assignments."""
    global _original_assignments

    # Re-apply stored assignments directly.  forceElement will
    # pull faces/shapes out of matcap_SG and into the original SG.
    for shape, assignments in _original_assignments.items():
        if not cmds.objExists(shape):
            continue
        for sg, members in assignments:
            if not cmds.objExists(sg):
                continue
            if members is None:
                cmds.sets(shape, edit=True, forceElement=sg)
            else:
                valid = [m for m in members if cmds.objExists(m)]
                if valid:
                    cmds.sets(valid, edit=True, forceElement=sg)

    # Safety net: any shape still in matcap_SG after the restore
    # (e.g. an SG was deleted, or a stored member no longer
    # resolves) gets pushed to initialShadingGroup so nothing is
    # left rendering the matcap shader.
    if cmds.objExists(SG_NAME):
        residual = cmds.sets(SG_NAME, query=True) or []
        if residual:
            try:
                cmds.sets(
                    residual,
                    edit=True,
                    forceElement="initialShadingGroup",
                )
            except (RuntimeError, ValueError):
                pass

    _original_assignments = {}


# ================================================================
# Viewport Textures
# ================================================================


def enable_viewport_textures():
    """Enable textured display on all model panels.

    Stores the previous state so it can be restored later.

    Returns:
        bool: True if any panel state was changed.
    """
    global _viewport_texture_states

    changed = False
    panels = cmds.getPanel(type="modelPanel") or []
    for panel in panels:
        current = cmds.modelEditor(
            panel, query=True, displayTextures=True
        )
        if not current:
            _viewport_texture_states[panel] = False
            cmds.modelEditor(
                panel, edit=True, displayTextures=True
            )
            changed = True
    return changed


def restore_viewport_textures():
    """Restore viewport texture display to stored states."""
    global _viewport_texture_states

    for panel, was_enabled in _viewport_texture_states.items():
        try:
            cmds.modelEditor(
                panel, edit=True, displayTextures=was_enabled
            )
        except RuntimeError:
            pass
    _viewport_texture_states = {}


# ================================================================
# Apply / Restore / Toggle
# ================================================================


def apply_matcap(meshes=None):
    """Apply the matcap shader to meshes.

    Args:
        meshes (list, optional): Mesh transforms to apply to.
            If None, applies to all meshes in the scene.

    Returns:
        bool: True if matcap was applied successfully.
    """
    global _matcap_active
    global _tracked_meshes

    create_shader_graph()

    if meshes is None:
        meshes = get_all_mesh_transforms()

    if not meshes:
        logger.warning("No meshes found to apply matcap")
        return False

    cmds.undoInfo(openChunk=True)
    try:
        store_original_assignments(meshes)

        shapes = []
        for transform in meshes:
            if not cmds.objExists(transform):
                continue
            shape_list = cmds.listRelatives(
                transform,
                shapes=True,
                fullPath=True,
                type="mesh",
                noIntermediate=True,
            )
            if shape_list:
                shapes.extend(shape_list)

        if shapes:
            cmds.sets(shapes, edit=True, forceElement=SG_NAME)

        _tracked_meshes = list(meshes)
        _matcap_active = True

        texture_changed = enable_viewport_textures()
        if texture_changed:
            cmds.inViewMessage(
                assistMessage="Viewport textures enabled for matcap display",
                pos="topCenter",
                fade=True,
            )
    finally:
        cmds.undoInfo(closeChunk=True)

    logger.info("Applied matcap to %d meshes", len(meshes))
    return True


def restore_original_materials():
    """Restore original materials on all tracked meshes."""
    global _matcap_active
    global _tracked_meshes

    if not _original_assignments:
        _matcap_active = False
        return

    cmds.undoInfo(openChunk=True)
    try:
        _restore_assignments()
        restore_viewport_textures()
        _matcap_active = False
        # Keep _tracked_meshes so toggle re-applies to
        # the same set instead of falling back to all meshes
    finally:
        cmds.undoInfo(closeChunk=True)

    logger.info("Restored original materials")


def toggle_matcap():
    """Toggle matcap on/off.

    Returns:
        bool: New active state after toggle.
    """
    if _matcap_active:
        restore_original_materials()
    else:
        apply_matcap(meshes=_tracked_meshes or None)
    return _matcap_active


def is_matcap_active():
    """Check whether the matcap is currently active.

    Returns:
        bool: True if matcap is applied.
    """
    return _matcap_active


def get_tracked_meshes():
    """Get the list of meshes currently tracked for matcap.

    Returns:
        list: Tracked mesh transform names, or empty list.
    """
    return list(_tracked_meshes)


# ================================================================
# Cleanup
# ================================================================


def cleanup():
    """Full cleanup: restore materials, delete shader graph, reset state."""
    global _matcap_active
    global _tracked_meshes
    global _original_assignments
    global _viewport_texture_states

    if _matcap_active:
        restore_original_materials()

    for node_name in ALL_NODE_NAMES:
        if cmds.objExists(node_name):
            try:
                cmds.delete(node_name)
            except RuntimeError:
                logger.warning("Could not delete %s", node_name)

    _matcap_active = False
    _tracked_meshes = []
    _original_assignments = {}
    _viewport_texture_states = {}

    logger.info("Matcap cleanup complete")
