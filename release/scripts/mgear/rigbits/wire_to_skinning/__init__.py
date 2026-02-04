"""Wire to Skinning Tool.

A comprehensive tool for:
1. Creating wire deformers from edge loops
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


# Expose core functions for scripting access
from .core import (
    get_curve_info,
    get_wire_deformer_info,
    get_wire_weight_map,
    get_mesh_wire_deformers,
    ensure_static_joint_exists,
    compute_skin_weights_deboor,
    get_edges_positions,
    create_curve_from_positions,
    create_wire_deformer,
    create_joints_at_cvs,
    create_skin_cluster,
    export_configuration,
    import_configuration,
)
