from maya import cmds
import mgear.pymaya as pm

import mgear
import mgear.menu
from mgear.core import pyqt


str_open_picker_mode = """
from mgear import anim_picker
anim_picker.load(False, False)
"""

str_open_dockable_mode = """
from mgear import anim_picker
anim_picker.load(False, True)
"""

str_open_edit_mode = """
from mgear import anim_picker
anim_picker.load(True, False)
"""


def refresh_passthrough(*args):
    """Re-evaluate the click-through mask on every open anim picker.

    Each floating picker applies or clears its empty-area passthrough mask
    based on its current opacity / auto-opacity state.

    Args:
        *args: n/a
    """
    widgets = pyqt.get_top_level_widgets(class_name="MainDockWindow")
    for ap in widgets:
        update = getattr(ap, "update_passthrough_mask", None)
        if update is not None:
            update()


def get_option_var_passthrough_state():
    """Return the anim picker opacity-passthrough option var.

    Returns:
        int: 0 or 1
    """
    if not cmds.optionVar(exists="mgear_ap_passthrough_OV"):
        cmds.optionVar(intValue=("mgear_ap_passthrough_OV", 0))

    return cmds.optionVar(query="mgear_ap_passthrough_OV")


def set_mgear_ap_passthrough_state(state):
    """Set the opacity-passthrough option var and refresh open pickers.

    Args:
        state (bool, int): 0, 1, True, False
    """
    cmds.optionVar(intValue=("mgear_ap_passthrough_OV", int(state)))
    refresh_passthrough()


def install():
    """Install Anim Picker gui menu"""
    pm.setParent(mgear.menu_id, menu=True)

    state = get_option_var_passthrough_state()

    cmds.setParent(mgear.menu_id, menu=True)
    pm.menuItem(divider=True)
    cmds.menuItem(
        "mgear_ap_menuitem",
        label="Anim Picker",
        subMenu=True,
        tearOff=True,
        image="mgear_mouse-pointer.svg",
    )
    cmds.menuItem(label="Anim Picker", command=str_open_picker_mode)
    cmds.menuItem(label="Anim Picker (Dockable)", command=str_open_dockable_mode)
    pm.menuItem(divider=True)
    cmds.menuItem(label="Edit Anim Picker", command=str_open_edit_mode)
    pm.menuItem(divider=True)
    msg = (
        "Click through empty picker areas to the viewport when the window is "
        "transparent (opacity < 100%) and Auto opacity is off."
    )
    cmds.menuItem(
        "mgear_ap_passthrough_menuitem",
        label="Enable opacity passthrough",
        command=set_mgear_ap_passthrough_state,
        checkBox=state,
        ann=msg,
    )
