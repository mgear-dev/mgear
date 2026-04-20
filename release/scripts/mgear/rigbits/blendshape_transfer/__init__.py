"""混合形状传输。

多源混合形状传输工具。将多个源网格的目标堆叠到
目标网格的单个 blendShape 节点中。支持导入/导出 .bst 配置文件。
"""

__version__ = "1.0.0"

from maya import cmds

from mgear.core import pyqt

from .ui import BlendshapeTransferUI


def show(*args):
    """显示混合形状传输 UI。

    返回：
        BlendshapeTransferUI: UI 实例。
    """
    workspace_control = (
        BlendshapeTransferUI.TOOL_NAME + "WorkspaceControl"
    )
    if cmds.workspaceControl(workspace_control, exists=True):
        cmds.deleteUI(workspace_control)

    return pyqt.showDialog(
        BlendshapeTransferUI, dockable=True
    )
