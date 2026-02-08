"""Evaluation Partition Tool - Core Module.

This module provides core functionality for the Evaluation Partition Tool,
including data structures, color generation, shader management, face assignment,
and configuration import/export.
"""

import colorsys
import json
import random

from maya import cmds


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
