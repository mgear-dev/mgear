"""Guide Template Manager.

A browsable template manager for Shifter guide templates (.sgt files).
Supports custom source folders, thumbnails, metadata, and flexible
import options (full, add-to-guide, partial with component selection).
"""

__version__ = "1.0.0"

from maya import cmds

from mgear.core import pyqt

from .ui import GuideTemplateManagerUI


def show(*args):
    """Show the Guide Template Manager UI.

    Returns:
        GuideTemplateManagerUI: The UI instance.
    """
    workspace_control = (
        GuideTemplateManagerUI.TOOL_NAME + "WorkspaceControl"
    )
    if cmds.workspaceControl(workspace_control, exists=True):
        cmds.deleteUI(workspace_control)

    return pyqt.showDialog(GuideTemplateManagerUI, dockable=True)
