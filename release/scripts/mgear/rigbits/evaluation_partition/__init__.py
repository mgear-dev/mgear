"""Evaluation Partition Tool.

A tool for partitioning mesh polygons into groups for improved parallel
evaluation performance in Maya.
"""

__version__ = "1.0.0"

from maya import cmds

from mgear.core import pyqt

from .ui import EvaluationPartitionUI


def show(*args):
    """Show the Evaluation Partition Tool UI.

    Returns:
        EvaluationPartitionUI: The UI instance.
    """
    # Delete existing workspace control if it exists
    workspace_control = EvaluationPartitionUI.TOOL_NAME + "WorkspaceControl"
    if cmds.workspaceControl(workspace_control, exists=True):
        cmds.deleteUI(workspace_control)

    return pyqt.showDialog(EvaluationPartitionUI, dockable=True)


# Expose core classes and functions for scripting access
from .core import (
    # Data classes
    PolygonGroup,
    PolygonGroupManager,
    # Constants
    CONFIG_FILE_EXT,
    CONFIG_VERSION,
    DEFAULT_GROUP_NAME,
    DEFAULT_SATURATION_RANGE,
    DEFAULT_VALUE_RANGE,
    SHADER_PREFIX,
    # Utility functions
    get_short_name,
    names_match,
    # Color functions
    generate_muted_color,
    # Shader functions
    create_partition_shader,
    delete_partition_shader,
    update_shader_color,
    rename_shader,
    # Face assignment functions
    assign_faces_to_shader,
    get_all_face_indices,
    get_selected_faces,
    # Group management functions
    create_default_group,
    create_group_from_selection,
    remove_group,
    update_group_color,
    rename_group,
    cleanup_all_shaders,
    reset_to_default,
    # Shader toggle functions
    capture_original_shading,
    show_partition_shaders,
    show_original_shaders,
    toggle_shaders,
    # Configuration functions
    group_to_dict,
    dict_to_group_data,
    manager_to_config,
    export_configuration,
    import_configuration,
    apply_configuration,
    execute_from_config,
    execute_from_file,
)
