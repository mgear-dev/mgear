import maya.cmds as cmds
import mgear

from mgear.core import string

menuID = "ueGear"


def install():
    """Installs ueGear sub-menu"""

    cmds.setParent(mgear.menu_id, menu=True)
    cmds.menuItem(divider=True)
    commands = (
        (
            "为选定节点应用ueGear标签",
            str_auto_tag,
            "mgear_ue_tag_add.svg",
        ),
        (
            "从选定节点移除ueGear标签",
            str_remove_tag,
            "mgear_ue_tag_remove.svg",
        ),
        ("-----", None),
        (
            "从Unreal导入选定资产",
            str_import_selected_assets_from_unreal,
            "mgear_ue_import.svg",
        ),
        (
            "将选定资产导出到Unreal",
            str_export_selected_assets_to_unreal,
            "mgear_ue_export.svg",
        ),
        ("-----", None),
        (
            "从Sequencer导入选定摄像机",
            str_import_selected_cameras_from_unreal,
            "mgear_ue_camera_import.svg",
        ),
        (
            "从Maya选择更新Sequencer摄像机",
            str_update_sequencer_camera_from_maya,
            "mgear_ue_camera_update.svg",
        ),
        ("-----", None),
        (
            "从Unreal关卡导入选定资产",
            str_import_selected_assets_from_level_unreal,
            "mgear_ue_level_import.svg",
        ),
        (
            "从Maya选择更新Unreal资产",
            str_update_unreal_Assets_from_Maya_Selection,
            "mgear_ue_update.svg",
        ),
    )

    mgear.menu.install(menuID, commands, image="UE5.svg")


str_auto_tag = """
from mgear.uegear import tag
tag.auto_tag()
"""

str_remove_tag = """
from mgear.uegear import tag
tag.remove_all_tags()
"""

str_import_selected_assets_from_unreal = """
from mgear.uegear import commands
commands.import_selected_assets_from_unreal()
"""

str_export_selected_assets_to_unreal = """
from mgear.uegear import commands
commands.export_selected_assets_to_unreal()
"""

str_import_selected_cameras_from_unreal = """
from mgear.uegear import commands
commands.import_selected_cameras_from_unreal()
"""

str_update_sequencer_camera_from_maya = """
from mgear.uegear import commands
commands.update_sequencer_camera_from_maya()
"""

str_import_selected_assets_from_level_unreal = """
from mgear.uegear import commands
commands.import_layout_from_unreal()
"""

str_update_unreal_Assets_from_Maya_Selection = """
from mgear.uegear import commands
commands.update_selected_transforms()
"""
