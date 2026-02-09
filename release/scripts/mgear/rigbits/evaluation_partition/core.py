"""Evaluation Partition Tool - Core Module.

This module provides core functionality for the Evaluation Partition Tool,
including data structures, color generation, shader management, face assignment,
and configuration import/export.
"""

import colorsys
import json
import logging
import random

from maya import cmds
from maya import mel

from mgear.core import blendshape
from mgear.core import deformer
from mgear.core import skin
from mgear.core import utils

log = logging.getLogger("mgear.rigbits.evaluation_partition")


# =====================================================
# CONSTANTS
# =====================================================

DEFAULT_SATURATION_RANGE = (0.25, 0.55)
DEFAULT_VALUE_RANGE = (0.55, 0.85)
SHADER_PREFIX = "evalPartition"
DEFAULT_GROUP_NAME = "All Faces"
CONFIG_FILE_EXT = ".evp"
CONFIG_VERSION = "1.0"


# =====================================================
# DATA CLASSES
# =====================================================


class PolygonGroup:
    """Represents a polygon group with shader assignment.

    Args:
        name (str): User-editable group name.
        color (tuple): RGB color tuple (r, g, b) with values 0-1.
        face_indices (set): Set of face indices belonging to this group.
        shader_node (str): Maya shader node name.
        shading_group (str): Maya shading group name.
    """

    def __init__(
        self,
        name="",
        color=(0.5, 0.5, 0.5),
        face_indices=None,
        shader_node="",
        shading_group="",
    ):
        self.name = name
        self.color = color
        self.face_indices = face_indices if face_indices is not None else set()
        self.shader_node = shader_node
        self.shading_group = shading_group


class PolygonGroupManager:
    """Manages polygon groups for a specific mesh.

    Args:
        mesh (str): The mesh transform or shape node name.
    """

    def __init__(self, mesh):
        self.mesh = mesh
        self.groups = []
        self.original_shading = {}
        self.showing_partitions = True
        self._mesh_short_name = mesh.split("|")[-1].replace(":", "_")

    def get_group_by_name(self, name):
        """Get a group by its name.

        Args:
            name (str): The group name to search for.

        Returns:
            PolygonGroup: The PolygonGroup if found, None otherwise.
        """
        for group in self.groups:
            if group.name == name:
                return group
        return None

    def get_default_group(self):
        """Get the default 'All Faces' group.

        Returns:
            PolygonGroup: The default PolygonGroup if it exists, None otherwise.
        """
        return self.get_group_by_name(DEFAULT_GROUP_NAME)

    def generate_unique_name(self, base_name="Group"):
        """Generate a unique group name.

        Args:
            base_name (str): The base name to use.

        Returns:
            str: A unique group name.
        """
        existing_names = {g.name for g in self.groups}
        if base_name not in existing_names:
            return base_name

        counter = 1
        while f"{base_name}_{counter}" in existing_names:
            counter += 1
        return f"{base_name}_{counter}"


# =====================================================
# COLOR FUNCTIONS
# =====================================================


def generate_muted_color(
    saturation_range=DEFAULT_SATURATION_RANGE,
    value_range=DEFAULT_VALUE_RANGE,
):
    """Generate a random muted color using HSV color space.

    Args:
        saturation_range (tuple): Min and max saturation values (0-1).
        value_range (tuple): Min and max value/brightness values (0-1).

    Returns:
        tuple: RGB color tuple (r, g, b) with values 0-1.
    """
    hue = random.random()
    saturation = random.uniform(*saturation_range)
    value = random.uniform(*value_range)

    r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
    return (r, g, b)


# =====================================================
# SHADER FUNCTIONS
# =====================================================


def create_partition_shader(name, color):
    """Create a lambert shader with the given color.

    Args:
        name (str): Base name for the shader.
        color (tuple): RGB color tuple (r, g, b) with values 0-1.

    Returns:
        tuple: Tuple of (shader_node, shading_group) names.
    """
    shader_name = f"{name}_shader"
    sg_name = f"{shader_name}SG"

    # Create lambert shader
    shader = cmds.shadingNode("lambert", asShader=True, name=shader_name)

    # Create shading group
    sg = cmds.sets(
        renderable=True,
        noSurfaceShader=True,
        empty=True,
        name=sg_name,
    )

    # Connect shader to shading group
    cmds.connectAttr(f"{shader}.outColor", f"{sg}.surfaceShader", force=True)

    # Set color
    cmds.setAttr(f"{shader}.color", *color, type="double3")

    return shader, sg


def delete_partition_shader(shader_node, shading_group):
    """Delete a partition shader and its shading group.

    Args:
        shader_node (str): The shader node name.
        shading_group (str): The shading group name.
    """
    if shading_group and cmds.objExists(shading_group):
        cmds.delete(shading_group)
    if shader_node and cmds.objExists(shader_node):
        cmds.delete(shader_node)


def update_shader_color(shader_node, color):
    """Update a shader's color.

    Args:
        shader_node (str): The shader node name.
        color (tuple): RGB color tuple (r, g, b) with values 0-1.
    """
    if cmds.objExists(shader_node):
        cmds.setAttr(f"{shader_node}.color", *color, type="double3")


def rename_shader(shader_node, shading_group, new_name):
    """Rename a shader and its shading group.

    Args:
        shader_node (str): Current shader node name.
        shading_group (str): Current shading group name.
        new_name (str): New base name for the shader.

    Returns:
        tuple: Tuple of (new_shader_name, new_shading_group_name).
    """
    new_shader_name = f"{new_name}_shader"
    new_sg_name = f"{new_shader_name}SG"

    renamed_shader = shader_node
    renamed_sg = shading_group

    if cmds.objExists(shader_node):
        renamed_shader = cmds.rename(shader_node, new_shader_name)
    if cmds.objExists(shading_group):
        renamed_sg = cmds.rename(shading_group, new_sg_name)

    return renamed_shader, renamed_sg


# =====================================================
# FACE ASSIGNMENT FUNCTIONS
# =====================================================


def assign_faces_to_shader(mesh, face_indices, shading_group):
    """Assign specific faces to a shading group.

    Args:
        mesh (str): The mesh transform name.
        face_indices (set): Set of face indices to assign.
        shading_group (str): Target shading group name.
    """
    if not face_indices:
        return

    if not cmds.objExists(shading_group):
        cmds.warning(f"Shading group '{shading_group}' does not exist.")
        return

    # Build face component list
    faces = [f"{mesh}.f[{i}]" for i in sorted(face_indices)]

    # Assign to shading group
    cmds.sets(faces, edit=True, forceElement=shading_group)


def get_all_face_indices(mesh):
    """Get all face indices for a mesh.

    Args:
        mesh (str): The mesh transform or shape name.

    Returns:
        set: Set of all face indices.
    """
    # Get the shape node
    shapes = cmds.listRelatives(mesh, shapes=True, type="mesh", fullPath=True)
    if not shapes:
        # Maybe it's already a shape
        if cmds.nodeType(mesh) == "mesh":
            shape = mesh
        else:
            return set()
    else:
        shape = shapes[0]

    face_count = cmds.polyEvaluate(shape, face=True)
    return set(range(face_count))


def get_short_name(name):
    """Get the short name from a potentially long path.

    Args:
        name (str): Node name, possibly with path (e.g., "|group1|pCube1").

    Returns:
        str: Short name without path (e.g., "pCube1").
    """
    return name.split("|")[-1]


def names_match(name1, name2):
    """Check if two node names refer to the same node.

    Compares short names to handle long/short path mismatches.

    Args:
        name1 (str): First node name.
        name2 (str): Second node name.

    Returns:
        bool: True if names match (same short name).
    """
    return get_short_name(name1) == get_short_name(name2)


def get_selected_faces(mesh=None):
    """Get currently selected polygon faces from Maya.

    Args:
        mesh (str): Optional mesh to filter selection by.

    Returns:
        tuple: Tuple of (mesh_name, set of face indices). Returns (None, empty set)
            if no valid face selection.
    """
    selection = cmds.ls(selection=True, flatten=True)
    if not selection:
        return None, set()

    face_indices = set()
    detected_mesh = None

    # Get filter mesh short name for comparison
    filter_short_name = get_short_name(mesh) if mesh else None

    for item in selection:
        # Check if it's a face component
        if ".f[" in item:
            # Extract mesh name and face index
            mesh_name = item.split(".f[")[0]
            mesh_short_name = get_short_name(mesh_name)

            # Filter by mesh if specified
            if filter_short_name and mesh_short_name != filter_short_name:
                continue

            if detected_mesh is None:
                detected_mesh = mesh_name
            elif not names_match(detected_mesh, mesh_name):
                # Multiple meshes selected, skip
                continue

            # Extract face index
            index_str = item.split(".f[")[1].rstrip("]")
            try:
                face_indices.add(int(index_str))
            except ValueError:
                # Handle face ranges like f[0:10]
                if ":" in index_str:
                    start, end = index_str.split(":")
                    face_indices.update(range(int(start), int(end) + 1))

    return detected_mesh, face_indices


# =====================================================
# GROUP MANAGEMENT FUNCTIONS
# =====================================================


def create_default_group(manager):
    """Create the initial 'All Faces' group containing all polygons.

    Args:
        manager (PolygonGroupManager): The PolygonGroupManager instance.

    Returns:
        PolygonGroup: The created default PolygonGroup.
    """
    # Get all face indices
    face_indices = get_all_face_indices(manager.mesh)

    # Generate muted color
    color = generate_muted_color()

    # Create shader
    shader_base_name = f"{SHADER_PREFIX}_{manager._mesh_short_name}_{DEFAULT_GROUP_NAME.replace(' ', '_')}"
    shader_node, shading_group = create_partition_shader(shader_base_name, color)

    # Create group
    group = PolygonGroup(
        name=DEFAULT_GROUP_NAME,
        color=color,
        face_indices=face_indices,
        shader_node=shader_node,
        shading_group=shading_group,
    )

    # Assign faces to shader
    assign_faces_to_shader(manager.mesh, face_indices, shading_group)

    return group


def create_group_from_selection(manager, name, selected_faces):
    """Create a new group from selected faces.

    Removes faces from other groups (faces belong to exactly one group).

    Args:
        manager (PolygonGroupManager): The PolygonGroupManager instance.
        name (str): Name for the new group.
        selected_faces (set): Set of face indices for the new group.

    Returns:
        PolygonGroup: The created PolygonGroup, or None if creation failed.
    """
    if not selected_faces:
        return None

    # Remove selected faces from all existing groups
    for group in manager.groups:
        group.face_indices -= selected_faces

    # Generate muted color
    color = generate_muted_color()

    # Create shader
    shader_base_name = f"{SHADER_PREFIX}_{manager._mesh_short_name}_{name.replace(' ', '_')}"
    shader_node, shading_group = create_partition_shader(shader_base_name, color)

    # Create group
    group = PolygonGroup(
        name=name,
        color=color,
        face_indices=selected_faces,
        shader_node=shader_node,
        shading_group=shading_group,
    )

    # Assign faces to new shader
    assign_faces_to_shader(manager.mesh, selected_faces, shading_group)

    # Re-assign remaining faces in other groups to their shaders
    for existing_group in manager.groups:
        if existing_group.face_indices:
            assign_faces_to_shader(
                manager.mesh,
                existing_group.face_indices,
                existing_group.shading_group,
            )

    return group


def remove_group(manager, group):
    """Remove a group and return its faces to the default group.

    Args:
        manager (PolygonGroupManager): The PolygonGroupManager instance.
        group (PolygonGroup): The group to remove.

    Returns:
        bool: True if removal was successful, False otherwise.
    """
    if group.name == DEFAULT_GROUP_NAME:
        cmds.warning("Cannot remove the default group.")
        return False

    if group not in manager.groups:
        return False

    # Get the default group
    default_group = manager.get_default_group()
    if not default_group:
        cmds.warning("Default group not found.")
        return False

    # Transfer faces to default group
    default_group.face_indices.update(group.face_indices)

    # Delete the shader
    delete_partition_shader(group.shader_node, group.shading_group)

    # Re-assign faces to default shader
    assign_faces_to_shader(
        manager.mesh,
        default_group.face_indices,
        default_group.shading_group,
    )

    # Remove from manager
    manager.groups.remove(group)

    return True


def update_group_color(group, new_color):
    """Update the shader color for a group.

    Args:
        group (PolygonGroup): The PolygonGroup to update.
        new_color (tuple): New RGB color tuple (r, g, b) with values 0-1.
    """
    group.color = new_color
    update_shader_color(group.shader_node, new_color)


def rename_group(manager, group, new_name):
    """Rename a group and its associated shader.

    Args:
        manager (PolygonGroupManager): The PolygonGroupManager instance.
        group (PolygonGroup): The group to rename.
        new_name (str): New name for the group.

    Returns:
        bool: True if rename was successful, False otherwise.
    """
    if group.name == DEFAULT_GROUP_NAME:
        cmds.warning("Cannot rename the default group.")
        return False

    # Check for duplicate names
    existing = manager.get_group_by_name(new_name)
    if existing and existing != group:
        cmds.warning(f"A group named '{new_name}' already exists.")
        return False

    # Rename shader
    new_base_name = f"{SHADER_PREFIX}_{manager._mesh_short_name}_{new_name.replace(' ', '_')}"
    new_shader, new_sg = rename_shader(
        group.shader_node, group.shading_group, new_base_name
    )

    # Update group
    group.name = new_name
    group.shader_node = new_shader
    group.shading_group = new_sg

    return True


def cleanup_all_shaders(manager):
    """Delete all partition shaders for a manager.

    Args:
        manager (PolygonGroupManager): The PolygonGroupManager instance.
    """
    for group in manager.groups:
        delete_partition_shader(group.shader_node, group.shading_group)
    manager.groups.clear()


def reset_to_default(manager):
    """Reset to a single default group containing all polygons.

    Args:
        manager (PolygonGroupManager): The PolygonGroupManager instance.

    Returns:
        PolygonGroup: The new default PolygonGroup.
    """
    # Clean up existing shaders
    cleanup_all_shaders(manager)

    # Create new default group
    default_group = create_default_group(manager)
    manager.groups.append(default_group)

    return default_group


# =====================================================
# SHADER TOGGLE FUNCTIONS
# =====================================================


def capture_original_shading(manager):
    """Capture the current per-face shading group assignments.

    Should be called before any partition shaders are applied, so the
    original materials can be restored later via toggle.

    Args:
        manager (PolygonGroupManager): The PolygonGroupManager instance.

    Returns:
        dict: Mapping of shading group name to set of face indices.
    """
    mesh = manager.mesh
    original = {}

    # Get shape node
    shapes = cmds.listRelatives(
        mesh, shapes=True, type="mesh", fullPath=True
    )
    if not shapes:
        return original
    shape = shapes[0]

    # Get all shading groups connected to this shape
    shading_groups = cmds.listSets(type=1, object=shape) or []

    for sg in shading_groups:
        members = cmds.sets(sg, query=True) or []

        face_indices = set()
        for member in members:
            # Filter to our mesh's face components
            if ".f[" not in member:
                # Whole object assignment (no per-face)
                if names_match(member, mesh):
                    face_indices = get_all_face_indices(mesh)
                    break
                continue

            member_mesh = member.split(".f[")[0]
            if not names_match(member_mesh, mesh):
                continue

            index_str = member.split(".f[")[1].rstrip("]")
            try:
                face_indices.add(int(index_str))
            except ValueError:
                if ":" in index_str:
                    start, end = index_str.split(":")
                    face_indices.update(range(int(start), int(end) + 1))

        if face_indices:
            original[sg] = face_indices

    manager.original_shading = original
    return original


def show_partition_shaders(manager):
    """Assign partition shaders to the mesh.

    Args:
        manager (PolygonGroupManager): The PolygonGroupManager instance.
    """
    for group in manager.groups:
        if group.face_indices and group.shading_group:
            assign_faces_to_shader(
                manager.mesh, group.face_indices, group.shading_group
            )
    manager.showing_partitions = True


def show_original_shaders(manager):
    """Restore the original shading group assignments.

    Args:
        manager (PolygonGroupManager): The PolygonGroupManager instance.

    Returns:
        bool: True if original shaders were restored, False if no
            original shading data is available.
    """
    if not manager.original_shading:
        cmds.warning("No original shading data captured.")
        return False

    for sg, face_indices in manager.original_shading.items():
        if cmds.objExists(sg):
            assign_faces_to_shader(manager.mesh, face_indices, sg)

    manager.showing_partitions = False
    return True


def toggle_shaders(manager):
    """Toggle between partition and original shaders.

    Args:
        manager (PolygonGroupManager): The PolygonGroupManager instance.

    Returns:
        bool: True if now showing partitions, False if showing original.
    """
    if manager.showing_partitions:
        show_original_shaders(manager)
    else:
        show_partition_shaders(manager)
    return manager.showing_partitions


# =====================================================
# PROGRESS BAR UTILITIES
# =====================================================


def _progress_start(title, max_value):
    """Start the Maya main progress bar.

    Args:
        title (str): Initial status text.
        max_value (int): Total number of steps.

    Returns:
        str: Progress bar UI element name.
    """
    bar = mel.eval("$tmp = $gMainProgressBar")
    cmds.progressBar(
        bar,
        edit=True,
        beginProgress=True,
        isInterruptable=False,
        status=title,
        maxValue=max_value,
    )
    return bar


def _progress_update(bar, status):
    """Advance progress bar by one step.

    Args:
        bar (str): Progress bar UI element name.
        status (str): New status text.
    """
    cmds.progressBar(
        bar, edit=True, step=1, status=status
    )


def _progress_end(bar):
    """Close the Maya main progress bar.

    Args:
        bar (str): Progress bar UI element name.
    """
    cmds.progressBar(bar, edit=True, endProgress=True)


# =====================================================
# DEFORMER UTILITIES
# =====================================================


def _get_vertex_positions(mesh):
    """Get all vertex world positions as a flat list.

    Args:
        mesh (str): Mesh transform name.

    Returns:
        list: Flat list of [x, y, z, x, y, z, ...].
    """
    return cmds.xform(
        f"{mesh}.vtx[*]", query=True,
        worldSpace=True, translation=True,
    )


# =====================================================
# PIPELINE STEP 1: SPLIT POLYGON GROUPS
# =====================================================


def split_polygon_groups(manager):
    """Split the mesh into separate parts based on polygon groups.

    Creates a duplicate of the mesh for each group in bind pose,
    deleting faces that don't belong to that group. Original
    shading is preserved on each partition. The source mesh is
    not modified.

    Deformers on the source are temporarily disabled so split
    parts contain bind-pose geometry suitable for deformer
    transfer.

    Args:
        manager (PolygonGroupManager): The manager with groups.

    Returns:
        tuple: (group_node, partition_meshes) where group_node
            is the parent transform and partition_meshes is a
            list of mesh names. Returns (None, []) if failed.
    """
    if not manager or not manager.groups:
        cmds.warning("No groups defined.")
        return None, []

    mesh = manager.mesh
    mesh_short = get_short_name(mesh)

    # Temporarily restore original shaders so duplicates
    # inherit them
    was_showing_partitions = manager.showing_partitions
    if was_showing_partitions and manager.original_shading:
        show_original_shaders(manager)

    # Disable all deformers for bind-pose duplicates
    saved_envelopes = deformer.disable_deformer_envelopes(mesh)

    partition_meshes = []

    try:
        for group in manager.groups:
            if not group.face_indices:
                continue

            safe_name = group.name.replace(" ", "_")
            partition_name = f"{mesh_short}_{safe_name}"

            dup = cmds.duplicate(
                mesh, rr=True, ic=False,
                name=partition_name,
            )
            new_obj = dup[0]

            # Unlock transform attributes
            for attr in (
                "translateX", "translateY",
                "translateZ",
                "rotateX", "rotateY", "rotateZ",
                "scaleX", "scaleY", "scaleZ",
            ):
                cmds.setAttr(
                    f"{new_obj}.{attr}", lock=False
                )

            new_faces = cmds.ls(
                f"{new_obj}.f[*]", flatten=True
            )

            # Build faces to delete by removing kept faces
            faces_to_del = list(new_faces)
            for face_idx in sorted(
                group.face_indices, reverse=True
            ):
                if face_idx < len(faces_to_del):
                    faces_to_del.pop(face_idx)

            if faces_to_del:
                cmds.delete(faces_to_del)

            cmds.delete(new_obj, ch=True)
            partition_meshes.append(new_obj)

    finally:
        deformer.restore_deformer_envelopes(saved_envelopes)

    # Restore previous shader state on source mesh
    if was_showing_partitions:
        show_partition_shaders(manager)

    if not partition_meshes:
        cmds.warning("No partitions created.")
        return None, []

    grp_name = f"{mesh_short}_partitions"
    grp = cmds.group(partition_meshes, name=grp_name)

    return grp, partition_meshes


# Backward compatibility alias
execute_partition = split_polygon_groups


# =====================================================
# PIPELINE STEP 2: TRANSFER BLENDSHAPES
# =====================================================


def transfer_blendshapes(source_mesh, partition_meshes):
    """Transfer blendshapes from source to each partition.

    Uses a wrap-based approach: for each partition, a temporary
    wrap deformer maps it to follow the source mesh. Blendshape
    targets are triggered one at a time and captured via the
    connect/disconnect pattern.

    Pattern from flex.update_utils.create_blendshapes_backup().

    Args:
        source_mesh (str): The original source mesh transform.
        partition_meshes (list): List of partition mesh names.

    Returns:
        dict: Mapping of partition mesh name to BS node name.
            Empty dict if source has no blendshapes.
    """
    bs_nodes = deformer.get_deformers(
        source_mesh, "blendShape"
    )
    if not bs_nodes:
        return {}

    # Disable all deformers except blendshapes on source
    saved_envelopes = deformer.disable_deformer_envelopes(
        source_mesh, exclude_types={"blendShape"}
    )

    result = {}

    try:
        for i, part_mesh in enumerate(partition_meshes):
            part_short = get_short_name(part_mesh)
            log.info(
                "  Transferring BS to %s (%d/%d)",
                part_short,
                i + 1,
                len(partition_meshes),
            )
            new_bs = _transfer_bs_to_partition(
                source_mesh, part_mesh, bs_nodes
            )
            if new_bs:
                result[part_mesh] = new_bs

    finally:
        deformer.restore_deformer_envelopes(saved_envelopes)

    return result


def _transfer_bs_to_partition(
    source_mesh, part_mesh, bs_nodes
):
    """Transfer blendshape targets to a single partition.

    Args:
        source_mesh (str): Source mesh transform.
        part_mesh (str): Partition mesh transform.
        bs_nodes (list): Source blendshape node names.

    Returns:
        str: New blendshape node name, or None if no targets.
    """
    # Create temp duplicate for wrap target
    temp_name = f"{part_mesh}_bs_transfer_temp"
    temp_dup = cmds.duplicate(
        part_mesh, rr=True, name=temp_name
    )[0]

    # Create wrap: temp dup follows source.
    # Returns (wrap_node, base_dup) -- base_dup is a static
    # mesh used for wrap reference that must be cleaned up.
    wrap_node, base_dup = deformer.create_wrap_deformer(
        temp_dup, source_mesh, use_base_duplicate=True
    )
    if not wrap_node:
        cmds.delete(temp_dup)
        if base_dup and cmds.objExists(base_dup):
            cmds.delete(base_dup)
        return None

    # Get temp dup shape for connection
    temp_shapes = cmds.listRelatives(
        temp_dup, shapes=True, type="mesh"
    )
    if not temp_shapes:
        cmds.delete(temp_dup)
        return None
    temp_shape = temp_shapes[0]

    # Create empty blendShape node on partition
    part_short = get_short_name(part_mesh)
    new_bs = cmds.deformer(
        part_mesh, type="blendShape",
        name=f"{part_short}_BS",
    )[0]

    has_targets = False

    for src_bs in bs_nodes:
        targets_idx = cmds.getAttr(
            f"{src_bs}.weight", multiIndices=True
        )
        if not targets_idx:
            continue

        for idx in targets_idx:
            target_name = cmds.aliasAttr(
                f"{src_bs}.weight[{idx}]", query=True
            )

            attr_name = blendshape.BS_TARGET_ITEM_ATTR.format(
                src_bs, idx
            )
            target_items = cmds.getAttr(
                attr_name, multiIndices=True
            )
            if not target_items:
                continue

            # Check for live connected targets
            if _has_live_target(attr_name, target_items):
                cmds.warning(
                    f"Skipping live target: {target_name}"
                )
                continue

            # Unlock/disconnect weight so we can set it
            weight_attr = f"{src_bs}.weight[{idx}]"
            saved_state = _unlock_and_disconnect_attr(
                weight_attr
            )

            try:
                for t_item in target_items:
                    weight = float(
                        (t_item - 5000) / 1000.0
                    )

                    # Trigger source BS
                    cmds.setAttr(weight_attr, weight)

                    # Capture via connect/disconnect
                    dest_attr = (
                        f"{new_bs}.inputTarget[0]"
                        f".inputTargetGroup[{idx}]"
                        f".inputTargetItem[{t_item}]"
                        ".inputGeomTarget"
                    )
                    cmds.connectAttr(
                        f"{temp_shape}.outMesh",
                        dest_attr,
                        force=True,
                    )
                    cmds.disconnectAttr(
                        f"{temp_shape}.outMesh",
                        dest_attr,
                    )

                # Reset weight before restoring
                cmds.setAttr(weight_attr, 0)

            finally:
                _restore_attr(weight_attr, saved_state)

            # Show weight attr and set alias
            cmds.setAttr(
                f"{new_bs}.weight[{idx}]", 0
            )
            if target_name:
                cmds.aliasAttr(
                    target_name,
                    f"{new_bs}.weight[{idx}]",
                )

            has_targets = True

    # Clean up temp objects. Delete wrap first to break
    # connections cleanly before removing the meshes.
    if cmds.objExists(wrap_node):
        cmds.delete(wrap_node)
    if base_dup and cmds.objExists(base_dup):
        cmds.delete(base_dup)
    if cmds.objExists(temp_dup):
        cmds.delete(temp_dup)

    if has_targets:
        return new_bs
    else:
        cmds.delete(new_bs)
        return None


def _has_live_target(attr_name, target_items):
    """Check if any target item has a live geometry input.

    Args:
        attr_name (str): The inputTargetItem base attr.
        target_items (list): List of target item indices.

    Returns:
        bool: True if any target has live connection.
    """
    for t_item in target_items:
        geom_attr = (
            f"{attr_name}[{t_item}].inputGeomTarget"
        )
        conns = cmds.listConnections(
            geom_attr, destination=False
        )
        if conns:
            return True
    return False


def _unlock_and_disconnect_attr(attr):
    """Temporarily unlock and disconnect an attribute.

    Returns state needed to restore via _restore_attr.

    Args:
        attr (str): Full attribute path (e.g. "node.weight[0]").

    Returns:
        dict: Saved state with keys "locked", "connection".
    """
    state = {"locked": False, "connection": None}

    if cmds.getAttr(attr, lock=True):
        state["locked"] = True
        cmds.setAttr(attr, lock=False)

    conns = cmds.listConnections(
        attr, source=True, destination=False,
        plugs=True,
    )
    if conns:
        state["connection"] = conns[0]
        cmds.disconnectAttr(conns[0], attr)

    return state


def _restore_attr(attr, state):
    """Restore attribute lock/connection from saved state.

    Args:
        attr (str): Full attribute path.
        state (dict): From _unlock_and_disconnect_attr.
    """
    if state["connection"]:
        try:
            cmds.connectAttr(
                state["connection"], attr, force=True
            )
        except RuntimeError:
            pass

    if state["locked"]:
        cmds.setAttr(attr, lock=True)


# =====================================================
# PIPELINE STEP 3: CLEAN UNUSED BS TARGETS
# =====================================================


def clean_unused_bs_targets(
    partition_meshes, threshold=0.0001
):
    """Remove blendshape targets with no visible effect.

    For each partition's blendShape node, tests each target by
    setting its weight to 1 and comparing vertex positions to
    base. Targets with max delta below threshold are removed.

    Args:
        partition_meshes (list): List of partition mesh names.
        threshold (float): Max delta to consider as no effect.
    """
    for part_mesh in partition_meshes:
        bs_nodes = deformer.get_deformers(
            part_mesh, "blendShape"
        )
        if not bs_nodes:
            continue

        for bs_node in bs_nodes:
            _clean_bs_node_targets(
                part_mesh, bs_node, threshold
            )


def _clean_bs_node_targets(mesh, bs_node, threshold):
    """Clean unused targets from a single BS node.

    Args:
        mesh (str): Mesh transform name.
        bs_node (str): BlendShape node name.
        threshold (float): Max delta threshold.
    """
    targets_idx = cmds.getAttr(
        f"{bs_node}.weight", multiIndices=True
    )
    if not targets_idx:
        cmds.delete(bs_node)
        return

    # Ensure all weights at 0 for base reference
    for idx in targets_idx:
        cmds.setAttr(f"{bs_node}.weight[{idx}]", 0)

    base_positions = _get_vertex_positions(mesh)

    targets_to_remove = []

    for idx in targets_idx:
        cmds.setAttr(f"{bs_node}.weight[{idx}]", 1)
        deformed_positions = _get_vertex_positions(mesh)
        cmds.setAttr(f"{bs_node}.weight[{idx}]", 0)

        # Compute max delta from flat position lists
        max_delta = 0.0
        for i in range(0, len(base_positions), 3):
            dx = deformed_positions[i] - base_positions[i]
            dy = (
                deformed_positions[i + 1]
                - base_positions[i + 1]
            )
            dz = (
                deformed_positions[i + 2]
                - base_positions[i + 2]
            )
            delta = (
                (dx * dx + dy * dy + dz * dz) ** 0.5
            )
            if delta > max_delta:
                max_delta = delta

        if max_delta < threshold:
            targets_to_remove.append(idx)

    # Remove unused targets (reverse order)
    for idx in reversed(targets_to_remove):
        alias = cmds.aliasAttr(
            f"{bs_node}.weight[{idx}]", query=True
        )
        if alias:
            cmds.aliasAttr(
                f"{bs_node}.weight[{idx}]",
                remove=True,
            )

        tgt_grp = (
            f"{bs_node}.inputTarget[0]"
            f".inputTargetGroup[{idx}]"
        )
        cmds.removeMultiInstance(tgt_grp, b=True)

        cmds.removeMultiInstance(
            f"{bs_node}.weight[{idx}]", b=True
        )

    if targets_to_remove:
        log.info(
            "  %s: removed %d/%d unused targets",
            get_short_name(mesh),
            len(targets_to_remove),
            len(targets_idx),
        )

    # Delete BS node if no targets remain
    remaining = cmds.getAttr(
        f"{bs_node}.weight", multiIndices=True
    )
    if not remaining:
        cmds.delete(bs_node)
        log.info(
            "  %s: deleted empty BS node",
            get_short_name(mesh),
        )


# =====================================================
# PIPELINE STEP 4: RECONNECT BS INPUTS
# =====================================================


def reconnect_bs_inputs(source_mesh, partition_meshes):
    """Replicate blendshape input connections on partitions.

    For each weight driven by an external connection on the
    source blendshape, connects the same driver to the
    corresponding weight on each partition's blendshape node.

    Args:
        source_mesh (str): The original source mesh transform.
        partition_meshes (list): List of partition mesh names.
    """
    src_bs_nodes = deformer.get_deformers(
        source_mesh, "blendShape"
    )
    if not src_bs_nodes:
        return

    for part_mesh in partition_meshes:
        part_bs_nodes = deformer.get_deformers(
            part_mesh, "blendShape"
        )
        if not part_bs_nodes:
            continue

        part_bs = part_bs_nodes[0]
        part_targets = cmds.getAttr(
            f"{part_bs}.weight", multiIndices=True
        ) or []

        for src_bs in src_bs_nodes:
            src_targets = cmds.getAttr(
                f"{src_bs}.weight", multiIndices=True
            ) or []

            for idx in src_targets:
                if idx not in part_targets:
                    continue

                # Check input connections on source weight
                src_attr = f"{src_bs}.weight[{idx}]"
                connections = cmds.listConnections(
                    src_attr,
                    source=True,
                    destination=False,
                    plugs=True,
                )

                dst_attr = f"{part_bs}.weight[{idx}]"

                if connections:
                    try:
                        cmds.connectAttr(
                            connections[0],
                            dst_attr,
                            force=True,
                        )
                    except RuntimeError:
                        pass
                else:
                    val = cmds.getAttr(src_attr)
                    cmds.setAttr(dst_attr, val)

            # Replicate envelope connection
            env_conns = cmds.listConnections(
                f"{src_bs}.envelope",
                source=True,
                destination=False,
                plugs=True,
            )
            if env_conns:
                try:
                    cmds.connectAttr(
                        env_conns[0],
                        f"{part_bs}.envelope",
                        force=True,
                    )
                except RuntimeError:
                    pass


# =====================================================
# PIPELINE STEP 5: COPY SKIN CLUSTERS
# =====================================================


def copy_skin_clusters(source_mesh, partition_meshes):
    """Copy skin cluster from source to each partition.

    Args:
        source_mesh (str): The original source mesh transform.
        partition_meshes (list): List of partition mesh names.

    Returns:
        dict: Mapping of partition mesh to skinCluster name.
            Empty dict if source has no skinCluster.
    """

    src_skin_node = skin.getSkinCluster(source_mesh)
    if not src_skin_node:
        log.warning(
            "No skinCluster found on %s", source_mesh
        )
        return {}

    result = {}

    for part_mesh in partition_meshes:
        part_short = get_short_name(part_mesh)
        skin_name = "{}_skinCluster".format(part_short)

        log.info(
            "Copying skin to %s", part_short
        )

        skin.skinCopy(
            source_mesh, part_mesh, name=skin_name
        )

        dst_skin_node = skin.getSkinCluster(part_mesh)
        if dst_skin_node:
            result[part_mesh] = dst_skin_node.name()
        else:
            log.warning(
                "skinCopy did not create skinCluster on %s",
                part_short,
            )

    return result


# =====================================================
# PIPELINE STEP 6: REMOVE UNUSED INFLUENCES
# =====================================================

def remove_unused_influences(partition_meshes):
    """Remove zero-weight influences from each partition.

    Uses Maya's built-in removeUnusedInfluences command
    on each partition mesh's skinCluster.

    Args:
        partition_meshes (list): List of partition mesh names.
    """
    for part_mesh in partition_meshes:
        skin_nodes = deformer.get_deformers(
            part_mesh, "skinCluster"
        )
        if not skin_nodes:
            continue

        skin = skin_nodes[0]
        cmds.skinCluster(
            skin, edit=True, removeUnusedInfluence=True
        )

        part_short = get_short_name(part_mesh)
        log.info(
            "  %s: removed unused influences",
            part_short,
        )


# =====================================================
# PIPELINE STEP 7: COPY SKIN CONFIGURATION
# =====================================================


def copy_skin_configuration(
    source_mesh, partition_meshes
):
    """Copy skinCluster settings and prebind connections.

    Copies skinCluster attributes (skinningMethod,
    normalizeWeights, deformUserNormals, DQS scale/support
    attributes) and replicates any prebind matrix input
    connections from the source skinCluster to each
    partition's skinCluster.

    DQS attributes (dqsScaleX/Y/Z, dqsSupportNonRigid)
    are copied as values. If they have input connections,
    those connections are replicated on the partition.

    Args:
        source_mesh (str): The original source mesh transform.
        partition_meshes (list): List of partition mesh names.
    """
    src_skins = deformer.get_deformers(
        source_mesh, "skinCluster"
    )
    if not src_skins:
        return

    src_skin = src_skins[0]

    # Attributes that are simple value copies
    skin_attrs = [
        "skinningMethod",
        "normalizeWeights",
        "deformUserNormals",
    ]

    # Attributes that may have values OR input connections
    connectable_attrs = [
        "dqsScaleX",
        "dqsScaleY",
        "dqsScaleZ",
        "dqsSupportNonRigid",
    ]

    for part_mesh in partition_meshes:
        part_skins = deformer.get_deformers(
            part_mesh, "skinCluster"
        )
        if not part_skins:
            continue

        part_skin = part_skins[0]

        # Copy simple skinCluster attributes
        for attr in skin_attrs:
            try:
                val = cmds.getAttr(f"{src_skin}.{attr}")
                cmds.setAttr(
                    f"{part_skin}.{attr}", val
                )
            except RuntimeError:
                pass

        # Copy connectable attributes (value or connection)
        for attr in connectable_attrs:
            _copy_attr_or_connection(
                src_skin, part_skin, attr
            )

        # Copy prebind matrix connections
        _copy_prebind_connections(src_skin, part_skin)


def _copy_attr_or_connection(src_node, dst_node, attr):
    """Copy an attribute value or replicate its connection.

    If the attribute on src_node has an input connection,
    the same driver is connected to the dst_node attribute.
    Otherwise, the current value is copied.

    Args:
        src_node (str): Source node name.
        dst_node (str): Destination node name.
        attr (str): Attribute name.
    """
    src_attr = f"{src_node}.{attr}"
    dst_attr = f"{dst_node}.{attr}"

    if not cmds.objExists(src_attr):
        return
    if not cmds.objExists(dst_attr):
        return

    # Check for input connection
    conns = cmds.listConnections(
        src_attr,
        source=True,
        destination=False,
        plugs=True,
    )
    if conns:
        try:
            cmds.connectAttr(
                conns[0], dst_attr, force=True
            )
        except RuntimeError:
            pass
    else:
        try:
            val = cmds.getAttr(src_attr)
            cmds.setAttr(dst_attr, val)
        except RuntimeError:
            pass


def _copy_prebind_connections(src_skin, part_skin):
    """Copy prebind matrix connections between skins.

    Maps by influence name since matrix indices may differ
    between source and partition skinClusters.

    Args:
        src_skin (str): Source skinCluster node.
        part_skin (str): Partition skinCluster node.
    """
    src_matrix_indices = cmds.getAttr(
        f"{src_skin}.matrix", multiIndices=True
    ) or []

    for src_idx in src_matrix_indices:
        prebind_attr = (
            f"{src_skin}.bindPreMatrix[{src_idx}]"
        )
        connections = cmds.listConnections(
            prebind_attr,
            source=True,
            destination=False,
            plugs=True,
        )
        if not connections:
            continue

        # Find which influence is at this index
        matrix_attr = f"{src_skin}.matrix[{src_idx}]"
        inf_conns = cmds.listConnections(
            matrix_attr,
            source=True,
            destination=False,
        )
        if not inf_conns:
            continue
        inf_name = inf_conns[0]

        # Find matching index in partition skin
        part_matrix_indices = cmds.getAttr(
            f"{part_skin}.matrix", multiIndices=True
        ) or []

        for p_idx in part_matrix_indices:
            p_matrix_attr = (
                f"{part_skin}.matrix[{p_idx}]"
            )
            p_inf_conns = cmds.listConnections(
                p_matrix_attr,
                source=True,
                destination=False,
            )
            if (
                p_inf_conns
                and p_inf_conns[0] == inf_name
            ):
                p_prebind = (
                    f"{part_skin}"
                    f".bindPreMatrix[{p_idx}]"
                )
                try:
                    cmds.connectAttr(
                        connections[0],
                        p_prebind,
                        force=True,
                    )
                except RuntimeError:
                    pass
                break


# =====================================================
# PIPELINE STEP 8: PROXIMITY WRAP PROXY
# =====================================================


def create_proximity_wrap_proxy(
    source_mesh, partition_meshes, group_node,
    manager=None,
):
    """Create a proxy mesh driven by proximity wrap.

    Duplicates the source mesh in bind pose and applies a
    proximity wrap deformer driven by all partition meshes.
    This reassembly mesh follows the combined deformation
    of all partitions.

    Args:
        source_mesh (str): The original source mesh transform.
        partition_meshes (list): List of partition mesh names.
        group_node (str): Partitions group for parenting.
        manager (PolygonGroupManager): Optional manager for
            shader state management.

    Returns:
        str: The proxy mesh transform name, or None if failed.
    """
    if not partition_meshes:
        return None

    mesh_short = get_short_name(source_mesh)

    # Temporarily restore original shaders
    was_showing = False
    if manager and manager.showing_partitions:
        was_showing = True
        if manager.original_shading:
            show_original_shaders(manager)

    # Disable deformers for bind-pose duplicate
    saved_envelopes = deformer.disable_deformer_envelopes(source_mesh)

    try:
        proxy_name = f"{mesh_short}_proxy"
        proxy = cmds.duplicate(
            source_mesh, rr=True, name=proxy_name
        )[0]

        for attr in (
            "translateX", "translateY",
            "translateZ",
            "rotateX", "rotateY", "rotateZ",
            "scaleX", "scaleY", "scaleZ",
        ):
            cmds.setAttr(
                f"{proxy}.{attr}", lock=False
            )

        cmds.delete(proxy, ch=True)

    finally:
        deformer.restore_deformer_envelopes(saved_envelopes)

    # Restore shader state
    if was_showing and manager:
        show_partition_shaders(manager)

    deformer.create_proximity_wrap(
        target_geos=[proxy],
        driver_geos=partition_meshes,
        deformer_name="{}_proximityWrap".format(
            mesh_short
        ),
    )

    # Parent proxy under partitions group
    if cmds.objExists(group_node):
        cmds.parent(proxy, group_node)

    return proxy


# =====================================================
# EXECUTION PIPELINE
# =====================================================


@utils.one_undo
def execute_full_pipeline(manager):
    """Run the complete evaluation partition pipeline.

    Orchestrates all 8 steps: split groups, transfer
    blendshapes, clean unused targets, reconnect inputs,
    copy skin, remove unused influences, copy skin config,
    and create proximity wrap proxy.

    Only transfers deformers that exist on the source mesh.
    Blendshape steps (2-4) and skin steps (5-7) are skipped
    if the source has no corresponding deformer.

    Shows a Maya progress bar and logs each step.

    Args:
        manager (PolygonGroupManager): The manager with
            groups defined.

    Returns:
        tuple: (group_node, partition_meshes, proxy_mesh).
            Returns (None, [], None) if execution failed.
    """
    if not manager or not manager.groups:
        cmds.warning("No groups defined.")
        return None, [], None

    source = manager.mesh
    source_short = get_short_name(source)

    # Count total steps for progress bar
    total_steps = 8
    bar = _progress_start(
        "Evaluation Partition: starting...",
        total_steps,
    )

    try:
        # Step 1: Split polygon groups
        _progress_update(
            bar, "Step 1/8: Splitting polygon groups..."
        )
        log.info(
            "Step 1/8: Splitting polygon groups on %s",
            source_short,
        )

        grp, partitions = split_polygon_groups(manager)
        if not grp:
            return None, [], None

        log.info(
            "  Created %d partitions", len(partitions)
        )

        # Re-resolve source mesh path in case DAG
        # changed during split.
        if not cmds.objExists(source):
            short = get_short_name(source)
            resolved = cmds.ls(short, long=True)
            if resolved:
                source = resolved[0]
            else:
                cmds.warning(
                    "Source mesh no longer exists "
                    "after split."
                )
                return grp, partitions, None

        # Detect which deformers exist on source
        has_bs = bool(
            deformer.get_deformers(
                source, "blendShape"
            )
        )
        has_skin = bool(
            deformer.get_deformers(
                source, "skinCluster"
            )
        )

        # Step 2: Transfer blendshapes
        _progress_update(
            bar, "Step 2/8: Transferring blendshapes..."
        )
        if has_bs:
            log.info(
                "Step 2/8: Transferring blendshapes"
            )
            transfer_blendshapes(source, partitions)
        else:
            log.info(
                "Step 2/8: Skipped (no blendshapes)"
            )

        # Step 3: Clean unused BS targets
        _progress_update(
            bar,
            "Step 3/8: Cleaning unused BS targets...",
        )
        if has_bs:
            log.info(
                "Step 3/8: Cleaning unused BS targets"
            )
            clean_unused_bs_targets(partitions)
        else:
            log.info("Step 3/8: Skipped")

        # Step 4: Reconnect BS inputs
        _progress_update(
            bar,
            "Step 4/8: Reconnecting BS inputs...",
        )
        if has_bs:
            log.info(
                "Step 4/8: Reconnecting BS inputs"
            )
            reconnect_bs_inputs(source, partitions)
        else:
            log.info("Step 4/8: Skipped")

        # Step 5: Copy skin clusters
        _progress_update(
            bar,
            "Step 5/8: Copying skin clusters...",
        )
        if has_skin:
            log.info(
                "Step 5/8: Copying skin clusters"
            )
            copy_skin_clusters(source, partitions)
        else:
            log.info(
                "Step 5/8: Skipped (no skinCluster)"
            )

        # Step 6: Remove unused influences
        _progress_update(
            bar,
            "Step 6/8: Removing unused influences...",
        )
        if has_skin:
            log.info(
                "Step 6/8: Removing unused influences"
            )
            remove_unused_influences(partitions)
        else:
            log.info("Step 6/8: Skipped")

        # Step 7: Copy skin configuration
        _progress_update(
            bar,
            "Step 7/8: Copying skin configuration...",
        )
        if has_skin:
            log.info(
                "Step 7/8: Copying skin configuration"
            )
            copy_skin_configuration(source, partitions)
        else:
            log.info("Step 7/8: Skipped")

        # Step 8: Proximity wrap proxy
        _progress_update(
            bar,
            "Step 8/8: Creating proximity wrap proxy...",
        )
        log.info(
            "Step 8/8: Creating proximity wrap proxy"
        )
        proxy = create_proximity_wrap_proxy(
            source, partitions, grp, manager
        )

        log.info(
            "Pipeline complete: %d partitions%s",
            len(partitions),
            " + proxy" if proxy else "",
        )

        return grp, partitions, proxy

    finally:
        _progress_end(bar)


# =====================================================
# CONFIGURATION EXPORT/IMPORT
# =====================================================


def group_to_dict(group):
    """Convert a PolygonGroup to a dictionary.

    Args:
        group (PolygonGroup): The PolygonGroup to convert.

    Returns:
        dict: Dictionary representation of the group.
    """
    return {
        "name": group.name,
        "color": list(group.color),
        "face_indices": sorted(group.face_indices),
    }


def dict_to_group_data(data):
    """Convert a dictionary to group data (without shader).

    Args:
        data (dict): Dictionary with group data.

    Returns:
        dict: Processed group data with proper types.
    """
    return {
        "name": data["name"],
        "color": tuple(data["color"]),
        "face_indices": set(data["face_indices"]),
    }


def manager_to_config(manager):
    """Convert a PolygonGroupManager to a configuration dictionary.

    This is the main configuration format that can be exported to JSON
    and used for scripting/automation.

    Args:
        manager (PolygonGroupManager): The PolygonGroupManager to convert.

    Returns:
        dict: Configuration dictionary ready for JSON export.
    """
    return {
        "version": CONFIG_VERSION,
        "mesh": manager.mesh,
        "mesh_short_name": manager._mesh_short_name,
        "groups": [group_to_dict(g) for g in manager.groups],
    }


def export_configuration(file_path, manager):
    """Export configuration to a JSON file.

    Args:
        file_path (str): Path to save the configuration file.
        manager (PolygonGroupManager): The PolygonGroupManager to export.

    Returns:
        bool: True if export was successful, False otherwise.
    """
    if not file_path.endswith(CONFIG_FILE_EXT):
        file_path += CONFIG_FILE_EXT

    config = manager_to_config(manager)

    try:
        with open(file_path, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except IOError as e:
        cmds.warning(f"Failed to export configuration: {e}")
        return False


def import_configuration(file_path):
    """Import configuration from a JSON file.

    Args:
        file_path (str): Path to the configuration file.

    Returns:
        dict: Configuration dictionary, or None if import failed.
    """
    try:
        with open(file_path, "r") as f:
            config = json.load(f)
        return config
    except (IOError, json.JSONDecodeError) as e:
        cmds.warning(f"Failed to import configuration: {e}")
        return None


def apply_configuration(config, mesh=None, create_shaders=True):
    """Apply a configuration to create a PolygonGroupManager.

    This is the main entry point for scripting - pass a configuration
    dictionary and get a fully initialized manager with shaders.

    Args:
        config (dict): Configuration dictionary (from import or manual creation).
        mesh (str): Override mesh name (uses config mesh if None).
        create_shaders (bool): Whether to create shaders and assign faces.

    Returns:
        PolygonGroupManager: Initialized PolygonGroupManager, or None if failed.

    Example:
        >>> config = {
        ...     "version": "1.0",
        ...     "mesh": "pCube1",
        ...     "groups": [
        ...         {"name": "All Faces", "color": [0.5, 0.6, 0.7], "face_indices": [0, 1, 2]},
        ...         {"name": "Head", "color": [0.8, 0.5, 0.5], "face_indices": [3, 4, 5]},
        ...     ]
        ... }
        >>> manager = apply_configuration(config)
    """
    target_mesh = mesh or config.get("mesh")
    if not target_mesh:
        cmds.warning("No mesh specified in configuration.")
        return None

    if not cmds.objExists(target_mesh):
        cmds.warning(f"Mesh '{target_mesh}' does not exist.")
        return None

    # Create manager
    manager = PolygonGroupManager(target_mesh)

    # Process groups from config
    groups_data = config.get("groups", [])
    if not groups_data:
        cmds.warning("No groups found in configuration.")
        return None

    for group_data in groups_data:
        name = group_data.get("name", "Unnamed")
        color = tuple(group_data.get("color", generate_muted_color()))
        face_indices = set(group_data.get("face_indices", []))

        if create_shaders:
            # Create shader
            shader_base_name = (
                f"{SHADER_PREFIX}_{manager._mesh_short_name}_{name.replace(' ', '_')}"
            )
            shader_node, shading_group = create_partition_shader(
                shader_base_name, color
            )

            # Assign faces
            if face_indices:
                assign_faces_to_shader(target_mesh, face_indices, shading_group)
        else:
            shader_node = ""
            shading_group = ""

        # Create group
        group = PolygonGroup(
            name=name,
            color=color,
            face_indices=face_indices,
            shader_node=shader_node,
            shading_group=shading_group,
        )
        manager.groups.append(group)

    return manager


def execute_from_config(config, mesh=None):
    """Execute the partition tool from a configuration dictionary.

    Args:
        config (dict): Configuration dictionary.
        mesh (str): Override mesh name (uses config mesh if None).

    Returns:
        PolygonGroupManager: Initialized PolygonGroupManager with shaders applied.

    Example:
        >>> config = {
        ...     "version": "1.0",
        ...     "mesh": "pSphere1",
        ...     "groups": [
        ...         {"name": "All Faces", "color": [0.6, 0.7, 0.6], "face_indices": list(range(100))},
        ...         {"name": "Top", "color": [0.8, 0.5, 0.5], "face_indices": list(range(100, 200))},
        ...     ]
        ... }
        >>> manager = execute_from_config(config)
    """
    return apply_configuration(config, mesh=mesh, create_shaders=True)


def execute_from_file(file_path, mesh=None):
    """Execute the partition tool directly from a .evp configuration file.

    This is the main entry point for pipeline automation and scripting.
    Loads the configuration from file and applies it with all shaders.

    Args:
        file_path (str): Path to the .evp configuration file.
        mesh (str): Override mesh name (uses mesh from config file if None).

    Returns:
        PolygonGroupManager: Initialized PolygonGroupManager with shaders applied,
            or None if failed.

    Example:
        >>> from mgear.rigbits import evaluation_partition
        >>>
        >>> # Execute directly from file - mesh is stored in the config
        >>> manager = evaluation_partition.execute_from_file("character_partition.evp")
        >>>
        >>> # Or override the mesh for a different character
        >>> manager = evaluation_partition.execute_from_file(
        ...     "body_partition.evp",
        ...     mesh="other_character_body"
        ... )
    """
    config = import_configuration(file_path)
    if not config:
        return None

    return apply_configuration(config, mesh=mesh, create_shaders=True)
