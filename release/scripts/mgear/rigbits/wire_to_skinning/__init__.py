"""Wire to Skinning Tool.

A comprehensive tool for:
1. Creating wire deformers from edge loops or joints
2. Converting wire deformers to skin clusters using de Boor algorithm

Supports multiple wire deformers on the same object.
Includes configuration export/import functionality.

Example:
    >>> from mgear.rigbits import wire_to_skinning
    >>> wire_to_skinning.show()
"""

__version__ = "1.0.0"

from maya import cmds

from mgear.core import pyqt

from .ui import WireToSkinningUI


def show(*args):
    """Show the Wire to Skinning Tool UI.

    Returns:
        WireToSkinningUI: The UI instance.
    """
    # Delete existing workspace control if it exists
    workspace_control = WireToSkinningUI.TOOL_NAME + "WorkspaceControl"
    if cmds.workspaceControl(workspace_control, exists=True):
        cmds.deleteUI(workspace_control)

    return pyqt.showDialog(WireToSkinningUI, dockable=True)


# Expose core functions and constants for scripting access
from .core import (
    # Constants
    CONFIG_FILE_EXT,
    # Functions - Wire/Curve info
    get_curve_info,
    get_wire_deformer_info,
    get_wire_weight_map,
    get_mesh_wire_deformers,
    get_curve_connected_joints,
    # Functions - Skin info
    get_mesh_skin_cluster,
    get_existing_skin_weights,
    ensure_static_joint_exists,
    # Functions - Weight computation
    compute_skin_weights_deboor,
    # Functions - Wire from edges
    get_edges_positions,
    create_curve_from_positions,
    create_wire_deformer,
    # Functions - Wire from joints
    create_curve_from_joints,
    connect_curve_to_joints,
    create_wire_from_joints,
    get_ordered_joints,
    # Functions - Skinning
    create_joints_at_cvs,
    create_skin_cluster,
    # Functions - Configuration
    export_configuration,
    import_configuration,
)
