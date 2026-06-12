"""Matcap Viewer.

Browse and apply matcap (Material Capture) shaders to viewport
meshes with one-click toggle between matcap and original materials.

Example:
    from mgear.utilbits import matcap_viewer
    matcap_viewer.show()
    matcap_viewer.toggle()  # hotkey-friendly
"""

__version__ = "1.0.0"

from maya import cmds

from .ui import MatcapViewerUI

_window = None


def show(*args):
    """Show the Matcap Viewer UI.

    Returns:
        MatcapViewerUI: The UI instance.
    """
    global _window

    control = MatcapViewerUI.TOOL_NAME + "WorkspaceControl"
    if cmds.workspaceControl(control, query=True, exists=True):
        cmds.workspaceControl(control, edit=True, close=True)
        cmds.deleteUI(control, control=True)

    _window = MatcapViewerUI()
    _window.show(dockable=True)
    return _window


def toggle(*args):
    """Toggle matcap material on/off.

    Works without the UI being open. Uses the last-used
    texture from QSettings if no shader graph exists yet.

    Returns:
        bool: New matcap active state.
    """
    from . import core
    from .ui import _SK_LAST_TEXTURE

    if not core.shader_graph_exists():
        from mgear.core import pyqt

        settings = pyqt.SettingsMixin.create_qsettings_object(None)
        last_texture = settings.value(_SK_LAST_TEXTURE, "")
        if last_texture:
            core.create_shader_graph()
            core.set_texture(last_texture)
        else:
            cmds.warning(
                "No matcap texture set. Open the Matcap Viewer "
                "and select a matcap first."
            )
            return False

    return core.toggle_matcap()
