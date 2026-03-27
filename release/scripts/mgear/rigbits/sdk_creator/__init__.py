"""SDK Creator.

Creates Set Driven Key setups from timeline poses. Reads
keyframed poses, creates SDK transform nodes with animCurve
and blendWeighted graphs driven by UIHost attributes. Supports
export/import of ``.sdkc`` configurations and mirroring.
"""

__version__ = "1.0.0"

from maya import cmds

from mgear.core import pyqt

from .ui import SDKCreatorUI
from .core import apply_from_file
from .core import create_sdk_setup
from .core import export_config
from .core import import_config
from .core import mirror_config
from .core import mirror_sdk_setup


def show(*args):
    """Show the SDK Creator UI.

    Returns:
        SDKCreatorUI: The UI instance.
    """
    workspace_control = (
        SDKCreatorUI.TOOL_NAME + "WorkspaceControl"
    )
    if cmds.workspaceControl(workspace_control, exists=True):
        cmds.deleteUI(workspace_control)

    return pyqt.showDialog(SDKCreatorUI, dockable=True)
