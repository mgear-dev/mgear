"""Blendshape Transfer.

Multi-source blendshape transfer tool. Stacks targets from
multiple source meshes into a single blendShape node on a
target mesh. Supports import/export of .bst config files.
"""

__version__ = "1.0.0"

from maya import cmds

from mgear.core import pyqt

from .ui import BlendshapeTransferUI


def show(*args):
    """Show the Blendshape Transfer UI.

    Returns:
        BlendshapeTransferUI: The UI instance.
    """
    workspace_control = (
        BlendshapeTransferUI.TOOL_NAME + "WorkspaceControl"
    )
    if cmds.workspaceControl(workspace_control, exists=True):
        cmds.deleteUI(workspace_control)

    return pyqt.showDialog(
        BlendshapeTransferUI, dockable=True
    )
