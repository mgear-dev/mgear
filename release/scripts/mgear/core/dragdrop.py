"""
drag and drop logic for mGear overrides of maya's default behavior
"""

# Stdlib imports
from __future__ import absolute_import

from functools import partial

# Maya imports
from maya import mel
from maya import cmds
import mgear.pymaya as pm

# mGear
import mgear
from mgear.shifter import io
from mgear.core import skin
from mgear.rigbits import rbf_io
from mgear.rigbits import wire_to_skinning

# mel override procs
MEL_OVERRIDE_CMD = r"""
//  Override the default performFileDropAction with mGears, with user approval
//  Use: Enable from the mGear > Utilities > Enable mGear file drop
//  Shout out Randall Hess

global proc int
performFileDropAction (string $theFile)
{
    string $pycmd = "from mgear.core import dragdrop;dragdrop.mgear_file_drop_action(\"" + $theFile + "\")";
    int $result = python($pycmd);
    return($result);
}
"""


# file drop functions ---------------------------------------------------------


def get_original_file_drop_action():
    """get the original performOriginalFileDropAction.mel, but check
    for custom override mel from another source first

    Returns:
        str: path to PerformFileDropAction.mel, custom or AD
    """
    # look for custom performFileDropAction
    mel_string_start = "Mel procedure found in: "
    orig_mel_file_str = mel.eval("whatIs performFileDropAction")
    if orig_mel_file_str.startswith(mel_string_start):
        return orig_mel_file_str.replace(mel_string_start, "")

    # if not custom, find vanilla AD
    mel_string_start = "Script found in: "
    orig_mel_file_str = mel.eval("whatIs performFileDropAction.mel")
    if orig_mel_file_str.startswith(mel_string_start):
        return orig_mel_file_str.replace(mel_string_start, "")


def get_mgear_file_drop_state():
    """get the option variable from maya to check if mGear override
    is requested

    Returns:
        int: 0 or 1, state of override
    """
    if not cmds.optionVar(exists="mgear_file_drop_OV"):
        cmds.optionVar(intValue=("mgear_file_drop_OV", 0))
    return cmds.optionVar(query="mgear_file_drop_OV")


def set_mgear_file_drop_state(state):
    """set the override state with maya option variable

    Args:
        state (bool, int): 0, 1, True, False
    """
    cmds.optionVar(intValue=("mgear_file_drop_OV", int(state)))


def mgear_file_drop_toggle(new_state):
    """toggle the state of the mgear override. False will reuse original

    Args:
        new_state (bool): from checkbox UI
    """
    set_mgear_file_drop_state(new_state)
    if new_state:
        mel_cmd = MEL_OVERRIDE_CMD
    else:
        if _ORIGINAL_FILEDROP_FILEPATH:
            mel_cmd = 'source "{}";'.format(_ORIGINAL_FILEDROP_FILEPATH)
        else:
            mel_cmd = 'source performFileDropAction.mel'
    mel.eval(mel_cmd)


def mgear_file_drop_action(theFile):
    """This action is called from the mGearFileDropAction.mel override

    Args:
        theFile (str): filepath from the maya drop action

    Returns:
        int: always return 1, to accept the drop action
    """
    if theFile.endswith(".sgt"):
        print("导入 mGear 导引文件：{}".format(theFile))
        guide_file_prompt(theFile)
    elif theFile.endswith(skin.PACK_EXT):
        print("导入 mGear 蒙皮包文件：{}".format(theFile))
        skin.importSkinPack(theFile)
    elif theFile.endswith(skin.FILE_EXT) or theFile.endswith(skin.FILE_JSON_EXT):
        print("导入 mGear 蒙皮文件：{}".format(theFile))
        skin.importSkin(theFile)
    elif theFile.endswith(rbf_io.RBF_FILE_EXTENSION):
        print("导入 mGear RBF 配置文件：{}".format(theFile))
        rbf_io.importRBFs(theFile)
    elif theFile.endswith(wire_to_skinning.CONFIG_FILE_EXT):
        print("导入线到蒙皮配置文件：{}".format(theFile))
        wire_to_skinning_file_prompt(theFile)
    else:
        mel.eval('performFileImportAction("{}");'.format(theFile))
    return 1


def guide_file_prompt(guide_filePath):
    """prompt dialogue for what to do with the .sgt, guide file

    Args:
        guide_filePath (str): filepath to guide
    """
    results = cmds.confirmDialog(title="mGear 导引文件",
                                 message="导入还是构建导引文件？",
                                 button=["导入", "构建", "取消"],
                                 defaultButton="导入",
                                 cancelButton="取消",
                                 dismissString="取消")
    if results == "导入":
        io.import_guide_template(filePath=guide_filePath)
    elif results == "构建":
        io.build_from_file(filePath=guide_filePath)
    else:
        pass


def wire_to_skinning_file_prompt(wts_filePath):
    """Prompt dialogue for importing a .wts wire to skinning config file.

    Args:
        wts_filePath (str): filepath to .wts configuration file
    """
    # Get selected mesh or prompt user
    selection = cmds.ls(selection=True, type="transform")
    mesh = None

    if selection:
        # Check if selection has a mesh shape
        for sel in selection:
            shapes = cmds.listRelatives(sel, shapes=True, type="mesh")
            if shapes:
                mesh = sel
                break

    if mesh:
        message = (
            "将线配置导入到选定的网格？\\n\\n"
            "网格：{}\\n文件：{}".format(mesh, wts_filePath)
        )
        buttons = ["导入", "取消"]
    else:
        message = (
            "未选择网格。\\n\\n"
            "选择一个网格并重试，或者使用配置文件中存储的网格名称导入。\\n\\n"
            "文件：{}".format(wts_filePath)
        )
        buttons = ["导入（使用存储的网格）", "取消"]

    results = cmds.confirmDialog(
        title="线到蒙皮",
        message=message,
        button=buttons,
        defaultButton=buttons[0],
        cancelButton="取消",
        dismissString="取消",
    )

    if results != "取消":
        wire_to_skinning.import_configuration(wts_filePath, target_mesh=mesh)


def install_utils_menu(m):
    """Install core utils submenu

    Args:
        m (pymel.ui): where to parent the menuItem
    """

    # get state
    state = get_mgear_file_drop_state()
    if state:
        mgear_file_drop_toggle(state)

    pm.setParent(m, menu=True)
    pm.menuItem(divider=True)
    cmds.menuItem("mgear_file_drop_menuitem",
                  label="启用 mGear 文件拖放",
                  command=mgear_file_drop_toggle,
                  checkBox=state)
    cmds.menuItem(divider=True)


try:
    # The variable is declared when the module is sourced
    # The idea being to find the performFilePathAction.mel preceeding
    # the mgear override
    _ORIGINAL_FILEDROP_FILEPATH
except NameError as e:
    _ORIGINAL_FILEDROP_FILEPATH = get_original_file_drop_action()
