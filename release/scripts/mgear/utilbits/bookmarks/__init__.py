"""Bookmarks Tool.

Save and recall object/component selections and isolate visibility
states in Maya. Bookmarks persist in the scene and can be exported
to .sbk files.

Example:
    from mgear.utilbits import bookmarks
    bookmarks.show()
"""

__version__ = "1.0.0"

from maya import cmds

from .ui import BookmarksUI

_window = None


def show(*args):
    """Show the Bookmarks Tool UI.

    Returns:
        BookmarksUI: The UI instance.
    """
    global _window

    control = BookmarksUI.TOOL_NAME + "WorkspaceControl"
    if cmds.workspaceControl(control, query=True, exists=True):
        cmds.workspaceControl(control, edit=True, close=True)
        cmds.deleteUI(control, control=True)

    _window = BookmarksUI()
    _window.show(dockable=True)
    return _window
